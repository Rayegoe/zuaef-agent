"""Shared quant primitives for ZUAEF-ASHARE-001 phase proofs (P0–P2).

Business truth lives in artifacts; this module holds only deterministic,
host-owned mechanics:

- akshare fetch + local CSV cache with source/retrieval metadata (P0);
- frozen market-rules config (effective-dated A-share execution truth);
- independent event replay over frozen trade intents (T+1, price limits,
  suspension, lots, commission, stamp duty, slippage);
- after-cost metrics and artifact writers.

akshare is imported lazily so the module stays importable in the core
environment (tests there skip quant behavior); heavy qlib usage lives in
tools/quant_eval_qlib.py and runs in the .venv-quant side environment.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")
CACHE_DIR = Path("data/quant-cache")

REQUIRED_HISTORY_COLUMNS = ("date", "open", "high", "low", "close", "volume")
HISTORY_CACHE_SCHEMA = 2
HISTORY_NORMALIZATION = "volume-shares-v1"


def to_tx_symbol(code: str) -> str:
    """Map a bare 6-digit A-share code to the Tencent exchange-prefixed form."""
    if code.startswith("6"):
        return f"sh{code}"
    if code.startswith(("0", "3")):
        return f"sz{code}"
    if code.startswith(("4", "8", "9")):
        return f"bj{code}"
    raise ValueError(f"cannot map symbol to exchange prefix: {code}")


# ---------------------------------------------------------------------------
# Local cache (P0 D006/D007): explicit files + sidecar metadata, no framework.
# ---------------------------------------------------------------------------


def _cache_paths(kind: str, key: str, cache_dir: Path) -> tuple[Path, Path]:
    base = cache_dir / kind
    return base / f"{key}.csv", base / f"{key}.meta.json"


def read_cache(kind: str, key: str, cache_dir: Path = CACHE_DIR) -> tuple[pd.DataFrame | None, dict | None]:
    csv_path, meta_path = _cache_paths(kind, key, cache_dir)
    if not (csv_path.exists() and meta_path.exists()):
        return None, None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    df = pd.read_csv(csv_path, dtype={"symbol": str, "constituent_code": str})
    return df, meta


def write_cache(kind: str, key: str, df: pd.DataFrame, meta: dict, cache_dir: Path = CACHE_DIR) -> None:
    csv_path, meta_path = _cache_paths(kind, key, cache_dir)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def history_cache_is_current(
    df: pd.DataFrame,
    meta: dict,
    *,
    symbol: str,
    adjust: str,
    start_date: str,
) -> bool:
    """Return whether a daily cache satisfies the current ingestion contract.

    This deliberately validates both the sidecar and basic CSV facts.  A cache
    written before volume normalization cannot be silently reused merely
    because its files exist.
    """
    if not isinstance(meta, dict) or df.empty:
        return False
    expected_adjust = adjust or "raw"
    if any(col not in df.columns for col in (*REQUIRED_HISTORY_COLUMNS, "symbol")):
        return False
    if (
        meta.get("cache_schema") != HISTORY_CACHE_SCHEMA
        or meta.get("normalization") != HISTORY_NORMALIZATION
        or meta.get("volume_unit") != "share"
        or meta.get("symbol") != symbol
        or meta.get("adjust") != expected_adjust
        or meta.get("start_date") != start_date
        or meta.get("rows") != len(df)
    ):
        return False
    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any() or (df["symbol"].astype(str) != symbol).any():
        return False
    actual_range = [str(dates.min().date()), str(dates.max().date())]
    return meta.get("date_range") == actual_range


# Volume semantic (spec v2.0 P0.1): amount/(volume*close) clusters at ~1 when
# volume is in shares (股) and at ~100 when in lots (手); the gap is two
# orders of magnitude, so 10 separates them with margin.
VOLUME_LOT_FACTOR_MIN = 10.0


def normalize_volume_unit(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Canonicalize ingested volume to shares at the quant data boundary.

    Tencent hist_tx returns volume in lots for some symbols and in shares
    for others; per-symbol raw-history profiling shows the unit is constant
    across each series's full history (e.g. 000786: 2101/2101 lot rows;
    002460: 2104/2104 share rows). The recent rows of an adjusted series are
    raw-price-anchored, so amount/(volume*close) on those rows identifies
    the source unit; a lot series is rescaled x100 once, here, so every
    cached series carries one canonical semantics. The applied fact is
    returned for the cache sidecar meta.
    """
    info = {"volume_unit": "unknown", "volume_source_unit": None, "volume_unit_factor_applied": None}
    if df.empty or "amount" not in df.columns:
        return df, info
    factors = [
        float(row["amount"]) / (float(row["volume"]) * float(row["close"]))
        for _, row in df.tail(5).iterrows()
        if float(row["volume"]) > 0 and float(row["close"]) > 0 and float(row["amount"]) > 0
    ]
    if not factors:
        return df, info
    if statistics.median(factors) >= VOLUME_LOT_FACTOR_MIN:
        df = df.copy()
        df["volume"] = df["volume"] * 100.0
        return df, {
            "volume_unit": "share",
            "volume_source_unit": "lot",
            "volume_unit_factor_applied": 100.0,
        }
    return df, {
        "volume_unit": "share",
        "volume_source_unit": "share",
        "volume_unit_factor_applied": 1.0,
    }


def fetch_history(symbol: str, adjust: str, *, refresh: bool = False, cache_dir: Path = CACHE_DIR,
                  start_date: str = "20180101") -> tuple[pd.DataFrame, dict, str]:
    """Fetch normalized daily history (Tencent path); cache; never mask failure."""
    key = f"{symbol}_{adjust or 'raw'}"
    if not refresh:
        try:
            df, meta = read_cache("daily", key, cache_dir)
        except (OSError, ValueError, pd.errors.ParserError):
            df, meta = None, None
        if (
            df is not None
            and meta is not None
            and history_cache_is_current(
                df, meta, symbol=symbol, adjust=adjust, start_date=start_date
            )
        ):
            return df, meta, "cache"
    import akshare as ak

    raw = None
    last_exc: Exception | None = None
    for attempt, delay in enumerate((0.0, 2.0, 8.0)):
        if delay:
            time.sleep(delay)
        try:
            raw = ak.stock_zh_a_hist_tx(
                symbol=to_tx_symbol(symbol), start_date=start_date, end_date="20500101", adjust=adjust
            )
            break
        except Exception as exc:  # noqa: BLE001 — transient transport failures retried boundedly
            last_exc = exc
    if raw is None:
        raise RuntimeError(f"history fetch failed for {symbol} adjust={adjust}: {last_exc}")
    if raw is None or raw.empty:
        raise RuntimeError(f"empty history returned for {symbol} adjust={adjust}")
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    missing = [c for c in REQUIRED_HISTORY_COLUMNS if c not in df.columns]
    if missing:
        raise RuntimeError(f"history for {symbol} missing normalized columns: {missing}")
    df["symbol"] = symbol
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    keep = [c for c in ("date", "symbol", *REQUIRED_HISTORY_COLUMNS[1:], "amount", "turnover") if c in df.columns]
    df = df[keep].sort_values("date").reset_index(drop=True)
    df, volume_info = normalize_volume_unit(df)
    meta = {
        "cache_schema": HISTORY_CACHE_SCHEMA,
        "normalization": HISTORY_NORMALIZATION,
        "source": "akshare.stock_zh_a_hist_tx",
        "symbol": symbol,
        "adjust": adjust or "raw",
        "start_date": start_date,
        "retrieved_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "rows": len(df),
        "date_range": [str(df["date"].min()), str(df["date"].max())],
        **volume_info,
    }
    write_cache("daily", key, df, meta, cache_dir)
    return df, meta, "live"


def fetch_csi500_constituents(*, refresh: bool = False, cache_dir: Path = CACHE_DIR) -> tuple[pd.DataFrame, dict, str]:
    key = "csi500_cons"
    if not refresh:
        df, meta = read_cache("universe", key, cache_dir)
        if df is not None:
            return df, meta, "cache"
    import akshare as ak

    raw = ak.index_stock_cons_csindex(symbol="000905")
    if raw is None or raw.empty:
        raise RuntimeError("empty CSI500 constituent list")
    df = raw.rename(
        columns={
            "日期": "effective_date",
            "成分券代码": "constituent_code",
            "成分券名称": "constituent_name",
            "指数代码": "index_code",
            "指数名称": "index_name",
        }
    )
    df["effective_date"] = pd.to_datetime(df["effective_date"]).dt.date
    df["constituent_code"] = df["constituent_code"].astype(str).str.zfill(6)
    meta = {
        "source": "akshare.index_stock_cons_csindex",
        "index": "000905",
        "retrieved_at": datetime.now(TZ_SHANGHAI).isoformat(),
        "rows": len(df),
        "effective_date": str(df["effective_date"].max()),
    }
    write_cache("universe", key, df, meta, cache_dir)
    return df, meta, "live"


# ---------------------------------------------------------------------------
# Frozen market-rules config (spec 04 §7: effective-dated, no scattered
# constants in code).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketRules:
    commission_rate: float
    commission_min: float
    stamp_duty_periods: tuple[dict, ...]  # {effective_from: 'YYYY-MM-DD', sell_rate: float}
    slippage_bps: float
    lot_size: int
    t_plus_1: bool
    price_limit_periods: tuple[dict, ...]  # {prefixes, effective_from, limit_pct}
    initial_capital: float

    @classmethod
    def from_config(cls, cfg: dict) -> MarketRules:
        ex = cfg["execution"]
        return cls(
            commission_rate=float(ex["commission_rate"]),
            commission_min=float(ex["commission_min"]),
            stamp_duty_periods=tuple(ex["stamp_duty"]),
            slippage_bps=float(ex["slippage_bps"]),
            lot_size=int(ex["lot_size"]),
            t_plus_1=bool(ex["t_plus_1"]),
            price_limit_periods=tuple(ex["price_limits"]),
            initial_capital=float(ex["initial_capital"]),
        )

    def stamp_duty_sell_rate(self, on: date) -> float:
        periods = sorted(self.stamp_duty_periods, key=lambda p: p["effective_from"])
        rate = 0.0
        for period in periods:
            if date.fromisoformat(period["effective_from"]) <= on:
                rate = float(period["sell_rate"])
        if on < date.fromisoformat(periods[0]["effective_from"]):
            raise ValueError(f"no stamp-duty rule effective on {on}")
        return rate

    def price_limit_pct(self, symbol: str, on: date) -> float:
        applicable = [
            p
            for p in self.price_limit_periods
            if symbol.startswith(tuple(p["prefixes"]))
            and date.fromisoformat(p["effective_from"]) <= on
        ]
        if not applicable:
            raise ValueError(f"no price-limit rule for {symbol} on {on}")
        return float(max(applicable, key=lambda p: p["effective_from"])["limit_pct"])


def load_config(path: Path) -> dict:
    import tomllib

    with path.open("rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# Strategy spec (spec 05 §2: minimal execution ABI).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategySpec:
    name: str
    universe: str
    max_holding_days: int
    stop_loss_pct: float
    take_profit_pct: float
    position_fraction: float
    max_positions: int
    # entry-clause thresholds: the only values an Agent child may mutate
    # (one material change per child); entry/exit structure stays host-owned.
    entry_pullback_max: float = -0.06
    entry_volume_ratio_min: float = 1.80

    @classmethod
    def from_config(cls, cfg: dict) -> StrategySpec:
        # spec-pack template shape: strategy fields at the TOML top level;
        # accept a [strategy] section too for embedded configs.
        s = cfg.get("strategy", cfg)
        return cls(
            name=str(s["name"]),
            universe=str(s["universe"]),
            max_holding_days=int(s["max_holding_days"]),
            stop_loss_pct=float(s["stop_loss_pct"]),
            take_profit_pct=float(s["take_profit_pct"]),
            position_fraction=float(s["position_fraction"]),
            max_positions=int(s["max_positions"]),
            entry_pullback_max=float(s.get("entry_pullback_max", -0.06)),
            entry_volume_ratio_min=float(s.get("entry_volume_ratio_min", 1.80)),
        )


# ---------------------------------------------------------------------------
# Independent event replay (P1 after-cost accounting; P2 adds blocked-trade
# failure modes). Input: frozen trade intents + raw prices + frozen rules.
# Never reads Qlib NAV.
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    action: str  # "BUY" | "SELL"
    symbol: str
    intent_date: date  # day the decision was made (execution is next open)


@dataclass
class FillRecord:
    date: date
    symbol: str
    action: str
    shares: int
    price: float
    cost: float
    reason: str = "filled"


@dataclass
class BlockedRecord:
    date: date
    symbol: str
    action: str
    reason: str


@dataclass
class PortfolioState:
    cash: float
    positions: dict[str, dict] = field(default_factory=dict)  # symbol -> {shares, entry_price, entry_date, available_date}


class ReplayEngine:
    """Deterministic daily event loop over frozen intents and raw prices.

    Execution semantics (spec 04 §7):
    - intents decided on day T execute at T+1 open (next_open);
    - T+1: shares bought on day D are sellable from D+1 (with next_open
      execution this is satisfied structurally, and is asserted);
    - buy blocked at limit-up open, sell blocked at limit-down open (reason
      recorded, sell retried next tradable day);
    - no bar on a date = suspension: trade impossible, sell deferred;
    - buys round down to the lot size and never exceed available cash;
    - costs: commission (rate, min), sell-side stamp duty (effective-dated),
      slippage applied adversely to fill price.
    """

    def __init__(self, rules: MarketRules, spec: StrategySpec, prices_raw: dict[str, pd.DataFrame],
                 enforce_market_truth: bool = True):
        self.rules = rules
        self.spec = spec
        # enforce_market_truth=False runs the same deterministic loop without
        # limit-up/down blocks — the cross-engine vector stage (P1). The
        # independent replay (P2) always runs with market truth on.
        self.enforce_market_truth = enforce_market_truth
        # per symbol: date -> (open, close), ascending; raw executable prices
        self.bars: dict[str, pd.DataFrame] = {}
        self._close_series: dict[str, pd.Series] = {}
        for symbol, df in prices_raw.items():
            b = df[["date", "open", "close"]].copy()
            b["date"] = pd.to_datetime(b["date"]).dt.date
            b = b.set_index("date")
            self.bars[symbol] = b
            self._close_series[symbol] = b["close"]
        self.portfolio = PortfolioState(cash=rules.initial_capital)
        self.fills: list[FillRecord] = []
        self.blocked: list[BlockedRecord] = []
        self.equity_rows: list[dict] = []

    def _slippage(self, price: float, side: str) -> float:
        slip = price * self.rules.slippage_bps / 10_000.0
        return price + slip if side == "BUY" else price - slip

    def _commission(self, notional: float) -> float:
        return max(notional * self.rules.commission_rate, self.rules.commission_min)

    def _open(self, symbol: str, on: date) -> float | None:
        bar = self.bars.get(symbol)
        if bar is None or on not in bar.index:
            return None
        return float(bar.at[on, "open"])

    def _limit_prices(self, symbol: str, on: date, prev_close: float) -> tuple[float, float]:
        pct = self.rules.price_limit_pct(symbol, on)
        return prev_close * (1 + pct), prev_close * (1 - pct)

    def _execute_buy(self, intent: Intent, on: date, prev_close_by_symbol: dict[str, float]) -> None:
        if len(self.portfolio.positions) >= self.spec.max_positions:
            self.blocked.append(BlockedRecord(on, intent.symbol, "BUY", "max_positions"))
            return
        open_price = self._open(intent.symbol, on)
        if open_price is None:
            self.blocked.append(BlockedRecord(on, intent.symbol, "BUY", "suspended_or_no_bar"))
            return
        prev_close = prev_close_by_symbol.get(intent.symbol)
        if self.enforce_market_truth and prev_close is not None:
            limit_up, _ = self._limit_prices(intent.symbol, on, prev_close)
            if open_price >= limit_up - 1e-9:
                # Entry idea is stale after a missed fill; record, do not retry.
                self.blocked.append(BlockedRecord(on, intent.symbol, "BUY", "limit_up_open"))
                return
        price = self._slippage(open_price, "BUY")
        budget = self.portfolio.cash * self.spec.position_fraction
        shares = math.floor(budget / price / self.rules.lot_size) * self.rules.lot_size
        if shares <= 0:
            self.blocked.append(BlockedRecord(on, intent.symbol, "BUY", "insufficient_budget"))
            return
        notional = shares * price
        cost = self._commission(notional)
        if notional + cost > self.portfolio.cash:
            shares -= self.rules.lot_size
            if shares <= 0:
                self.blocked.append(BlockedRecord(on, intent.symbol, "BUY", "insufficient_cash"))
                return
            notional = shares * price
            cost = self._commission(notional)
        self.portfolio.cash -= notional + cost
        position = self.portfolio.positions.get(intent.symbol)
        if position is None:
            self.portfolio.positions[intent.symbol] = {
                "shares": shares,
                "entry_price": price,
                "entry_date": on,
                "buy_date": on,  # T+1: sellable strictly after the buy date
                "holding_days": 0,
            }
        else:
            total = position["shares"] + shares
            position["entry_price"] = (
                position["entry_price"] * position["shares"] + notional
            ) / total
            position["shares"] = total
            position["entry_date"] = on
        self.fills.append(FillRecord(on, intent.symbol, "BUY", shares, price, cost))

    def _execute_sell(self, intent: Intent, on: date, prev_close_by_symbol: dict[str, float]) -> bool:
        """Returns True when the sell settled; blocked deferrable sells return False."""
        position = self.portfolio.positions.get(intent.symbol)
        if position is None:
            self.blocked.append(BlockedRecord(on, intent.symbol, "SELL", "no_position"))
            return True
        if self.rules.t_plus_1 and on <= position["buy_date"]:
            self.blocked.append(BlockedRecord(on, intent.symbol, "SELL", "t_plus_1"))
            return False
        open_price = self._open(intent.symbol, on)
        if open_price is None:
            self.blocked.append(BlockedRecord(on, intent.symbol, "SELL", "suspended_or_no_bar"))
            return False
        prev_close = prev_close_by_symbol.get(intent.symbol)
        if self.enforce_market_truth and prev_close is not None:
            _, limit_down = self._limit_prices(intent.symbol, on, prev_close)
            if open_price <= limit_down + 1e-9:
                self.blocked.append(BlockedRecord(on, intent.symbol, "SELL", "limit_down_open"))
                return False
        price = self._slippage(open_price, "SELL")
        shares = position["shares"]
        notional = shares * price
        stamp = notional * self.rules.stamp_duty_sell_rate(on)
        cost = self._commission(notional) + stamp
        self.portfolio.cash += notional - cost
        self.fills.append(FillRecord(on, intent.symbol, "SELL", shares, price, cost))
        del self.portfolio.positions[intent.symbol]
        return True

    def _prev_closes(self, today: date) -> dict[str, float]:
        prev: dict[str, float] = {}
        for symbol, closes in self._close_series.items():
            prior = closes.loc[closes.index < today]
            if len(prior):
                prev[symbol] = float(prior.iloc[-1])
        return prev

    def run(self, intents: list[Intent], trading_dates: list[date] | None = None) -> dict:
        """Drive the event loop across the trading calendar.

        Intents decided on day T are applied on the next trading day's open.
        Sells blocked by T+1, suspension or limit-down retry on later days;
        a sell that can never settle just stays open (recorded in blocked).
        """
        if trading_dates is None:
            all_dates: set[date] = set()
            for closes in self._close_series.values():
                all_dates.update(closes.index)
            trading_dates = sorted(all_dates)
        self._close_series = {
            symbol: closes.sort_index() for symbol, closes in self._close_series.items()
        }
        pending: list[Intent] = []
        by_day: dict[date, list[Intent]] = {}
        for intent in intents:
            by_day.setdefault(intent.intent_date, []).append(intent)
        for today in trading_dates:
            prev_closes = self._prev_closes(today)
            still_pending: list[Intent] = []
            for intent in pending:
                if intent.action == "BUY":
                    self._execute_buy(intent, today, prev_closes)
                elif not self._execute_sell(intent, today, prev_closes):
                    still_pending.append(intent)
            # intents decided today become executable on the next trading day
            pending = still_pending + list(by_day.get(today, []))
            equity = self.portfolio.cash
            for symbol, position in self.portfolio.positions.items():
                closes = self._close_series.get(symbol)
                close = None
                if closes is not None:
                    known = closes.loc[closes.index <= today].dropna()
                    if len(known):
                        close = float(known.iloc[-1])
                equity += position["shares"] * (
                    close if close is not None else position["entry_price"]
                )
            self.equity_rows.append({"date": today, "equity": equity, "cash": self.portfolio.cash})
        return {
            "fills": self.fills,
            "blocked": self.blocked,
            "equity": pd.DataFrame(self.equity_rows),
            "final_equity": self.equity_rows[-1]["equity"] if self.equity_rows else self.rules.initial_capital,
        }


# ---------------------------------------------------------------------------
# After-cost metrics (spec 05 §6).
# ---------------------------------------------------------------------------


def compute_metrics(equity: pd.DataFrame, fills: list[FillRecord], rules: MarketRules) -> dict:
    eq = equity["equity"].astype(float)
    days_per_year = 244
    total_return = (
        float(eq.iloc[-1] / rules.initial_capital - 1) if len(eq) else 0.0
    )
    years = len(eq) / days_per_year
    annualized = (
        float((eq.iloc[-1] / rules.initial_capital) ** (1 / years) - 1)
        if years > 0 and rules.initial_capital > 0 and eq.iloc[-1] > 0
        else 0.0
    )
    running_max = eq.cummax()
    drawdown = eq / running_max - 1
    sells = [f for f in fills if f.action == "SELL"]
    buy_costs = sum(f.cost for f in fills if f.action == "BUY")
    sell_costs = sum(f.cost for f in fills if f.action == "SELL")
    total_cost = buy_costs + sell_costs
    return {
        "total_return_pct": round(total_return * 100, 4),
        "annualized_return_pct": round(annualized * 100, 4),
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 4),
        "trade_count": len(sells),
        "total_cost": round(total_cost, 2),
        "cost_drag_pct_of_initial": round(total_cost / rules.initial_capital * 100, 4),
    }


def trade_records(fills: list[FillRecord]) -> pd.DataFrame:
    rows = [
        {
            "date": f.date,
            "symbol": f.symbol,
            "action": f.action,
            "shares": f.shares,
            "price": round(f.price, 4),
            "cost": round(f.cost, 2),
            "reason": f.reason,
        }
        for f in fills
    ]
    return pd.DataFrame(rows, columns=["date", "symbol", "action", "shares", "price", "cost", "reason"])


def detect_corporate_action_dates(
    raw: pd.DataFrame,
    qfq: pd.DataFrame,
    *,
    minimum_segment: int = 10,
    absolute_tolerance: float = 0.05,
) -> list[date]:
    """Detect dates where the qfq/raw adjustment factor changes materially.

    The replay does not implement dividends or share-count adjustments.  This
    detector is therefore a conservative trust gate, not corporate-action
    accounting: trades crossing one of these dates must be labelled
    unsupported instead of silently entering trusted metrics.
    """
    left = raw[["date", "close"]].rename(columns={"close": "raw_close"}).copy()
    right = qfq[["date", "close"]].rename(columns={"close": "qfq_close"}).copy()
    left["date"] = pd.to_datetime(left["date"], errors="coerce")
    right["date"] = pd.to_datetime(right["date"], errors="coerce")
    joined = left.merge(right, on="date", how="inner").sort_values("date")
    joined = joined[(joined["raw_close"] > 0) & (joined["qfq_close"] > 0)]
    if len(joined) <= minimum_segment:
        return []
    # Within one adjustment regime Tencent raw and qfq closes have a stable
    # affine mapping.  A dividend/split boundary changes that mapping.  Fit
    # the established segment, detect an out-of-regime residual, then reset;
    # this avoids treating ordinary price moves as corporate actions.
    segment: list[tuple[float, float]] = []
    events: list[date] = []
    for row in joined.itertuples(index=False):
        raw_close, qfq_close = float(row.raw_close), float(row.qfq_close)
        if len(segment) >= minimum_segment:
            sample = segment[-60:]
            slope, intercept = statistics.linear_regression(
                [p[0] for p in sample], [p[1] for p in sample]
            )
            residuals = [abs(y - (slope * x + intercept)) for x, y in sample]
            tolerance = max(
                absolute_tolerance,
                8.0 * (statistics.median(residuals) + 0.005),
            )
            if abs(qfq_close - (slope * raw_close + intercept)) > tolerance:
                events.append(pd.Timestamp(row.date).date())
                segment = []
        segment.append((raw_close, qfq_close))
    return events


def unsupported_corporate_action_trades(
    fills: list[FillRecord],
    prices_raw: dict[str, pd.DataFrame],
    prices_qfq: dict[str, pd.DataFrame],
) -> list[dict]:
    """Return settled trades that cross an unsupported adjustment event."""
    action_dates = {
        symbol: detect_corporate_action_dates(prices_raw[symbol], prices_qfq[symbol])
        for symbol in prices_raw.keys() & prices_qfq.keys()
    }
    entries: dict[str, date] = {}
    unsupported: list[dict] = []
    for fill in sorted(fills, key=lambda f: f.date):
        if fill.action == "BUY":
            entries.setdefault(fill.symbol, fill.date)
            continue
        entry = entries.pop(fill.symbol, None)
        if entry is None:
            continue
        crossed = [d for d in action_dates.get(fill.symbol, []) if entry < d <= fill.date]
        if crossed:
            unsupported.append(
                {
                    "symbol": fill.symbol,
                    "entry_date": str(entry),
                    "exit_date": str(fill.date),
                    "detected_action_dates": [str(d) for d in crossed],
                }
            )
    return unsupported
