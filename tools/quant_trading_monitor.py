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
    .venv/bin/python tools/quant_trading_monitor.py ack-buy --symbol 600000 --price 10.5 --shares 500
    .venv/bin/python tools/quant_trading_monitor.py ack-sell --symbol 600000 --price 10.9 --shares 500
    .venv/bin/python tools/quant_trading_monitor.py status
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from quant_core import StrategySpec, load_config, read_cache
from quant_live_scan import (
    ACTIVE_SYMBOLS_PATH,
    fetch_batch_quotes,
    load_volume_semantics,
    resolve_universe,
    timing_from_quote_hist,
    volume_gate_suppresses,
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
EVENT_DATA_UNTRUSTED = "DATA_UNTRUSTED"
EVENT_CONNECTION_LOST = "LIVE_CONNECTION_LOST"

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

    def open_position(self, symbol: str, price: float, shares: int, when: str, strategy: str) -> dict:
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


def in_session(now: datetime | None = None) -> bool:
    now = now or now_sh()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return SESSION_AM[0] <= t <= SESSION_AM[1] or SESSION_PM[0] <= t <= SESSION_PM[1]


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
) -> dict:
    """Single fast-layer pass. Deterministic: same quotes+state -> same events."""
    now = now or now_sh()
    today = now.date()
    day_str = today.isoformat()
    if not in_session(now):
        status = "MARKET_CLOSED"
        _write_summary(store, status, [], now, day_str, state_dir)
        return {"status": status, "events": [], "symbols": 0}

    resolved = resolve_universe(None, active_path=ACTIVE_SYMBOLS_PATH)
    symbols = list(resolved["symbols"])
    position_symbols = [p["symbol"] for p in store.positions["open"]]
    quote_symbols = sorted(set(symbols) | set(position_symbols))
    quotes = fetch_batch_quotes(quote_symbols)

    if semantic_status is None:
        semantic_status = load_volume_semantics(
            expected_symbols=symbols, universe_as_of=resolved["as_of"]
        )["status"]
    suppressed = volume_gate_suppresses(semantic_status)

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
        _write_summary(store, status, events, now, day_str, state_dir)
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
        hist, meta = read_cache("daily", f"{symbol}_qfq")
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
        hist, _meta = read_cache("daily", f"{symbol}_qfq")
        hist_close = (
            pd.to_numeric(hist.sort_values("date")["close"], errors="coerce").dropna()
            if hist is not None
            else None
        )
        positions_live[symbol] = {
            "price": round(price, 3),
            "pnl": round((price - float(position["entry_price"])) * position["shares"], 2),
        }
        state, reason = evaluate_exit(position, price, hist_close, spec, today)
        if state != position["state"]:
            position["state"] = state
            position["exit_reason"] = reason
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
    )
    return {"status": status, "events": events, "symbols": len(quote_symbols)}


def _write_summary(store: Store, status: str, events: list, now: datetime, day: str,
                   state_dir: Path, attention: list[dict] | None = None, symbols: int = 0,
                   positions_live: dict | None = None) -> None:
    ready = [s for s, o in store.opportunities.items() if o.get("state") == ST_READY]
    near = [s for s, o in store.opportunities.items() if o.get("state") == ST_NEAR]
    exit_alerts = [p["symbol"] for p in store.positions["open"] if p.get("state") == "EXIT_ALERT"]
    _write_json(Path(state_dir) / "state.json", {
        "as_of": now.isoformat(),
        "day": day,
        "status": status,
        "symbols_scanned": symbols,
        "attention_items": len([a for a in (attention or []) if a.get("state") in (ST_READY, "EXIT_ALERT")]),
        "ready": ready,
        "near": near,
        "watch": [s for s, o in store.opportunities.items() if o.get("state") == ST_WATCH],
        "positions": [
            {
                **{k: p.get(k) for k in ("id", "symbol", "entry_price", "shares", "state", "exit_reason")},
                **((positions_live or {}).get(p["symbol"], {})),
            }
            for p in store.positions["open"]
        ],
        "exit_alerts": exit_alerts,
        "events": events,
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
    when = _ack_time(args.time)
    position = store.open_position(args.symbol.upper(), float(args.price), int(args.shares), when, spec.name)
    opp = store.opportunities.get(position["symbol"])
    if opp and opp.get("state") in (ST_NEAR, ST_READY, ST_WATCH):
        opp["state"] = ST_EXECUTED
        opp["since"] = when[:10]
    store.record_forward("EXECUTED", position["symbol"], when[:10], float(args.price), position["id"])
    store.append_alert({
        "day": when[:10], "type": EVENT_POSITION_OPENED, "symbol": position["symbol"],
        "price": float(args.price), "what": "user BUY acknowledged",
        "why": f"{position['id']} {args.shares} shares @ {args.price}",
        "conditions": None, "invalidation": "close via ack-sell", "data_trust": "USER_CONFIRMED",
    })
    store.save()
    print(json.dumps({"position": position["id"], "symbol": position["symbol"], "state": "HOLD"}, ensure_ascii=False))
    return 0


def cmd_ack_sell(args, store: Store) -> int:
    symbol = args.symbol.upper()
    open_positions = [p for p in store.positions["open"] if p["symbol"] == symbol]
    if not open_positions:
        print(json.dumps({"error": f"no open position for {symbol}"}), file=sys.stderr)
        return 1
    when = _ack_time(args.time)
    closed = store.close_position(open_positions[0], float(args.price), int(args.shares), when)
    # the position is gone; the symbol's opportunity lifecycle resumes
    opp = store.opportunities.get(symbol)
    if opp and opp.get("state") == ST_EXECUTED:
        store.opportunities[symbol] = {**opp, "state": ST_WATCH, "since": when[:10]}
    store.record_forward("CLOSED", symbol, when[:10], float(args.price), closed["id"])
    store.append_alert({
        "day": when[:10], "type": EVENT_POSITION_CLOSED, "symbol": symbol,
        "price": float(args.price), "what": "user SELL acknowledged",
        "why": f"{closed['id']} closed, pnl {closed['pnl']}",
        "conditions": None, "invalidation": None, "data_trust": "USER_CONFIRMED",
    })
    store.save()
    print(json.dumps({"closed": closed["id"], "pnl": closed["pnl"]}, ensure_ascii=False))
    return 0


def cmd_cycle(args, store: Store) -> int:
    cfg, spec = _load_strategy()
    result = run_cycle(store, active_cfg=cfg, spec=spec, state_dir=store.dir)
    settle_forward(store)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["status"] in ("NO_TRADE", "ALERTS", "MARKET_CLOSED") else 3


def cmd_session(args, store: Store) -> int:
    cfg, spec = _load_strategy()
    interval = max(30, int(args.interval))
    deadline = time.monotonic() + args.minutes * 60
    cycles = 0
    print(f"session monitor: interval={interval}s minutes={args.minutes} state={store.dir}", flush=True)
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
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
        if not in_session() and result["status"] == "MARKET_CLOSED" and args.exit_on_close:
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
    p_buy.add_argument("--time", default=None, help="ISO time; default now (Asia/Shanghai)")
    p_sell = sub.add_parser("ack-sell", help="user-confirmed SELL -> CLOSED")
    p_sell.add_argument("--symbol", required=True)
    p_sell.add_argument("--price", type=float, required=True)
    p_sell.add_argument("--shares", type=int, required=True)
    p_sell.add_argument("--time", default=None)
    sub.add_parser("status", help="print current monitor state")
    args = parser.parse_args()

    store = Store(args.state_dir)
    handlers = {
        "once": cmd_cycle,
        "session": cmd_session,
        "ack-buy": cmd_ack_buy,
        "ack-sell": cmd_ack_sell,
        "status": cmd_status,
    }
    return handlers[args.cmd](args, store)


if __name__ == "__main__":
    sys.exit(main())
