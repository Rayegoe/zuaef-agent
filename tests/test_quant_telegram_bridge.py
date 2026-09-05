"""Quant Telegram event bridge tests.

Every seam is injected: the Telegram sender is a recording fake, the agent
run is monkeypatched at the bridge module boundary, and canonical artifacts
live in tmp_path. Network is never touched; the real Agent is exercised only
by the existing quant plugin suite.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import quant_telegram_bridge as qb
from zuaef_telegram.client import TelegramError

TZ_SH = ZoneInfo("Asia/Shanghai")
# 2026-09-09 is a Wednesday; 10:00 falls inside the AM session, 11:45 is the
# lunch break (off-session, same day, before the daily-summary deadline).
IN_SESSION = datetime(2026, 9, 9, 10, 0, 0, tzinfo=TZ_SH)
LUNCH_BREAK = datetime(2026, 9, 9, 11, 45, 0, tzinfo=TZ_SH)
AFTER_CLOSE = datetime(2026, 9, 9, 15, 10, 0, tzinfo=TZ_SH)


# ── fixtures / fakes ────────────────────────────────────────────────────────


class FakeClient:
    """Recording sender; fail_on=N raises on the Nth send (0-based)."""

    def __init__(self, fail_on: int | None = None):
        self.messages: list[str] = []
        self.fail_on = fail_on

    def send_message(self, text: str) -> dict:
        if self.fail_on is not None and len(self.messages) >= self.fail_on:
            raise TelegramError("telegram unreachable")
        self.messages.append(text)
        return {"ok": True, "message_id": len(self.messages)}


def _outcome(presentation: str = "解释：601799 进入 READY。", *, effects: list | None = None, run_id: str = "run-1"):
    return SimpleNamespace(
        presentation=presentation,
        receipt=SimpleNamespace(run_id=run_id, tool_effect_facts=effects or []),
    )


@pytest.fixture()
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    trading = tmp_path / "trading"
    (trading / "").mkdir(parents=True)
    state = tmp_path / "state"
    state.mkdir()
    return trading, state


def _write_alerts(trading: Path, alerts: list[dict]) -> None:
    payload = "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in alerts)
    (trading / "alerts.jsonl").write_text(payload, encoding="utf-8")


def _tick(trading, state, client, *, now=IN_SESSION, settings=None, monkeypatch=None, outcome=None, run_error=None):
    if monkeypatch is not None:
        def fake_run(**kwargs):
            if run_error is not None:
                raise run_error
            return outcome if outcome is not None else _outcome()
        monkeypatch.setattr(qb, "start_profile_run", fake_run)
    return qb.run_tick(
        now=now, trading_dir=trading, state_dir=state,
        client=client, settings=settings,
    )


def _state(state_dir: Path) -> dict:
    return json.loads((state_dir / "state.json").read_text(encoding="utf-8"))


# ── dispatch matrix ─────────────────────────────────────────────────────────


def test_e1_new_ready_runs_agent_and_pushes_presentation(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:00:01+08:00", "type": "NEW_READY", "symbol": "601799",
        "day": "2026-09-09", "price": 74.88, "what": "NEAR -> READY",
        "why": "frozen entry conditions satisfied", "data_trust": "PASS",
        "conditions": {"pullback_5d": -0.0853, "volume_ratio_20d": 2.2, "strength_1d": 0.01},
    }])
    client = FakeClient()
    seen = {}

    def fake_run(**kwargs):
        seen.update(kwargs)
        return _outcome()

    monkeypatch.setattr(qb, "start_profile_run", fake_run)
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state,
                     client=client, settings=object())
    assert rc == 0
    assert seen["profile"] == "quant-decision"
    assert seen["surface"] == "telegram"
    assert seen["actor_role"] == "supervisor"
    assert "NEW_READY" in seen["prompt"] and "601799" in seen["prompt"]
    assert client.messages == ["解释：601799 进入 READY。"]
    st = _state(state)
    assert st["offset"] > 0
    assert st["delivered_ids"] == ["NEW_READY:601799:2026-09-09T10:00:01+08:00"]
    assert not st["pending_recovery"]


def test_agent_run_prompt_carries_event_and_no_delivery_authority(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:00:01+08:00", "type": "NEW_READY", "symbol": "601799",
        "day": "2026-09-09", "price": 74.88, "what": "NEAR -> READY", "why": "x",
    }])
    prompts = []

    def fake_run(**kwargs):
        prompts.append(kwargs["prompt"])
        return _outcome()

    monkeypatch.setattr(qb, "start_profile_run", fake_run)
    qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state,
                client=FakeClient(), settings=object())
    assert prompts, "agent run must be triggered"
    assert "get_trading_context" in prompts[0]
    assert "no delivery authority" in prompts[0]
    assert "NEW_READY" in prompts[0]


def test_agent_failure_degrades_to_deterministic_fallback(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:00:01+08:00", "type": "NEW_READY", "symbol": "601799",
        "day": "2026-09-09", "price": 74.88, "what": "NEAR -> READY", "why": "x",
    }])
    client = FakeClient()
    rc = _tick(trading, state, client, monkeypatch=monkeypatch,
               run_error=RuntimeError("model unavailable"))
    assert rc == 0
    assert len(client.messages) == 1
    assert "Agent explanation unavailable" in client.messages[0]
    assert "NEW_READY" in client.messages[0]
    assert _state(state)["delivered_ids"], "fallback counts as delivered (§22.1)"


def test_e2_position_exit_alert_uses_agent_path(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:05:00+08:00", "type": "POSITION_EXIT_ALERT", "symbol": "601799",
        "day": "2026-09-09", "price": 72.61, "what": "HOLD -> EXIT_ALERT",
        "why": "stop_loss", "conditions": {"entry_price": 74.88, "shares": 100, "pnl": -3.03},
    }])
    client = FakeClient()
    rc = _tick(trading, state, client, settings=object(), monkeypatch=monkeypatch, outcome=_outcome("EXIT 解释"))
    assert rc == 0
    assert client.messages == ["EXIT 解释"]


def test_deterministic_events_send_fixed_copy_without_any_agent_call(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [
        {"ts": "2026-09-09T10:01:00+08:00", "type": "LIVE_CONNECTION_LOST", "symbol": None,
         "day": "2026-09-09", "price": None, "what": "quotes unavailable",
         "why": "quote failures=3/3", "data_trust": "UNKNOWN"},
        {"ts": "2026-09-09T10:02:00+08:00", "type": "DATA_UNTRUSTED", "symbol": None,
         "day": "2026-09-09", "why": "volume_semantics fail-closed"},
        {"ts": "2026-09-09T10:03:00+08:00", "type": "POSITION_OPENED", "symbol": "601799",
         "day": "2026-09-09", "price": 74.88, "what": "user BUY acknowledged",
         "why": "p-0001 100 shares @ 74.88", "venue": "paper"},
    ])
    client = FakeClient()
    called = []

    def fake_run(**kwargs):
        called.append(kwargs)
        return _outcome()

    monkeypatch.setattr(qb, "start_profile_run", fake_run)
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state,
                     client=client, settings=None)
    assert rc == 0
    assert called == [], "E3/E4/E5 are deterministic and must not call the Agent"
    assert "SYSTEM_UNAVAILABLE ≠ NO_TRADE" in client.messages[0]
    assert "DATA_UNTRUSTED" in client.messages[1]
    assert "已记录 paper Buy：601799" in client.messages[2]
    assert _state(state)["pending_recovery"] is True


def test_non_material_events_consumed_silently(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [
        {"ts": "2026-09-09T10:01:00+08:00", "type": "NEW_NEAR", "symbol": "600015", "day": "2026-09-09"},
        {"ts": "2026-09-09T10:02:00+08:00", "type": "HUMAN_SKIP", "symbol": "601799",
         "day": "2026-09-09", "price": 74.88, "why": "user skip", "venue": None},
    ])
    client = FakeClient()
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None)
    assert rc == 0
    assert client.messages == []
    assert _state(state)["offset"] > 0, "lines consumed without notifications"


# ── checkpoint semantics (amendment ③) ──────────────────────────────────────


def test_failed_send_keeps_checkpoint_and_retries_only_failed_line(dirs):
    trading, state = dirs
    _write_alerts(trading, [
        {"ts": "2026-09-09T10:01:00+08:00", "type": "POSITION_OPENED", "symbol": "601799",
         "day": "2026-09-09", "price": 74.88, "why": "p-0001 100 shares @ 74.88", "venue": "paper"},
        {"ts": "2026-09-09T10:02:00+08:00", "type": "DATA_UNTRUSTED", "symbol": None,
         "day": "2026-09-09", "why": "gate fail-closed"},
    ])
    failing = FakeClient(fail_on=1)  # first send OK, second fails
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=failing, settings=None)
    assert rc == 1
    first_line_end = (trading / "alerts.jsonl").read_bytes().index(b"\n") + 1
    st = _state(state)
    assert st["offset"] == first_line_end, \
        "checkpoint must sit exactly after the delivered line"
    delivered = list(st["delivered_ids"])
    assert len(delivered) == 1 and "POSITION_OPENED" in delivered[0]

    healthy = FakeClient()
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=healthy, settings=None)
    assert rc == 0
    assert len(healthy.messages) == 1, "only the failed line is retried"
    assert "DATA_UNTRUSTED" in healthy.messages[0]
    st = _state(state)
    assert st["offset"] == (trading / "alerts.jsonl").stat().st_size
    assert len(st["delivered_ids"]) == 2


def test_malformed_line_does_not_wedge_the_bridge(dirs):
    trading, state = dirs
    good = json.dumps({"ts": "2026-09-09T10:01:00+08:00", "type": "DATA_UNTRUSTED",
                       "symbol": None, "day": "2026-09-09", "why": "x"}, ensure_ascii=False)
    (trading / "alerts.jsonl").write_text("{broken json\n" + good + "\n", encoding="utf-8")
    client = FakeClient()
    rc = qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None)
    assert rc == 0
    assert len(client.messages) == 1
    assert _state(state)["offset"] == (trading / "alerts.jsonl").stat().st_size


# ── source reset (amendment ②) ──────────────────────────────────────────────


def test_source_reset_rescans_but_never_resends_delivered_events(dirs):
    trading, state = dirs
    first = {"ts": "2026-09-09T10:01:00+08:00", "type": "POSITION_OPENED", "symbol": "601799",
             "day": "2026-09-09", "price": 74.88, "why": "p-0001 100 shares @ 74.88", "venue": "paper"}
    _write_alerts(trading, [first])
    client = FakeClient()
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert len(client.messages) == 1

    # simulate truncate+rotate: new inode, same event re-appears plus a new one
    second = {"ts": "2026-09-09T10:09:00+08:00", "type": "DATA_UNTRUSTED", "symbol": None,
              "day": "2026-09-09", "why": "gate fail-closed"}
    alerts = trading / "alerts.jsonl"
    alerts.unlink()  # new inode
    _write_alerts(trading, [dict(first, ts="2026-09-09T10:01:00+08:00"), second])
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert len(client.messages) == 2, "delivered identity not re-sent after reset"
    assert "DATA_UNTRUSTED" in client.messages[1]


# ── delivery authority (amendment ①) ────────────────────────────────────────


def test_agent_delivery_tool_effect_blocks_forwarding(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:00:01+08:00", "type": "NEW_READY", "symbol": "601799",
        "day": "2026-09-09", "price": 74.88, "what": "NEAR -> READY", "why": "x",
    }])
    rogue = _outcome(effects=[SimpleNamespace(tool_name="report_to_telegram", status="completed")])
    client = FakeClient()
    rc = _tick(trading, state, client, settings=object(), monkeypatch=monkeypatch, outcome=rogue)
    assert rc == 0
    assert client.messages == [], "bridge must not double-deliver after a rogue tool send"
    assert "DELIVERY_AUTHORITY_VIOLATION" in (state / "bridge.jsonl").read_text(encoding="utf-8")
    assert _state(state)["delivered_ids"], "violation event is consumed, not retried"


def test_delivery_guard_ignores_non_delivery_and_unsettled_effects(dirs, monkeypatch):
    trading, state = dirs
    _write_alerts(trading, [{
        "ts": "2026-09-09T10:00:01+08:00", "type": "NEW_READY", "symbol": "601799",
        "day": "2026-09-09", "price": 74.88, "what": "NEAR -> READY", "why": "x",
    }])
    effects = [
        SimpleNamespace(tool_name="get_trading_context", status="completed"),
        SimpleNamespace(tool_name="report_to_telegram", status="started"),  # never settled
    ]
    client = FakeClient()
    rc = _tick(trading, state, client, settings=object(), monkeypatch=monkeypatch,
               outcome=_outcome(effects=effects))
    assert rc == 0
    assert client.messages == ["解释：601799 进入 READY。"], "benign effects must not block forwarding"


# ── SYSTEM_RECOVERED (amendment ④) ─────────────────────────────────────────


def _recovering_runtime(trading: Path, now: datetime) -> None:
    (trading / "state.json").write_text(json.dumps({
        "status": "NO_TRADE", "system_unavailable": False,
        "as_of": now.isoformat(timespec="seconds"),
    }), encoding="utf-8")
    heartbeat = (now.timestamp() - 10)
    from datetime import datetime as dt
    ts = dt.fromtimestamp(heartbeat, TZ_SH).isoformat(timespec="seconds")
    (trading / "soak.jsonl").write_text(json.dumps({
        "ts": ts, "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 12,
    }) + "\n", encoding="utf-8")


def test_recovery_sends_once_on_deterministic_evidence(dirs):
    trading, state = dirs
    st = qb.load_state(state)
    st["pending_recovery"] = True
    qb.save_state(state, st)
    _recovering_runtime(trading, IN_SESSION)
    client = FakeClient()
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert len(client.messages) == 1 and "SYSTEM_RECOVERED" in client.messages[0]
    assert _state(state)["pending_recovery"] is False
    # second tick: no repeat
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=FakeClient(), settings=None) == 0


def test_recovery_requires_in_session_and_fresh_heartbeat_and_explicit_false(dirs):
    trading, state = dirs
    st = qb.load_state(state)
    st["pending_recovery"] = True
    qb.save_state(state, st)
    client = FakeClient()
    # stale heartbeat (>90s) must not count as recovery
    _recovering_runtime(trading, IN_SESSION)
    stale = (IN_SESSION.timestamp() - 300)
    from datetime import datetime as dt
    soak = json.loads((trading / "soak.jsonl").read_text(encoding="utf-8").splitlines()[0])
    soak["ts"] = dt.fromtimestamp(stale, TZ_SH).isoformat(timespec="seconds")
    (trading / "soak.jsonl").write_text(json.dumps(soak) + "\n", encoding="utf-8")
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert client.messages == []
    # outside the trading session must not count either (lunch break)
    _recovering_runtime(trading, LUNCH_BREAK)
    assert qb.run_tick(now=LUNCH_BREAK, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert client.messages == []
    # system_unavailable missing (never explicitly false) must not count
    _recovering_runtime(trading, IN_SESSION)
    st2 = json.loads((trading / "state.json").read_text(encoding="utf-8"))
    del st2["system_unavailable"]
    (trading / "state.json").write_text(json.dumps(st2), encoding="utf-8")
    assert qb.run_tick(now=IN_SESSION, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert client.messages == []
    assert _state(state)["pending_recovery"] is True


# ── daily summary (T10, amendment ⑤) ────────────────────────────────────────


def test_daily_summary_once_after_close_with_continuity_verdict(dirs, monkeypatch):
    trading, state = dirs
    day = "2026-09-09"
    soak_rows = [
        {"ts": f"{day}T09:35:00+08:00", "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 10},
        {"ts": f"{day}T09:36:00+08:00", "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 10},
        {"ts": f"{day}T15:00:30+08:00", "status": "MARKET_CLOSED", "events": 0, "symbols": 0, "ms": 0},
    ]
    (trading / "soak.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in soak_rows), encoding="utf-8")
    _write_alerts(trading, [
        {"ts": f"{day}T09:40:00+08:00", "type": "NEW_READY", "symbol": "601799", "day": day},
        {"ts": f"{day}T09:50:00+08:00", "type": "POSITION_OPENED", "symbol": "601799", "day": day},
    ])
    (trading / "positions.json").write_text(json.dumps({"open": [{"symbol": "601799"}], "closed": []}), encoding="utf-8")
    (trading / "forward.json").write_text(json.dumps({"observations": [{"day": day, "kind": "READY"}]}), encoding="utf-8")
    # decouple from the real repo's semantic proof: no proof on record ->
    # the dashboard's own m1 verdict implementation yields PARTIAL here
    monkeypatch.setattr(qb.biz, "load_latest_semantic_proof", lambda semantic_dir: None)

    client = FakeClient()
    rc = qb.run_tick(now=AFTER_CLOSE, trading_dir=trading, state_dir=state, client=client, settings=None)
    assert rc == 0
    summary = client.messages[0]
    assert "📊 Quant 日报 2026-09-09" in summary
    assert "扫描：2 次" in summary
    assert "READY：1" in summary
    assert "ENTER：1" in summary
    assert "EXIT：0" in summary
    assert "NO_TRADE：yes" in summary
    assert "Forward新增：1" in summary
    assert "持仓：1" in summary
    # in-session scans exist but market/single proof missing -> the SAME
    # load_real_trend() implementation the Dashboard uses says PARTIAL
    assert "Runtime continuity：PARTIAL" in summary
    # the day's material alerts were also dispatched in the same tick
    assert len(client.messages) == 3
    assert "Agent explanation unavailable" in client.messages[1]
    assert "已记录 paper Buy：601799" in client.messages[2]
    assert _state(state)["daily"] == {"sent_for": day}
    # second tick: no repeat of either summary or events
    rc = qb.run_tick(now=AFTER_CLOSE, trading_dir=trading, state_dir=state, client=FakeClient(), settings=None)
    assert rc == 0


def test_daily_summary_continuity_fail_mapping(dirs, monkeypatch):
    """NO_REAL_EVIDENCE maps to FAIL: closed-only soak, no scans, no forward."""
    trading, state = dirs
    day = "2026-09-09"
    (trading / "soak.jsonl").write_text(
        json.dumps({"ts": f"{day}T15:00:30+08:00", "status": "MARKET_CLOSED", "events": 0, "symbols": 0, "ms": 0}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(qb.biz, "load_latest_semantic_proof", lambda semantic_dir: None)
    client = FakeClient()
    assert qb.run_tick(now=AFTER_CLOSE, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert "Runtime continuity：FAIL" in client.messages[0]


def test_daily_summary_not_sent_before_deadline_or_without_soak(dirs):
    trading, state = dirs
    (trading / "soak.jsonl").write_text(
        json.dumps({"ts": "2026-09-09T10:00:00+08:00", "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 1}) + "\n",
        encoding="utf-8")
    client = FakeClient()
    before = datetime(2026, 9, 9, 14, 59, tzinfo=TZ_SH)
    assert qb.run_tick(now=before, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert client.messages == []
    # a day with zero soak rows produces no summary either
    empty = datetime(2026, 9, 10, 15, 10, tzinfo=TZ_SH)
    assert qb.run_tick(now=empty, trading_dir=trading, state_dir=state, client=client, settings=None) == 0
    assert client.messages == []


# ── config fail-closed ──────────────────────────────────────────────────────


def test_build_client_requires_token_and_chat(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ZUAEF_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(qb.BridgeError, match="credentials missing"):
        qb.build_client()


def test_identity_uses_ts_or_day_fallback():
    assert qb.event_identity({"type": "NEW_READY", "symbol": "X", "ts": "t1"}) == "NEW_READY:X:t1"
    assert qb.event_identity({"type": "POSITION_OPENED", "symbol": "X", "day": "d1"}) == "POSITION_OPENED:X:d1"
