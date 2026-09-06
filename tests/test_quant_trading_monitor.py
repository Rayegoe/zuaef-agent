"""M1 trading-loop monitor tests (offline, fixture-driven).

Protects the M1 product boundaries: deterministic lifecycle transitions with
material-change-only alerts (no price-noise spam), READY strictly bound to the
frozen trigger + semantic gate, positions created ONLY by user acknowledgement,
exit alerts on the frozen S3 rules, SYSTEM_UNAVAILABLE never reported as
NO_TRADE, market-closed produces no synthetic activity, and fixture runs stay
inside their --state-dir (never real business artifacts). No live network.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("pandas")

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import pandas as pd
import quant_trading_monitor as mon
from quant_core import StrategySpec

TZ_SH = ZoneInfo("Asia/Shanghai")
NOW = datetime(2026, 9, 2, 10, 0, tzinfo=TZ_SH)  # a Wednesday, in session
TODAY = NOW.date()

SPEC = StrategySpec(
    name="volume_pullback_reversal", universe="csi500_subset", max_holding_days=5,
    stop_loss_pct=0.03, take_profit_pct=0.06, position_fraction=0.10, max_positions=5,
    entry_pullback_max=-0.06, entry_volume_ratio_min=1.80,
)


def make_hist(symbol: str, closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    days = pd.bdate_range(end="2026-09-01", periods=len(closes))
    vols = volumes or [1_000_000.0] * len(closes)
    return pd.DataFrame({
        "symbol": symbol, "date": days.strftime("%Y-%m-%d"),
        "open": closes, "high": [c * 1.01 for c in closes], "low": [c * 0.99 for c in closes],
        "close": closes, "volume": vols, "amount": [c * v for c, v in zip(closes, vols)],
    })


def make_quote(symbol: str, price: float, prev_close: float, volume: float = 2_000_000.0) -> dict:
    return {
        "name": symbol, "price": price, "prev_close": prev_close, "open": prev_close,
        "volume": volume, "date": "20260902", "time": "10:00:00",
    }


# 600001: pullback -6.1% (Ref close,5 = 10.6), ratio 2.0, strength +0.05 -> trigger TRUE (READY)
READY_CLOSES = [10.0] * 25 + [10.6, 10.5, 10.35, 10.1, 9.95]
# 600002: pullback -4.8% (gap 0.20), ratio 1.7 (gap 0.056), strength -0.01 (gap 0.001) -> NEAR
NEAR_CLOSES = [10.0] * 25 + [10.45, 10.4, 10.3, 10.2, 9.95]
# 600003: pullback -1% -> WATCH
WATCH_CLOSES = [10.0] * 25 + [10.1, 10.05, 10.05, 10.0, 10.0]
# 600004: position-only symbol, price above its MA5 (no MA5 exit noise)
POSITION_CLOSES = [10.0] * 25 + [10.3, 10.35, 10.4, 10.45, 10.5]

HIST = {
    "600001": make_hist("600001", READY_CLOSES),
    "600002": make_hist("600002", NEAR_CLOSES),
    "600003": make_hist("600003", WATCH_CLOSES),
    "600004": make_hist("600004", POSITION_CLOSES),
}
QUOTES = {
    "600001": make_quote("600001", 9.95, 9.9),
    "600002": make_quote("600002", 9.95, 9.96, volume=1_700_000.0),
    "600003": make_quote("600003", 10.0, 10.0, volume=1_000_000.0),
    "600004": make_quote("600004", 10.2, 10.15),
}


@pytest.fixture()
def monitor_env(monkeypatch):
    """Patch the monitor's data plane onto fixtures; nothing touches network."""
    monkeypatch.setattr(mon, "resolve_universe", lambda *a, **k: {
        "symbols": list(HIST), "source": "fixture", "source_path": "fixture", "as_of": "fixture"})
    monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: QUOTES.get(s) for s in symbols})
    monkeypatch.setattr(mon, "read_cache", lambda kind, key, cache_dir=None: (HIST[key.split("_")[0]], {}))
    monkeypatch.setattr(mon, "load_volume_semantics", lambda **k: {"status": "PASS"})
    return SimpleNamespace(active_cfg={"monitor": {"near_band": 0.25}})


def fresh_store(tmp_path) -> mon.Store:
    return mon.Store(tmp_path / "trading")


# ---------------------------------------------------------------------------
# lifecycle logic
# ---------------------------------------------------------------------------


class TestLifecycleLogic:
    def test_clause_distances_are_real_and_zero_when_met(self):
        d = mon.clause_distances(-0.06, 1.80, 0.01, 10.0, SPEC)
        assert d == {"pullback": 0.0, "volume": 0.0, "strength": 0.0}
        d2 = mon.clause_distances(-0.045, 1.60, -0.05, 10.0, SPEC)
        assert d2["pullback"] == pytest.approx(0.25, abs=1e-9)
        assert d2["volume"] == pytest.approx(0.1111, abs=1e-3)
        assert d2["strength"] == pytest.approx(0.005, abs=1e-9)

    def test_full_lifecycle_with_single_events(self):
        seq = [
            (False, False, None),                          # -> WATCH, no event
            (True, False, mon.EVENT_NEW_NEAR),             # WATCH -> NEAR
            (False, True, mon.EVENT_NEW_READY),            # NEAR -> READY
            (False, True, None),                           # stable READY: no spam
            (False, False, mon.EVENT_READY_INVALIDATED),   # READY -> INVALIDATED
            (True, False, mon.EVENT_NEW_NEAR),             # re-entry re-alerts
        ]
        prev = None
        for near, ready, expected_event in seq:
            state, event = mon.classify_opportunity(prev, tracked=prev is not None, near=near, ready=ready)
            assert event == expected_event, f"prev={prev} near={near} ready={ready}"
            prev = state

    def test_exit_rules_stop_take_ma5_and_holding(self):
        pos = {"entry_price": 10.0, "entry_date": TODAY.isoformat()}
        assert mon.evaluate_exit(pos, 9.65, None, SPEC, TODAY)[0] == "EXIT_ALERT"
        assert mon.evaluate_exit(pos, 10.65, None, SPEC, TODAY)[0] == "EXIT_ALERT"
        closes = pd.Series([10.5, 10.4, 10.3, 10.2, 9.8])
        assert "close_below_ma5" in mon.evaluate_exit(pos, 10.0, closes, SPEC, TODAY)[1]
        assert mon.evaluate_exit(pos, 10.0, None, SPEC, TODAY)[0] == "HOLD"
        old = {**pos, "entry_date": "2026-08-20"}
        assert "max_holding_days" in mon.evaluate_exit(old, 10.0, None, SPEC, TODAY)[1]

    def test_forward_math_settles_only_available_horizons(self):
        bars = make_hist("600001", [10.0] * 12 + [10.2, 10.4, 10.3, 10.5, 10.8, 10.6, 10.9, 11.0, 10.7, 10.4])
        event_day = str(bars["date"].iloc[11])[:10]  # the day before the specials start
        out = mon.forward_math(bars, event_day, 10.0)
        assert out["d1"] == pytest.approx(0.02) and out["d3"] == pytest.approx(0.03)
        # high = close*1.01, low = close*0.99 in the fixture
        assert out["mfe_5d"] == pytest.approx(10.8 * 1.01 / 10.0 - 1, abs=1e-4)
        assert out["mae_5d"] == pytest.approx(10.2 * 0.99 / 10.0 - 1, abs=1e-4)
        short = make_hist("600002", [10.0] * 10 + [10.2])
        out2 = mon.forward_math(short, str(short["date"].iloc[-2])[:10], 10.0)
        assert out2["d1"] == pytest.approx(0.02) and "d3" not in out2


# ---------------------------------------------------------------------------
# cycle behaviour (fixture data plane)
# ---------------------------------------------------------------------------


class TestCycle:
    def test_market_closed_runs_no_scan_and_fakes_nothing(self, tmp_path, monitor_env, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("no quote fetch outside session")
        monkeypatch.setattr(mon, "fetch_batch_quotes", boom)
        store = fresh_store(tmp_path)
        result = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC,
                               state_dir=store.dir, now=datetime(2026, 9, 2, 16, 0, tzinfo=TZ_SH))
        assert result["status"] == "MARKET_CLOSED" and result["events"] == []

    def test_ready_near_watch_are_detected_with_alerts(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        result = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        assert result["status"] == "ALERTS"
        types = {(e["type"], e["symbol"]) for e in result["events"]}
        assert ("NEW_READY", "600001") in types
        assert ("NEW_NEAR", "600002") in types
        assert store.opportunities["600003"]["state"] == "WATCH"

    def test_no_duplicate_alerts_when_nothing_changes(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        first = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        second = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        assert first["status"] == "ALERTS" and second["status"] == "NO_TRADE"
        assert second["events"] == []

    def test_semantic_gate_fail_closed_invalidates_ready(self, tmp_path, monitor_env, monkeypatch):
        store = fresh_store(tmp_path)
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        monkeypatch.setattr(mon, "load_volume_semantics", lambda **k: {"status": "FAIL"})
        result = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        kinds = [e["type"] for e in result["events"]]
        assert mon.EVENT_DATA_UNTRUSTED in kinds
        assert ("READY_INVALIDATED", "600001") in {(e["type"], e["symbol"]) for e in result["events"]}
        assert store.opportunities["600001"]["state"] == "INVALIDATED"

    def test_connection_lost_is_system_unavailable_not_no_trade(self, tmp_path, monitor_env, monkeypatch):
        monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: None for s in symbols})
        store = fresh_store(tmp_path)
        first = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        assert first["status"] == "SYSTEM_UNAVAILABLE"
        assert first["events"][0]["type"] == mon.EVENT_CONNECTION_LOST
        second = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        dedup = [e for e in second["events"] if e["type"] == mon.EVENT_CONNECTION_LOST]
        assert dedup == []  # one alert per day, never spam

    def test_position_exit_alerts_once_then_stays(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.open_position("600004", 10.0, 500, "2026-09-01T10:00:00", SPEC.name)
        # entry 10.0, price 10.2, close above MA5: no exit condition anywhere
        first = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        assert first["events"] == [] or all(e["type"] != mon.EVENT_POSITION_EXIT_ALERT for e in first["events"])
        QUOTES["600004"] = make_quote("600004", 9.6, 10.15)  # -4% below entry -> stop loss
        try:
            stopped = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
            assert any(e["type"] == mon.EVENT_POSITION_EXIT_ALERT and e["symbol"] == "600004" for e in stopped["events"])
            assert "stop_loss" in store.positions["open"][0]["exit_reason"]
            again = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
            assert not any(e["type"] == mon.EVENT_POSITION_EXIT_ALERT for e in again["events"])
        finally:
            QUOTES["600004"] = make_quote("600004", 10.2, 10.15)

    def test_executed_symbol_is_pinned_out_of_lifecycle(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.open_position("600001", 9.95, 500, "2026-09-01T10:00:00", SPEC.name)
        store.opportunities["600001"] = {"state": "EXECUTED", "since": "2026-09-01"}
        result = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        assert store.opportunities["600001"]["state"] == "EXECUTED"
        lifecycle = {mon.EVENT_NEW_NEAR, mon.EVENT_NEW_READY, mon.EVENT_READY_INVALIDATED}
        assert all(e["symbol"] != "600001" for e in result["events"] if e["type"] in lifecycle)


# ---------------------------------------------------------------------------
# human acknowledgement boundary
# ---------------------------------------------------------------------------


class TestAckBoundary:
    def test_buy_creates_position_executes_opportunity_and_sell_closes(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.opportunities["600001"] = {"state": "READY", "since": "2026-09-02"}
        store.save()  # materialize seeds: transactions reload from disk
        rc = mon.cmd_ack_buy(SimpleNamespace(symbol="600001", price=9.9, shares=500, time=None), store)
        assert rc == 0 and len(store.positions["open"]) == 1
        assert store.opportunities["600001"]["state"] == "EXECUTED"
        assert store.forward["observations"][-1]["kind"] == "EXECUTED"
        rc = mon.cmd_ack_sell(SimpleNamespace(symbol="600001", price=10.2, shares=500, time=None), store)
        assert rc == 0 and store.positions["open"] == [] and store.positions["closed"][0]["pnl"] == 150.0
        assert store.opportunities["600001"]["state"] == "WATCH"  # lifecycle resumes
        assert store.forward["observations"][-1]["kind"] == "CLOSED"

    def test_sell_without_position_is_rejected(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        rc = mon.cmd_ack_sell(SimpleNamespace(symbol="600999", price=10.0, shares=100, time=None), store)
        assert rc == 1 and store.positions["closed"] == []

    def test_alert_stream_separates_signal_alert_and_user_trade(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        mon.cmd_ack_buy(SimpleNamespace(symbol="600001", price=9.9, shares=500, time=None), store)
        alerts = [json.loads(l) for l in (store.dir / "alerts.jsonl").read_text().splitlines()]
        kinds = {a["type"] for a in alerts}
        assert mon.EVENT_NEW_READY in kinds and mon.EVENT_POSITION_OPENED in kinds
        opened = next(a for a in alerts if a["type"] == mon.EVENT_POSITION_OPENED)
        assert opened["data_trust"] == "USER_CONFIRMED"  # a human fact, not a system signal


class TestAckVenueNoteSkip:
    def test_buy_persists_venue_and_alert_fields(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        rc = mon.cmd_ack_buy(SimpleNamespace(
            symbol="600001", price=9.9, shares=500, time=None, venue="real", note="my entry"), store)
        assert rc == 0
        assert store.positions["open"][0]["venue"] == "real"
        alerts = [json.loads(l) for l in (store.dir / "alerts.jsonl").read_text().splitlines()]
        opened = next(a for a in alerts if a["type"] == mon.EVENT_POSITION_OPENED)
        assert opened["venue"] == "real" and opened["note"] == "my entry"
        # CLI ack alerts carry the same event contract as cycle alerts (Phase 2 §T2)
        assert opened["ts"], "CLI ack alert must carry a ts"
        assert opened["day"] == opened["ts"][:10]

    def test_sell_rejects_partial_close(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name)
        store.save()  # materialize seeds: transactions reload from disk
        rc = mon.cmd_ack_sell(SimpleNamespace(
            symbol="600001", price=10.2, shares=100, time=None, venue="real"), store)
        assert rc == 1 and len(store.positions["open"]) == 1

    def test_sell_rejects_venue_mismatch(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name, venue="paper")
        store.save()  # materialize seeds: transactions reload from disk
        rc = mon.cmd_ack_sell(SimpleNamespace(
            symbol="600001", price=10.2, shares=500, time=None, venue="real"), store)
        assert rc == 1 and len(store.positions["open"]) == 1

    def test_sell_defaults_to_position_venue_and_closes(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.open_position("600001", 9.9, 500, "2026-09-02T10:00:00", SPEC.name, venue="real")
        store.save()  # materialize seeds: transactions reload from disk
        # args without a venue attr (older CLI callers) inherit the position venue
        rc = mon.cmd_ack_sell(SimpleNamespace(
            symbol="600001", price=10.2, shares=500, time=None), store)
        assert rc == 0 and store.positions["open"] == []

    def test_skip_records_human_fact_without_touching_lifecycle(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        store.opportunities["600001"] = {"state": "READY", "since": "2026-09-02"}
        store.save()  # materialize seeds: transactions reload from disk
        rc = mon.cmd_skip(SimpleNamespace(
            symbol="600001", price=9.95, time=None, note="too extended"), store)
        assert rc == 0
        assert store.opportunities["600001"]["state"] == "READY"  # state machine untouched
        assert store.forward["observations"][-1]["kind"] == "SKIP"
        assert store.forward["observations"][-1]["ref_price"] == 9.95
        alerts = [json.loads(l) for l in (store.dir / "alerts.jsonl").read_text().splitlines()]
        skip = next(a for a in alerts if a["type"] == mon.EVENT_HUMAN_SKIP)
        assert skip["symbol"] == "600001" and skip["note"] == "too extended"
        assert skip["data_trust"] == "USER_CONFIRMED"

    def test_summary_data_trust_follows_semantic_gate_not_availability(self, tmp_path, monitor_env, monkeypatch):
        store = fresh_store(tmp_path)
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        state = json.loads((store.dir / "state.json").read_text())
        assert state["data_trust"] == "PASS"
        monkeypatch.setattr(mon, "load_volume_semantics", lambda **k: {"status": "FAIL"})
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        state = json.loads((store.dir / "state.json").read_text())
        assert state["data_trust"] == "FAIL"
        # outside the session: nothing evaluated -> UNKNOWN, never a fake verdict
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir,
                      now=datetime(2026, 9, 2, 16, 0, tzinfo=TZ_SH))
        state = json.loads((store.dir / "state.json").read_text())
        assert state["data_trust"] == "UNKNOWN" and state["system_unavailable"] is False


# ---------------------------------------------------------------------------
# fixture isolation
# ---------------------------------------------------------------------------


class TestFixtureIsolation:
    def test_fixture_run_never_touches_real_state_dir(self, tmp_path, monitor_env, monkeypatch):
        real_dir = mon.STATE_DIR
        sentinel = real_dir / "opportunities.json"
        before = sentinel.read_text() if sentinel.exists() else None
        store = fresh_store(tmp_path)
        mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        after = sentinel.read_text() if sentinel.exists() else None
        assert before == after and store.dir != real_dir

    def test_summary_distinguishes_no_trade_from_system_unavailable(self, tmp_path, monitor_env):
        store = fresh_store(tmp_path)
        ok = mon.run_cycle(store, active_cfg=monitor_env.active_cfg, spec=SPEC, state_dir=store.dir, now=NOW)
        state = json.loads((store.dir / "state.json").read_text())
        assert state["market_no_trade"] is (ok["status"] == "NO_TRADE")
        assert state["system_unavailable"] is False


# ── ledger transaction lock (concurrent ack safety) ─────────────────────────


def _ack_args(state_dir: Path, symbol: str, day: str) -> list[str]:
    """A real ack-buy CLI invocation (subprocess), like the gateway tool runs."""
    return [
        sys.executable,
        str(Path(mon.__file__)),
        "--state-dir", str(state_dir),
        "ack-buy", "--symbol", symbol, "--price", "10.0", "--shares", "100",
        "--venue", "paper", "--time", f"{day}T10:00:00+08:00",
    ]


def test_parallel_ack_buys_preserve_every_position(tmp_path):
    """pydantic-ai runs same-response tool calls concurrently, so the three
    record_trade_outcome calls behind one user message are three parallel
    ack-buy processes. The unlocked read-modify-write lost a position live
    (2026-09-07: two BUYs both got p-0001); with the ledger lock every
    position must land with a distinct id."""
    import subprocess

    procs = [
        subprocess.Popen(
            _ack_args(tmp_path, symbol, day),
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for symbol, day in (
            ("600519", "2026-09-01"), ("601799", "2026-09-02"), ("000807", "2026-09-03")
        )
    ]
    for proc in procs:
        _, stderr = proc.communicate(timeout=120)
        assert proc.returncode == 0, stderr.decode()

    positions = json.loads((tmp_path / "positions.json").read_text())
    assert sorted(p["symbol"] for p in positions["open"]) == ["000807", "600519", "601799"]
    assert len({p["id"] for p in positions["open"]}) == 3
    assert positions["next_id"] == 4


def test_ack_buy_blocks_while_ledger_lock_is_held(tmp_path):
    """The transaction lock must actually engage: a writer holding the lock
    blocks ack-buy until release; the ack then completes correctly."""
    import fcntl
    import subprocess
    import time

    lock_path = tmp_path / ".ledger.lock"
    with open(lock_path, "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        proc = subprocess.Popen(
            _ack_args(tmp_path, "600519", "2026-09-01"),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2.0)
        assert proc.poll() is None, "ack-buy must block while the ledger lock is held"
        fcntl.flock(fh, fcntl.LOCK_UN)
    assert proc.wait(timeout=120) == 0
    positions = json.loads((tmp_path / "positions.json").read_text())
    assert len(positions["open"]) == 1 and positions["open"][0]["symbol"] == "600519"
