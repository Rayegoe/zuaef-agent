"""M1 Live Trading Loop v0.1 — trading-session monitor (spec v2.0-optimized, M1).

Turns the one-shot daily chain (scan -> brief -> dashboard) into a continuous
session loop over the already-selected active watch universe:

    slow layer (NOT this loop): candidate builder -> active universe
    fast layer (this loop, 30-60s): quotes -> timing -> strategy conditions
        -> opportunity state changes -> material-change alerts
    position layer: user-acknowledged positions -> exit-condition alerts

Deterministic throughout. The Agent is NOT a polling engine: material state
changes land in the alert stream (and the dashboard attention area); an Agent
interpretation can be run afterwards on that stream, never inside the loop.

Business distinctions enforced here (spec 00 §9):
- MARKET_CLOSED      outside A-share session — no synthetic activity;
- SYSTEM_UNAVAILABLE connection lost / data untrusted — never reported as NO_TRADE;
- NO_TRADE           healthy scan, no opportunity met the frozen policy.

Opportunity lifecycle (minimal, spec M1 §6): WATCH -> NEAR -> READY ->
INVALIDATED; EXECUTED is set only by a user BUY acknowledgement. NEAR is a
real computation: the worst normalized remaining gap to the frozen entry
clauses (pullback, volume ratio, 1d strength) within the monitoring near-band.
READY is exactly the frozen scan trigger with the semantic gate armed.

Positions are first-class: created only by `ack-buy` (human external effect),
monitored against the frozen S3 exit rules (stop-loss / take-profit /
close-below-MA5 / max holding days), closed only by `ack-sell`. Forward
observation (D+1/3/5/8, MFE/MAE) accrues for real NEAR/READY/EXECUTED/CLOSED
records from cached daily bars — never mocked, never backfilled as fills.

State lives under workspace/artifacts/quant/trading/ (file-native, no new
platform). `--state-dir` isolates fixture/replay runs from real results.

    .venv/bin/python tools/quant_trading_monitor.py once
    .venv/bin/python tools/quant_trading_monitor.py session --interval 45
    .venv/bin/python tools/quant_trading_monitor.py ack-buy --symbol 600000 --price 10.5 --shares 500 --venue paper
    .venv/bin/python tools/quant_trading_monitor.py ack-sell --symbol 600000 --price 10.9 --shares 500
    .venv/bin/python tools/quant_trading_monitor.py skip --symbol 600000 --price 10.5 --note "too extended"
    .venv/bin/python tools/quant_trading_monitor.py status
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
# zuaef_quant.freshness / zuaef_quant.watchlist are stdlib-only host modules
# shared with the agent's quant toolset — one source of truth for the
# freshness contract and the analysis-watchlist layout.
_PLUGINS_DIR = Path(__file__).resolve().parents[1] / "plugins" / "zuaef-quant"
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

from quant_core import StrategySpec, load_config, read_cache
from quant_live_scan import (
    ACTIVE_SYMBOLS_PATH,
    UniverseError,
    fetch_batch_quotes,
    load_volume_semantics,
    resolve_universe,
    timing_from_quote_hist,
    volume_gate_suppresses,
)
from zuaef_quant.freshness import derive_freshness, market_date_of
from zuaef_quant.watchlist import (
    WatchlistError,
    all_symbols_in,
    normalize_symbol,
    read_symbols_in,
)

TZ_SH = ZoneInfo("Asia/Shanghai")
STATE_DIR = Path("workspace/artifacts/quant/trading")
ACTIVE_STRATEGY = Path("benchmarks/quant/gen1/active.toml")

NEAR_BAND_DEFAULT = 0.25  # monitoring sensitivity: worst clause within 25% of its frozen magnitude
SESSION_AM = (dtime(9, 30), dtime(11, 30))
SESSION_PM = (dtime(13, 0), dtime(15, 0))
FORWARD_HORIZONS = (1, 3, 5, 8)

EVENT_NEW_NEAR = "NEW_NEAR"
EVENT_NEW_READY = "NEW_READY"
EVENT_READY_INVALIDATED = "READY_INVALIDATED"
EVENT_POSITION_EXIT_ALERT = "POSITION_EXIT_ALERT"
EVENT_POSITION_EXIT_CLEARED = "POSITION_EXIT_CLEARED"
EVENT_POSITION_OPENED = "POSITION_OPENED"
EVENT_POSITION_CLOSED = "POSITION_CLOSED"
EVENT_HUMAN_SKIP = "HUMAN_SKIP"
EVENT_DATA_UNTRUSTED = "DATA_UNTRUSTED"
EVENT_CONNECTION_LOST = "LIVE_CONNECTION_LOST"

VENUES = ("paper", "real")

ST_WATCH, ST_NEAR, ST_READY, ST_INVALIDATED, ST_EXECUTED = (
    "WATCH", "NEAR", "READY", "INVALIDATED", "EXECUTED",
)


# ---------------------------------------------------------------------------
# Pure lifecycle logic (no I/O) — the deterministic heart of the monitor.
# ---------------------------------------------------------------------------


def clause_distances(pullback: float, ratio: float, strength: float, price: float, spec: StrategySpec) -> dict:
    """Normalized remaining gap to each frozen entry clause (>=0; 0 = met).

    Real computation off the same values the scan uses — not UI decoration.
    The strength clause is `strength >= 0`; its gap is the recovery needed,
    as a fraction of the current price.
    """
    return {
        "pullback": max(0.0, (pullback - spec.entry_pullback_max) / abs(spec.entry_pullback_max)),
        "volume": max(0.0, (spec.entry_volume_ratio_min - ratio) / spec.entry_volume_ratio_min),
        "strength": max(0.0, -strength / price) if price > 0 else 1.0,
    }


def is_ready(trigger: bool, semantic_suppressed: bool) -> bool:
    """READY = frozen entry conditions hold AND the semantic gate arms them."""
    return bool(trigger) and not semantic_suppressed


def classify_opportunity(
    prev_state: str | None,
    *,
    tracked: bool,
    near: bool,
    ready: bool,
) -> tuple[str, str | None]:
    """One symbol's lifecycle transition. Returns (new_state, event|None)."""
    if ready:
        event = EVENT_NEW_READY if prev_state != ST_READY else None
        return ST_READY, event
    if near:
        event = EVENT_NEW_NEAR if prev_state not in (ST_NEAR,) else None
        return ST_NEAR, event
    if prev_state in (ST_NEAR, ST_READY):
        return ST_INVALIDATED, EVENT_READY_INVALIDATED
    if prev_state is None and not tracked:
        return ST_WATCH, None
    return (prev_state or ST_WATCH), None


def evaluate_exit(
    position: dict,
    price: float,
    hist_close: pd.Series | None,
    spec: StrategySpec,
    today: date,
) -> tuple[str, str | None]:
    """Frozen S3 exit rules against a live price. Returns (state, reason)."""
    entry = float(position["entry_price"])
    if price <= entry * (1 - spec.stop_loss_pct):
        return "EXIT_ALERT", f"stop_loss {spec.stop_loss_pct:.0%} (entry {entry}, now {price})"
    if price >= entry * (1 + spec.take_profit_pct):
        return "EXIT_ALERT", f"take_profit {spec.take_profit_pct:.0%} (entry {entry}, now {price})"
    if hist_close is not None and len(hist_close) >= 5:
        last_close = float(hist_close.iloc[-1])
        ma5 = float(hist_close.tail(5).mean())
        if last_close < ma5:
            return "EXIT_ALERT", f"close_below_ma5 ({last_close:.2f} < {ma5:.2f})"
    entry_day = date.fromisoformat(str(position["entry_date"]))
    if (today - entry_day).days >= spec.max_holding_days:
        return "EXIT_ALERT", f"max_holding_days {spec.max_holding_days}"
    return "HOLD", None


def forward_math(bars: pd.DataFrame, event_day: str, ref_price: float) -> dict:
    """D+1/3/5/8 returns and 5-day MFE/MAE for one observation, from real
    cached daily bars after the event day. Missing horizons stay pending."""
    days = pd.to_datetime(bars["date"], format="mixed", errors="coerce")
    bars = bars.assign(_day=days).loc[days.notna()].sort_values("_day")
    future = bars.loc[pd.to_datetime(bars["_day"]) > pd.Timestamp(event_day)]
    out: dict = {}
    for n in FORWARD_HORIZONS:
        key = f"d{n}"
        if len(future) >= n:
            close = float(future["close"].iloc[n - 1])
            out[key] = round(close / ref_price - 1, 6)
    if len(future) >= 5:
        window = future.iloc[:5]
        out["mfe_5d"] = round(float(window["high"].max()) / ref_price - 1, 6)
        out["mae_5d"] = round(float(window["low"].min()) / ref_price - 1, 6)
    return out


# ---------------------------------------------------------------------------
# State store (file-native JSON; --state-dir isolates fixtures from reality).
# ---------------------------------------------------------------------------


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


class Store:
    def __init__(self, state_dir: Path = STATE_DIR):
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.opportunities = _read_json(self.dir / "opportunities.json", {})
        self.positions = _read_json(self.dir / "positions.json", {"open": [], "closed": [], "next_id": 1})
        self.forward = _read_json(self.dir / "forward.json", {"observations": []})
        alerts_path = self.dir / "alerts.jsonl"
        self._alerts_path = alerts_path

    def append_alert(self, alert: dict) -> None:
        self._alerts_path.parent.mkdir(parents=True, exist_ok=True)
        with self._alerts_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert, ensure_ascii=False, default=str) + "\n")

    def reload(self) -> None:
        """Re-read the canonical files, discarding stale in-memory state."""
        self.opportunities = _read_json(self.dir / "opportunities.json", {})
        self.positions = _read_json(self.dir / "positions.json", {"open": [], "closed": [], "next_id": 1})
        self.forward = _read_json(self.dir / "forward.json", {"observations": []})

    @contextmanager
    def transaction(self):
        """Serialize one read-modify-write transaction on the canonical ledger.

        Concurrent writers are real (reproduced live 2026-09-07: pydantic-ai
        runs same-response tool calls concurrently, so parallel ack-buys both
        read ``next_id=1`` and last-writer-wins silently lost a position).
        The lock is per TRANSACTION, not per process: long-running loops
        (``session``) re-enter per cycle, so an ack from another process
        waits at most one cycle instead of being locked out for the session.
        Every mutating command must hold this lock across its reload →
        mutate → save span; ``save()`` inside the lock publishes exactly the
        state it mutated.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / ".ledger.lock").open("a+") as lock_fh:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            try:
                self.reload()
                yield
            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)

    def alerts_today(self, today: str, kinds: set[str]) -> int:
        if not self._alerts_path.exists():
            return 0
        n = 0
        for line in self._alerts_path.read_text(encoding="utf-8").splitlines():
            try:
                a = json.loads(line)
            except ValueError:
                continue
            if str(a.get("day")) == today and a.get("type") in kinds:
                n += 1
        return n

    def save(self) -> None:
        _write_json(self.dir / "opportunities.json", self.opportunities)
        _write_json(self.dir / "positions.json", self.positions)
        _write_json(self.dir / "forward.json", self.forward)

    def record_forward(self, kind: str, symbol: str, day: str, ref_price: float, ref_id: str | None = None) -> None:
        self.forward["observations"].append(
            {"kind": kind, "symbol": symbol, "day": day, "ref_price": ref_price, "ref_id": ref_id}
        )

    def open_position(self, symbol: str, price: float, shares: int, when: str, strategy: str, venue: str = "paper") -> dict:
        pid = f"p-{self.positions['next_id']:04d}"
        self.positions["next_id"] += 1
        position = {
            "id": pid,
            "symbol": symbol,
            "entry_price": price,
            "shares": shares,
            "entry_time": when,
            "entry_date": when[:10],
            "strategy": strategy,
            "venue": venue,
            "state": "HOLD",
        }
        self.positions["open"].append(position)
        return position

    def close_position(self, position: dict, price: float, shares: int, when: str) -> dict:
        position["state"] = "CLOSED"
        self.positions["open"].remove(position)
        pnl = (price - float(position["entry_price"])) * shares
        closed = {**position, "exit_price": price, "exit_shares": shares, "exit_time": when, "pnl": round(pnl, 2)}
        self.positions["closed"].append(closed)
        return closed


# ---------------------------------------------------------------------------
# Session clock
# ---------------------------------------------------------------------------


def now_sh() -> datetime:
    return datetime.now(TZ_SH)


def market_phase(now: datetime | None = None) -> str:
    now = now or now_sh()
    if now.tzinfo is not None:
        now = now.astimezone(TZ_SH)
    if now.weekday() >= 5:
        return "MARKET_CLOSED"
    t = now.time()
    if t < SESSION_AM[0]:
        return "PRE_OPEN"
    if t < SESSION_AM[1]:
        return "OPEN_AM"
    if t < SESSION_PM[0]:
        return "LUNCH_BREAK"
    if t < SESSION_PM[1]:
        return "OPEN_PM"
    return "MARKET_CLOSED"


def in_session(now: datetime | None = None) -> bool:
    return market_phase(now) in {"OPEN_AM", "OPEN_PM"}


def market_tick_at(quotes: dict) -> str | None:
    stamps = []
    for quote in quotes.values():
        if not quote or not quote.get("date") or not quote.get("time"):
            continue
        try:
            stamp = datetime.fromisoformat(f"{quote['date']}T{quote['time']}")
            stamps.append(stamp.replace(tzinfo=TZ_SH) if stamp.tzinfo is None else stamp.astimezone(TZ_SH))
        except ValueError:
            continue
    return max(stamps).isoformat() if stamps else None


def watchlist_dir(state_dir: Path) -> Path:
    """The analysis watchlist dir is a sibling of the trading dir:
    artifacts/quant/trading ↔ artifacts/quant/watchlist."""
    return Path(state_dir).parent / "watchlist"


def analysis_watchlist_symbols(state_dir: Path) -> list[str]:
    """Union of every scope's user-attention symbols. A read failure degrades
    to an empty list — watchlist diagnostics must never break the trading
    loop (the canonical candidate/position plane is independent)."""
    try:
        return all_symbols_in(watchlist_dir(state_dir))
    except OSError:
        return []


# Evidence-first (symbol context): price-limit arithmetic is a host fact,
# never an LLM probability guess. Board classification from the code prefix
# covers the regular regimes; ST (±5%) is NOT detectable from the code alone
# and stays an explicit limitation rather than a guess.
_PRICE_LIMIT_RULES = (
    ("300", 0.20, "SZ_CHINEXT"), ("301", 0.20, "SZ_CHINEXT"),
    ("688", 0.20, "SH_STAR"), ("689", 0.20, "SH_STAR"),
    ("43", 0.30, "BJ"), ("83", 0.30, "BJ"), ("87", 0.30, "BJ"),
    ("88", 0.30, "BJ"), ("92", 0.30, "BJ"),
)
_PRICE_LIMIT_DEFAULT = (0.10, "MAIN_BOARD")


def price_limit_rule(symbol: str, prev_close: float, price: float | None = None) -> dict:
    """Host-computed daily price limit for one A-share (evidence packet).

    limit_up_price uses the standard two-decimal rounding of prev_close ×
    (1 + pct); ``at_limit_up`` compares the observed price against it."""
    code = str(symbol).strip()
    pct, board = _PRICE_LIMIT_DEFAULT
    for prefix, rule_pct, rule_board in _PRICE_LIMIT_RULES:
        if code.startswith(prefix):
            pct, board = rule_pct, rule_board
            break
    if prev_close <= 0:
        return {
            "available": False,
            "board": board,
            "reason": "prev_close unavailable",
            "limitations": ["ST shares trade at ±5% and cannot be detected from the code prefix"],
        }
    limit_up = round(prev_close * (1 + pct), 2)
    result = {
        "available": True,
        "board": board,
        "price_limit_pct": pct,
        "limit_up_price": limit_up,
        "basis": "board-prefix rule on the 6-digit code; host arithmetic",
        "limitations": ["ST shares trade at ±5% and cannot be detected from the code prefix"],
    }
    if price is not None and price > 0:
        result["at_limit_up"] = price >= limit_up
        result["distance_to_limit"] = round(limit_up - price, 3)
    return result


# ---------------------------------------------------------------------------
# One deterministic monitor cycle
# ---------------------------------------------------------------------------


def run_cycle(
    store: Store,
    *,
    active_cfg: dict,
    spec: StrategySpec,
    state_dir: Path = STATE_DIR,
    now: datetime | None = None,
    semantic_status: str | None = None,
    data_adapter=None,
) -> dict:
    """Single fast-layer pass. Deterministic: same quotes+state -> same events."""
    now = now or now_sh()
    today = now.date()
    day_str = today.isoformat()
    if not in_session(now):
        status = market_phase(now)
        _write_summary(store, status, [], now, day_str, state_dir)
        return {"status": status, "events": [], "symbols": 0}
    # Host-only replay seam. The default live data path stays unchanged.
    resolved = (data_adapter.resolve_universe() if data_adapter is not None
                else resolve_universe(None, active_path=ACTIVE_SYMBOLS_PATH))
    symbols = list(resolved["symbols"])
    position_symbols = [p["symbol"] for p in store.positions["open"]]
    # Three-tier universe (analysis watchlist): user-attention symbols join
    # the QUOTE plane only. The opportunity layer below iterates the
    # candidate `symbols` exclusively, so a watched symbol can never produce
    # READY/NEAR — strategy evidence stays free of user curation.
    watchlist_symbols = analysis_watchlist_symbols(Path(state_dir))
    quote_symbols = sorted(set(symbols) | set(position_symbols) | set(watchlist_symbols))
    quotes = (data_adapter.fetch_batch_quotes(quote_symbols) if data_adapter is not None
              else fetch_batch_quotes(quote_symbols))
    history_read = data_adapter.read_cache if data_adapter is not None else read_cache

    if semantic_status is None:
        semantic_status = load_volume_semantics(
            expected_symbols=symbols, universe_as_of=resolved["as_of"]
        )["status"]
    suppressed = volume_gate_suppresses(semantic_status)
    # data trust = this cycle's semantic gate verdict, fail-closed; it is a
    # data fact and deliberately separate from runtime availability
    data_trust = "PASS" if semantic_status == "PASS" else "FAIL"

    events: list[dict] = []

    def emit(etype: str, symbol: str | None, detail: dict) -> None:
        """Material state change -> in-memory cycle result AND the durable
        alert stream (spec M1 §8: state changes land in a real artifact)."""
        alert = {"ts": now.isoformat(timespec="seconds"), "type": etype, "symbol": symbol, "day": day_str, **detail}
        events.append(alert)
        store.append_alert(alert)

    # --- data trust: connection + semantic gate (deduped per day) ---
    quote_failures = [s for s in quote_symbols if quotes.get(s) is None]
    stale = [
        s
        for s, q in quotes.items()
        if q is not None and str(q.get("date", ""))[:8] != today.strftime("%Y%m%d")
    ]
    if len(quote_failures) == len(quote_symbols) or (quotes and len(stale) > len(quotes) / 2):
        if store.alerts_today(day_str, {EVENT_CONNECTION_LOST}) == 0:
            emit(
                EVENT_CONNECTION_LOST,
                None,
                {
                    "price": None,
                    "what": "live connection lost",
                    "why": f"quote failures={len(quote_failures)}/{len(quote_symbols)} stale={len(stale)}",
                    "conditions": None,
                    "invalidation": "monitoring paused until quotes return to today's session",
                    "data_trust": semantic_status,
                },
            )
        status = "SYSTEM_UNAVAILABLE"
        _write_summary(store, status, events, now, day_str, state_dir, data_trust="UNKNOWN")
        return {"status": status, "events": events, "symbols": len(quote_symbols)}
    if suppressed and store.alerts_today(day_str, {EVENT_DATA_UNTRUSTED}) == 0:
        emit(
            EVENT_DATA_UNTRUSTED,
            None,
            {
                "price": None,
                "what": "volume semantics not proven — trigger clause suppressed",
                "why": f"volume_semantics={semantic_status} (fail-closed, spec P0.1)",
                "conditions": None,
                "invalidation": "READY requires a proven semantic proof",
                "data_trust": semantic_status,
            },
        )

    # --- opportunity layer ---
    near_band = float(active_cfg.get("monitor", {}).get("near_band", NEAR_BAND_DEFAULT))
    executed_symbols = {p["symbol"] for p in store.positions["open"]}
    attention: list[dict] = []
    for symbol in symbols:
        quote = quotes.get(symbol)
        if quote is None or quote.get("price", 0) <= 0:
            continue
        hist, meta = history_read("daily", f"{symbol}_qfq")
        if hist is None or meta is None:
            continue
        timing = timing_from_quote_hist(quote, hist)
        if timing is None:
            continue
        pullback, ratio = timing
        strength = float(quote["price"]) - float(quote["prev_close"])
        if symbol in executed_symbols:
            # The lifecycle fact that matters now is the Position; keep the
            # opportunity pinned to EXECUTED until the position closes.
            opp = store.opportunities.get(symbol, {})
            store.opportunities[symbol] = {
                **opp,
                "state": ST_EXECUTED,
                "last_eval": now.isoformat(),
                "price": round(float(quote["price"]), 3),
            }
            continue
        trigger = (
            pullback <= spec.entry_pullback_max
            and ratio >= spec.entry_volume_ratio_min
            and strength >= 0
        )
        distances = clause_distances(pullback, ratio, strength, float(quote["price"]), spec)
        near = (not trigger) and all(v <= near_band for v in distances.values())
        ready = is_ready(trigger, suppressed)
        prev = store.opportunities.get(symbol, {}).get("state")
        state, event = classify_opportunity(prev, tracked=symbol in store.opportunities, near=near, ready=ready)
        store.opportunities[symbol] = {
            "state": state,
            "since": store.opportunities.get(symbol, {}).get("since", day_str) if state == prev else day_str,
            "last_eval": now.isoformat(),
            "price": round(float(quote["price"]), 3),
            "pullback_5d": round(pullback, 4),
            "volume_ratio_20d": round(ratio, 3),
            "distance": {k: round(v, 4) for k, v in distances.items()},
        }
        if state in (ST_NEAR, ST_READY):
            attention.append({"symbol": symbol, "state": state, **store.opportunities[symbol]})
        if event:
            emit(
                event,
                symbol,
                {
                    "price": round(float(quote["price"]), 3),
                    "what": f"{prev or 'none'} -> {state}",
                    "why": (
                        "frozen entry conditions met" if state == ST_READY
                        else "within near-band of frozen entry conditions" if state == ST_NEAR
                        else "conditions no longer hold"
                    ),
                    "conditions": {
                        "pullback_5d": round(pullback, 4),
                        "volume_ratio_20d": round(ratio, 3),
                        "strength_1d": round(strength, 3),
                        "entry": f"pullback<={spec.entry_pullback_max}, ratio>={spec.entry_volume_ratio_min}, strength>=0",
                    },
                    "invalidation": "any clause leaves the near-band / trigger turns false",
                    "data_trust": semantic_status,
                },
            )
            if state == ST_READY:
                store.record_forward("READY", symbol, day_str, float(quote["price"]))

    # --- position layer ---
    positions_live: dict = {}
    for position in list(store.positions["open"]):
        symbol = position["symbol"]
        quote = quotes.get(symbol)
        if quote is None or quote.get("price", 0) <= 0:
            continue
        price = float(quote["price"])
        hist, _meta = history_read("daily", f"{symbol}_qfq")
        hist_close = (
            pd.to_numeric((hist.sort_values("date") if "date" in hist else hist)["close"], errors="coerce").dropna()
            if hist is not None
            else None
        )
        positions_live[symbol] = {
            "price": round(price, 3),
            "pnl": round((price - float(position["entry_price"])) * position["shares"], 2),
        }
        state, reason = evaluate_exit(position, price, hist_close, spec, today)
        close_evidence = {"close_value": None, "close_date": None, "ma5_value": None, "bar_source": None}
        if hist_close is not None and len(hist_close) >= 5:
            close_evidence["close_value"] = float(hist_close.iloc[-1])
            close_evidence["ma5_value"] = float(hist_close.iloc[-5:].mean())
            raw_date = hist.loc[hist_close.index[-1], "date"] if "date" in hist else None
            parsed_date = pd.to_datetime(raw_date, errors="coerce")
            close_evidence["close_date"] = parsed_date.date().isoformat() if not pd.isna(parsed_date) else None
            close_evidence["bar_source"] = (_meta or {}).get("source")
        positions_live[symbol]["latest_close_evidence"] = close_evidence
        if reason and reason.startswith("close_below_ma5") and close_evidence["close_date"] and close_evidence["close_date"] < day_str:
            reason = reason.replace("close_below_ma5", "latest_confirmed_close_below_ma5", 1)
        if state != position["state"]:
            position["state"] = state
            position["exit_reason"] = reason
            position["exit_evidence"] = close_evidence if reason and "close_below_ma5" in reason else None
            if state == "EXIT_ALERT":
                emit(
                    EVENT_POSITION_EXIT_ALERT,
                    symbol,
                    {
                        "price": round(price, 3),
                        "what": "HOLD -> EXIT_ALERT",
                        "why": reason,
                        "conditions": {
                            "entry_price": position["entry_price"],
                            "shares": position["shares"],
                            "pnl": round((price - float(position["entry_price"])) * position["shares"], 2),
                            "holding_days": (today - date.fromisoformat(position["entry_date"])).days,
                            **close_evidence,
                        },
                        "invalidation": "cleared only by user SELL acknowledgement",
                        "data_trust": semantic_status,
                    },
                )
            else:
                emit(
                    EVENT_POSITION_EXIT_CLEARED,
                    symbol,
                    {
                        "price": round(price, 3),
                        "what": "EXIT_ALERT -> HOLD",
                        "why": "exit condition no longer holds intraday",
                        "conditions": None,
                        "invalidation": "re-alerts on the next transition",
                        "data_trust": semantic_status,
                    },
                )
        attention.append({
            "symbol": symbol,
            "state": position["state"],
            "kind": "position",
            "price": round(price, 3),
            "entry_price": position["entry_price"],
            "pnl": round((price - float(position["entry_price"])) * position["shares"], 2),
            "exit_reason": position.get("exit_reason"),
        })

    status = "ALERTS" if any(e["type"] not in (EVENT_POSITION_EXIT_CLEARED,) for e in events) else "NO_TRADE"
    store.save()
    _write_summary(
        store, status, events, now, day_str, state_dir,
        attention=attention, symbols=len(quote_symbols), positions_live=positions_live,
        data_trust=data_trust,
        tick_at=market_tick_at(quotes),
        analysis_watchlist=watchlist_symbols,
    )
    return {"status": status, "events": events, "symbols": len(quote_symbols), "data_trust": data_trust}


def _write_summary(store: Store, status: str, events: list, now: datetime, day: str,
                   state_dir: Path, attention: list[dict] | None = None, symbols: int = 0,
                   positions_live: dict | None = None, data_trust: str = "UNKNOWN",
                   tick_at: str | None = None, analysis_watchlist: list[str] | None = None) -> None:
    ready = [s for s, o in store.opportunities.items() if o.get("state") == ST_READY]
    near = [s for s, o in store.opportunities.items() if o.get("state") == ST_NEAR]
    exit_alerts = [p["symbol"] for p in store.positions["open"] if p.get("state") == "EXIT_ALERT"]
    previous = _read_json(Path(state_dir) / "state.json", {})
    _write_json(Path(state_dir) / "state.json", {
        "as_of": now.isoformat(),
        "cycle_at": now.isoformat(),
        "heartbeat_at": now.isoformat(),
        "last_scan_at": now.isoformat() if symbols > 0 else previous.get("last_scan_at"),
        "market_tick_at": tick_at,
        "market_phase": market_phase(now),
        "analysis_watchlist": sorted(analysis_watchlist or []),
        "day": day,
        "status": status,
        "symbols_scanned": symbols,
        "attention_items": len([a for a in (attention or []) if a.get("state") in (ST_READY, "EXIT_ALERT")]),
        "ready": ready,
        "near": near,
        "watch": [s for s, o in store.opportunities.items() if o.get("state") == ST_WATCH],
        "positions": [
            {
                **{k: p.get(k) for k in ("id", "symbol", "entry_price", "shares", "venue", "state", "exit_reason", "exit_evidence")},
                **((positions_live or {}).get(p["symbol"], {})),
            }
            for p in store.positions["open"]
        ],
        "exit_alerts": exit_alerts,
        "events": events,
        # data trust is a fact about the data gate, NOT runtime availability:
        # PASS/FAIL only when semantics were evaluated this cycle, else UNKNOWN
        "data_trust": data_trust,
        "market_no_trade": status == "NO_TRADE",
        "system_unavailable": status == "SYSTEM_UNAVAILABLE",
    })


# ---------------------------------------------------------------------------
# Forward observation settlement (host-owned, from real cached bars only)
# ---------------------------------------------------------------------------


def settle_forward(store: Store) -> dict:
    settled = 0
    for obs in store.forward["observations"]:
        if obs.get("d8") is not None:
            continue
        hist, _meta = read_cache("daily", f"{obs['symbol']}_qfq")
        if hist is None:
            continue
        math = forward_math(hist, str(obs["day"]), float(obs["ref_price"]))
        if math:
            obs.update(math)
            settled += 1
    store.save()
    return {"observations": len(store.forward["observations"]), "updated": settled}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_strategy() -> tuple[dict, StrategySpec]:
    cfg = load_config(ACTIVE_STRATEGY)
    return cfg, StrategySpec.from_config(cfg)


def _ack_time(value: str | None) -> str:
    if value:
        return value
    return now_sh().isoformat(timespec="seconds")


def cmd_ack_buy(args, store: Store) -> int:
    _cfg, spec = _load_strategy()
    venue = getattr(args, "venue", None) or "paper"
    note = getattr(args, "note", None) or ""
    if venue not in VENUES:
        print(json.dumps({"error": f"venue must be one of {list(VENUES)}"}), file=sys.stderr)
        return 1
    when = _ack_time(args.time)
    with store.transaction():
        position = store.open_position(args.symbol.upper(), float(args.price), int(args.shares), when, spec.name, venue=venue)
        opp = store.opportunities.get(position["symbol"])
        if opp and opp.get("state") in (ST_NEAR, ST_READY, ST_WATCH):
            opp["state"] = ST_EXECUTED
            opp["since"] = when[:10]
        store.record_forward("EXECUTED", position["symbol"], when[:10], float(args.price), position["id"])
        store.append_alert({
            "ts": when, "day": when[:10], "type": EVENT_POSITION_OPENED, "symbol": position["symbol"],
            "price": float(args.price), "what": "user BUY acknowledged",
            "why": f"{position['id']} {args.shares} shares @ {args.price}",
            "venue": venue, "note": note,
            "conditions": None, "invalidation": "close via ack-sell", "data_trust": "USER_CONFIRMED",
        })
        store.save()
    print(json.dumps({"position": position["id"], "symbol": position["symbol"], "state": "HOLD", "venue": venue}, ensure_ascii=False))
    return 0


def cmd_ack_sell(args, store: Store) -> int:
    symbol = args.symbol.upper()
    open_positions = [p for p in store.positions["open"] if p["symbol"] == symbol]
    if not open_positions:
        print(json.dumps({"error": f"no open position for {symbol}"}), file=sys.stderr)
        return 1
    position = open_positions[0]
    # Phase 1: full close only — a partial share count would close the whole
    # position while booking wrong P&L, so it is rejected, not silently shrunk
    if int(args.shares) != int(position["shares"]):
        print(json.dumps({
            "error": f"Phase 1 closes the full position only: open {position['shares']} shares, got {args.shares}",
        }), file=sys.stderr)
        return 1
    venue = getattr(args, "venue", None) or position.get("venue", "paper")
    if venue not in VENUES:
        print(json.dumps({"error": f"venue must be one of {list(VENUES)}"}), file=sys.stderr)
        return 1
    if venue != position.get("venue", "paper"):
        print(json.dumps({
            "error": f"venue mismatch: position opened as {position.get('venue')}, sell claimed {venue}",
        }), file=sys.stderr)
        return 1
    note = getattr(args, "note", None) or ""
    when = _ack_time(args.time)
    with store.transaction():
        # Re-resolve the position inside the lock: a concurrent writer may
        # have closed it between the pre-check above and this transaction.
        open_positions = [p for p in store.positions["open"] if p["symbol"] == symbol]
        if not open_positions:
            print(json.dumps({"error": f"no open position for {symbol}"}), file=sys.stderr)
            return 1
        position = open_positions[0]
        if int(args.shares) != int(position["shares"]):
            print(json.dumps({
                "error": f"Phase 1 closes the full position only: open {position['shares']} shares, got {args.shares}",
            }), file=sys.stderr)
            return 1
        closed = store.close_position(position, float(args.price), int(args.shares), when)
        # the position is gone; the symbol's opportunity lifecycle resumes
        opp = store.opportunities.get(symbol)
        if opp and opp.get("state") == ST_EXECUTED:
            store.opportunities[symbol] = {**opp, "state": ST_WATCH, "since": when[:10]}
        store.record_forward("CLOSED", symbol, when[:10], float(args.price), closed["id"])
        store.append_alert({
            "ts": when, "day": when[:10], "type": EVENT_POSITION_CLOSED, "symbol": symbol,
            "price": float(args.price), "what": "user SELL acknowledged",
            "why": f"{closed['id']} closed, pnl {closed['pnl']}",
            "venue": venue, "note": note,
            "conditions": None, "invalidation": None, "data_trust": "USER_CONFIRMED",
        })
        store.save()
    print(json.dumps({"closed": closed["id"], "pnl": closed["pnl"], "venue": venue}, ensure_ascii=False))
    return 0


def cmd_skip(args, store: Store) -> int:
    """Record a human SKIP decision on a live opportunity as a real fact:
    one HUMAN_SKIP alert plus a SKIP forward observation (settles D+1/3/5/8
    through the existing settle path, feeding future override-value research).
    The opportunity state machine is intentionally untouched."""
    symbol = args.symbol.upper()
    price = float(args.price)
    if price <= 0:
        print(json.dumps({"error": "price must be positive"}), file=sys.stderr)
        return 1
    when = _ack_time(args.time)
    note = getattr(args, "note", None) or ""
    with store.transaction():
        store.record_forward("SKIP", symbol, when[:10], price)
        store.append_alert({
            "ts": when, "day": when[:10], "type": EVENT_HUMAN_SKIP, "symbol": symbol,
            "price": price, "what": "user skipped the opportunity",
            "why": note or "human decided not to act",
            "venue": None, "note": note,
            "conditions": None, "invalidation": None, "data_trust": "USER_CONFIRMED",
        })
        store.save()
    print(json.dumps({"skipped": symbol, "day": when[:10]}, ensure_ascii=False))
    return 0


def cmd_cycle(args, store: Store) -> int:
    cfg, spec = _load_strategy()
    # One cycle = one transaction: the scan runs under the lock, so a
    # concurrent ack waits at most one scan instead of racing the ledger.
    with store.transaction():
        result = run_cycle(store, active_cfg=cfg, spec=spec, state_dir=store.dir)
        settle_forward(store)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["status"] in ("NO_TRADE", "ALERTS", "MARKET_CLOSED", "PRE_OPEN", "LUNCH_BREAK") else 3


def cmd_session(args, store: Store) -> int:
    cfg, spec = _load_strategy()
    interval = max(30, int(args.interval))
    deadline = time.monotonic() + args.minutes * 60
    cycles = 0
    print(f"session monitor: interval={interval}s minutes={args.minutes} state={store.dir}", flush=True)
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            # Per-cycle transaction: each cycle reloads the canonical files,
            # so acks written by other processes between cycles are picked
            # up instead of being overwritten by a stale in-memory copy.
            with store.transaction():
                result = run_cycle(store, active_cfg=cfg, spec=spec, state_dir=store.dir)
                settle_forward(store)
        except Exception as exc:  # noqa: BLE001 — the loop must survive a bad cycle
            result = {"status": "SYSTEM_UNAVAILABLE", "events": [], "error": repr(exc)}
        cycles += 1
        with (store.dir / "soak.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": now_sh().isoformat(timespec="seconds"), "status": result["status"],
                "events": len(result.get("events", [])), "symbols": result.get("symbols", 0),
                "ms": int((time.perf_counter() - started) * 1000),
            }) + "\n")
        print(json.dumps(result, ensure_ascii=False, default=str), flush=True)
        if result["status"] in {"MARKET_CLOSED", "LUNCH_BREAK"} and args.exit_on_close:
            break
        time.sleep(max(0.0, interval - (time.perf_counter() - started)))
    print(json.dumps({"session_cycles": cycles}), flush=True)
    return 0


def cmd_status(args, store: Store) -> int:
    state = _read_json(store.dir / "state.json", {})
    print(json.dumps({
        "state": state,
        "open_positions": store.positions["open"],
        "closed_trades": store.positions["closed"],
        "forward_observations": len(store.forward["observations"]),
    }, ensure_ascii=False, default=str))
    return 0


def cmd_symbol_context(args, store: Store) -> int:
    """On-demand single-symbol analysis context (read-only diagnostics).

    Three-tier universe semantics: the answer states where the symbol LIVES
    (candidate pool / analysis watchlist / open positions) and gives real
    strategy-clause distances — but diagnostics never produce READY/NEAR.
    Not in the candidate pool ≠ not researchable; that distinction is the
    whole point of this command."""
    try:
        symbol = normalize_symbol(args.symbol)
    except WatchlistError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

    now = now_sh()
    _cfg, spec = _load_strategy()
    today = now.date()
    state = _read_json(store.dir / "state.json", {})
    scope = (args.scope or "").strip()
    watch_directory = watchlist_dir(store.dir)
    try:
        scope_symbols = read_symbols_in(watch_directory, scope) if scope else None
    except OSError:
        scope_symbols = None
    candidate_symbols: list[str] | None
    try:
        candidate_symbols = list(
            resolve_universe(None, active_path=ACTIVE_SYMBOLS_PATH)["symbols"]
        )
    except (UniverseError, OSError, ValueError):
        candidate_symbols = None  # membership unknown stays unknown

    quote = fetch_batch_quotes([symbol]).get(symbol)
    quote_block: dict = {"available": False}
    if quote and float(quote.get("price", 0) or 0) > 0:
        quote_day = str(quote.get("date", ""))[:8]
        try:
            quote_date = datetime.strptime(quote_day, "%Y%m%d").date()
        except ValueError:
            quote_date = None
        if quote_date is None:
            q_status, q_reason = "INSUFFICIENT_EVIDENCE", "quote date unreadable"
        elif quote_date == today and in_session(now):
            q_status, q_reason = "LIVE_CURRENT", "today's session quote"
        elif quote_date == today:
            q_status = "TODAY_LAST_SESSION"
            q_reason = f"today's quote outside session ({market_phase(now)})"
        elif quote_date < today:
            q_status, q_reason = "STALE", f"quote date {quote_date.isoformat()} predates today"
        else:
            q_status, q_reason = "INSUFFICIENT_EVIDENCE", f"quote date {quote_date.isoformat()} is in the future"
        price = float(quote["price"])
        prev_close = float(quote.get("prev_close", 0) or 0)
        quote_block = {
            "available": True,
            "price": price,
            "prev_close": prev_close,
            "change_pct": round((price / prev_close - 1) * 100, 2) if prev_close > 0 else None,
            "volume": quote.get("volume"),
            "quote_date": quote_date.isoformat() if quote_date else None,
            "quote_time": quote.get("time"),
            "freshness_status": q_status,
            "freshness_reason": q_reason,
        }
    else:
        quote_block["freshness_reason"] = "quote unavailable in this run"

    # strategy distance on the SAME primitives the frozen scan uses
    strategy_block: dict = {"available": False}
    hist, hist_meta = read_cache("daily", f"{symbol}_qfq")
    hist_close = (
        pd.to_numeric((hist.sort_values("date") if "date" in hist else hist)["close"], errors="coerce").dropna()
        if hist is not None else None
    )
    # history sufficiency is a host fact: the frozen timing needs 25 cached
    # sessions strictly before the quote date — never an LLM impression of
    # "历史不足"
    history_block = {
        "bars_available": int(len(hist_close)) if hist_close is not None else 0,
        "required_bars": 25,
    }
    history_block["sufficient"] = history_block["bars_available"] >= history_block["required_bars"]
    if quote_block["available"] and quote.get("prev_close", 0):
        history_block["note"] = "bars counted from the cached daily history (all cached sessions)"
    hist_last_date = None
    if hist is not None and len(hist):
        raw_last = hist["date"].iloc[-1] if "date" in hist else None
        parsed = pd.to_datetime(raw_last, errors="coerce")
        hist_last_date = parsed.date().isoformat() if not pd.isna(parsed) else None
    if quote_block["available"] and hist_close is not None and len(hist_close) >= 5:
        timing = timing_from_quote_hist(quote, hist)
        if timing is not None:
            pullback, ratio = timing
            strength = float(quote["price"]) - float(quote.get("prev_close", 0) or 0)
            distances = clause_distances(pullback, ratio, strength, float(quote["price"]), spec)
            strategy_block = {
                "available": True,
                "pullback_5d": round(pullback, 4),
                "volume_ratio_20d": round(ratio, 3),
                "strength_1d": round(strength, 3),
                "clause_distances": {k: round(v, 4) for k, v in distances.items()},
                "frozen_thresholds": {
                    "entry_pullback_max": spec.entry_pullback_max,
                    "entry_volume_ratio_min": spec.entry_volume_ratio_min,
                },
                "history_last_date": hist_last_date,
                "ma5_evidence": {
                    "close_value": float(hist_close.iloc[-1]),
                    "ma5_value": float(hist_close.iloc[-5:].mean()),
                    "close_date": hist_last_date,
                },
            }
        else:
            strategy_block = {"available": False, "reason": "insufficient history for timing"}
    elif quote_block["available"]:
        strategy_block = {"available": False, "reason": "insufficient daily history"}

    last_scan_at = state.get("last_scan_at")
    scan_freshness = derive_freshness(
        now=now,
        latest_market_data_date=state.get("day"),
        last_scan_at=last_scan_at,
    )
    result = {
        "symbol": symbol,
        "requested_at": now.isoformat(timespec="seconds"),
        "market_phase": market_phase(now),
        "universe": {
            "in_candidate_pool": (symbol in candidate_symbols) if candidate_symbols is not None else None,
            "in_analysis_watchlist_scope": (symbol in scope_symbols) if scope_symbols is not None else None,
            "analysis_scope": scope or None,
            "in_open_positions": any(p["symbol"] == symbol for p in store.positions["open"]),
            "semantics": (
                "candidate pool -> READY/NEAR lifecycle; analysis watchlist -> "
                "diagnostics only, never READY/NEAR; positions -> HOLD/EXIT watch"
            ),
        },
        "quote": quote_block,
        "strategy_distance": strategy_block,
        "history": history_block,
        "market_rules": (
            price_limit_rule(symbol, float(quote["prev_close"]), float(quote["price"]))
            if quote_block["available"] and float(quote.get("prev_close", 0) or 0) > 0
            else {"available": False, "reason": "quote unavailable"}
        ),
        "scan": {
            "last_scan_at": last_scan_at,
            "data_trust": state.get("data_trust") or "UNKNOWN",
            "freshness_status": scan_freshness["freshness_status"],
            "freshness_reason": scan_freshness["freshness_reason"],
        },
        "limitations": [
            "analysis-only context: on-demand fetch, not the 45s monitor loop",
            "diagnostic distances never generate READY/NEAR; only the frozen candidate scan does",
            "watchlist membership is user attention, not a strategy input",
            "strategy profitability UNPROVEN (S3 frozen, PIT-contaminated universe)",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=STATE_DIR,
                        help="state directory (fixtures/replays must isolate here)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("once", help="one monitor cycle")
    p_session = sub.add_parser("session", help="continuous in-session loop")
    p_session.add_argument("--interval", type=int, default=45, help="seconds between cycles (30-60)")
    p_session.add_argument("--minutes", type=int, default=600, help="max wall-clock run time")
    p_session.add_argument("--exit-on-close", action="store_true", help="stop at market close")
    p_buy = sub.add_parser("ack-buy", help="user-confirmed BUY -> Position")
    p_buy.add_argument("--symbol", required=True)
    p_buy.add_argument("--price", type=float, required=True)
    p_buy.add_argument("--shares", type=int, required=True)
    p_buy.add_argument("--venue", choices=list(VENUES), default="paper", help="paper (default) or real")
    p_buy.add_argument("--note", default="", help="free-text human note")
    p_buy.add_argument("--time", default=None, help="ISO time; default now (Asia/Shanghai)")
    p_sell = sub.add_parser("ack-sell", help="user-confirmed SELL -> CLOSED (full close only)")
    p_sell.add_argument("--symbol", required=True)
    p_sell.add_argument("--price", type=float, required=True)
    p_sell.add_argument("--shares", type=int, required=True, help="must equal the open position's shares")
    p_sell.add_argument("--venue", choices=list(VENUES), default=None, help="must match the position's venue")
    p_sell.add_argument("--note", default="", help="free-text human note")
    p_sell.add_argument("--time", default=None)
    p_skip = sub.add_parser("skip", help="record a human SKIP on an opportunity (no position change)")
    p_skip.add_argument("--symbol", required=True)
    p_skip.add_argument("--price", type=float, required=True, help="reference price for forward settlement")
    p_skip.add_argument("--note", default="", help="why the opportunity was skipped")
    p_skip.add_argument("--time", default=None)
    p_sym = sub.add_parser("symbol-context",
                           help="on-demand single-symbol analysis context (read-only)")
    p_sym.add_argument("--symbol", required=True, help="6-digit A-share code")
    p_sym.add_argument("--scope", default=None,
                       help="analysis watchlist scope for membership facts")
    sub.add_parser("status", help="print current monitor state")
    args = parser.parse_args()

    store = Store(args.state_dir)
    handlers = {
        "once": cmd_cycle,
        "session": cmd_session,
        "ack-buy": cmd_ack_buy,
        "ack-sell": cmd_ack_sell,
        "skip": cmd_skip,
        "status": cmd_status,
        "symbol-context": cmd_symbol_context,
    }
    return handlers[args.cmd](args, store)


if __name__ == "__main__":
    sys.exit(main())
