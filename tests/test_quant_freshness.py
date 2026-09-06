"""Quant freshness derivation and response-contract tests — Quant Freshness
& Natural Response Spec v0.1 §4–§14.

Pure derivation tests (T1–T4 plus MARKET_NOT_OPEN / contradiction edges) run
against injected clocks; tool-level tests pin the freshness fields on
``get_trading_context`` output; T5–T8 pin the semantic constraints of the
quant-decision instructions (semantic assertions, never full-text
snapshots).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from zuaef_quant.freshness import (
    FRESH,
    INSUFFICIENT_EVIDENCE,
    MARKET_NOT_OPEN,
    MARKET_TZ,
    NOT_SCANNED,
    STALE,
    derive_freshness,
)
from zuaef_quant.plugin import QUANT_INSTRUCTIONS, create_plugin
from zuaef_quant.toolset import resolve_repo_root

from zuaef_agent.gateway.interaction_projection import (
    project_interaction_context,
)
from zuaef_agent.plugin_api import PluginEnv

WED = _dt.date(2026, 9, 9)  # a Wednesday


def _market_dt(day: _dt.date, hour: int, minute: int = 0) -> _dt.datetime:
    return _dt.datetime.combine(day, _dt.time(hour, minute), tzinfo=MARKET_TZ)


def _derive(now, latest, scan):
    return derive_freshness(
        now=now, latest_market_data_date=latest, last_scan_at=scan
    )


# ── T1: fresh zero ─────────────────────────────────────────────────────────


def test_t1_fresh_zero_allows_today_result_semantics():
    result = _derive(
        _market_dt(WED, 10, 30), WED.isoformat(), WED.isoformat()
    )
    assert result["freshness_status"] == FRESH
    assert result["requested_market_date"] == WED.isoformat()
    assert "today" in result["freshness_reason"]


# ── T2: stale zero ──────────────────────────────────────────────────────────


def test_t2_stale_zero_is_not_a_today_result():
    """Old READY/NEAR records must never be interpretable as 'no candidates
    today': the status is STALE and the reason names the data/scan dates."""
    result = _derive(
        _market_dt(WED, 14, 0),
        _dt.date(2026, 9, 8).isoformat(),
        _dt.date(2026, 9, 8).isoformat(),
    )
    assert result["freshness_status"] == STALE
    assert "2026-09-08" in result["freshness_reason"]
    assert "not today" in result["freshness_reason"]


# ── T3: data fresh but no scan ──────────────────────────────────────────────


def test_t3_data_present_without_scan_is_not_scanned():
    result = _derive(
        _market_dt(WED, 14, 0),
        WED.isoformat(),
        _dt.date(2026, 9, 8).isoformat(),
    )
    assert result["freshness_status"] == NOT_SCANNED
    assert "not yet" in result["freshness_reason"]


# ── T4: missing metadata fails closed ───────────────────────────────────────


def test_t4_missing_metadata_is_insufficient_evidence():
    for latest, scan in ((None, WED.isoformat()), (WED.isoformat(), None), (None, None)):
        result = _derive(_market_dt(WED, 14, 0), latest, scan)
        assert result["freshness_status"] == INSUFFICIENT_EVIDENCE
    garbage = _derive(_market_dt(WED, 14, 0), "not-a-date", WED.isoformat())
    assert garbage["freshness_status"] == INSUFFICIENT_EVIDENCE


def test_contradicted_dates_fail_closed():
    """Dates ahead of the request cannot describe the requested day."""
    future = _dt.date(2026, 9, 10).isoformat()
    result = _derive(_market_dt(WED, 14, 0), future, WED.isoformat())
    assert result["freshness_status"] == INSUFFICIENT_EVIDENCE


# ── MARKET_NOT_OPEN edges ───────────────────────────────────────────────────


def test_weekday_before_scan_window_is_market_not_open():
    result = _derive(
        _market_dt(WED, 8, 0),  # Wednesday 08:00 local
        _dt.date(2026, 9, 8).isoformat(),
        _dt.date(2026, 9, 8).isoformat(),
    )
    assert result["freshness_status"] == MARKET_NOT_OPEN


def test_weekend_before_scan_window_is_stale_not_market_not_open():
    saturday = _dt.date(2026, 9, 12)
    result = _derive(
        _market_dt(saturday, 8, 0),
        _dt.date(2026, 9, 11).isoformat(),
        _dt.date(2026, 9, 11).isoformat(),
    )
    assert result["freshness_status"] == STALE


def test_naive_timestamps_are_read_as_market_local():
    """soak/ts writers that drop the offset must not shift the market day."""
    result = _derive(
        _market_dt(WED, 14, 0),
        WED.isoformat(),
        "2026-09-09T09:47:00",  # naive — same wall clock
    )
    assert result["freshness_status"] == FRESH


# ── get_trading_context carries the freshness contract ──────────────────────


def _plugin_env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="quant",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _fake_quant_python(tmp_path: Path) -> Path:
    fake = tmp_path / "fakeenv" / "python"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    return fake


def _toolset(tmp_path: Path, monkeypatch, now: _dt.datetime):
    monkeypatch.chdir(Path(str(resolve_repo_root())))
    monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    bundle = create_plugin(_plugin_env(tmp_path), {})
    toolset = bundle.capabilities[0].toolsets[0]
    import zuaef_quant.toolset as toolset_mod

    monkeypatch.setattr(toolset_mod, "now_market", lambda: now)
    return toolset


def _write_trading_artifacts(workspace: Path, *, day: str, scan_ts: str | None):
    trading = workspace / "artifacts" / "quant" / "trading"
    trading.mkdir(parents=True, exist_ok=True)
    (trading / "state.json").write_text(
        json.dumps(
            {
                "as_of": "2026-09-04T19:10:35+08:00",
                "day": day,
                "status": "MARKET_CLOSED",
                "data_trust": None,
                "ready": [],
                "near": [],
                "exit_alerts": [],
                "market_no_trade": False,
                "system_unavailable": False,
            }
        ),
        encoding="utf-8",
    )
    soak_lines = []
    if scan_ts is not None:
        soak_lines.append(
            json.dumps({"ts": scan_ts, "status": "MARKET_CLOSED", "symbols": 50})
        )
    if soak_lines:
        (trading / "soak.jsonl").write_text("\n".join(soak_lines) + "\n", encoding="utf-8")


def test_context_reports_stale_zero_with_full_freshness_facts(
    tmp_path: Path, monkeypatch
):
    """The spec §2 live scene: request on 09-07, data through 09-04, scan
    from 09-03, READY=0/NEAR=0 — the context must say STALE, never let the
    model read it as 'no candidates today'."""
    toolset = _toolset(tmp_path, monkeypatch, _market_dt(WED, 14, 0))
    workspace = tmp_path / "workspace"
    _write_trading_artifacts(
        workspace, day="2026-09-04", scan_ts="2026-09-03T18:28:01+08:00"
    )

    data = json.loads(toolset.tools["get_trading_context"].function())

    assert data["present"] is True
    assert data["ready"] == [] and data["near"] == []
    assert data["requested_market_date"] == WED.isoformat()
    assert data["latest_market_data_date"] == "2026-09-04"
    assert data["last_scan_market_date"] == "2026-09-03"
    assert data["last_scan_at"] == "2026-09-03T18:28:01+08:00"
    assert data["market_state"] == "MARKET_CLOSED"
    assert data["freshness_status"] == STALE
    assert "not today" in data["freshness_reason"]
    assert any("freshness_status is FRESH" in line for line in data["limitations"])


def test_context_without_artifacts_fails_closed(tmp_path: Path, monkeypatch):
    toolset = _toolset(tmp_path, monkeypatch, _market_dt(WED, 14, 0))
    data = json.loads(toolset.tools["get_trading_context"].function())
    assert data["freshness_status"] == INSUFFICIENT_EVIDENCE
    assert data["last_scan_market_date"] is None


def test_context_fresh_zero(tmp_path: Path, monkeypatch):
    toolset = _toolset(tmp_path, monkeypatch, _market_dt(WED, 15, 0))
    _write_trading_artifacts(
        tmp_path / "workspace", day=WED.isoformat(), scan_ts=f"{WED.isoformat()}T10:05:00+08:00"
    )
    data = json.loads(toolset.tools["get_trading_context"].function())
    assert data["freshness_status"] == FRESH


# ── T5–T8: instruction-level semantic constraints ────────────────────────────


def test_t5_forward_zero_must_say_profitability_unverified():
    """Zero forward observations/settled samples must be reported as
    "profitability not yet verified" — the contract lives in the
    instructions (the tool already exposes the raw counts)."""
    assert "profitability is\n  not yet verified" in QUANT_INSTRUCTIONS
    assert "Zero forward observations" in QUANT_INSTRUCTIONS


def test_t5_forward_zero_forbids_positive_effectiveness_claims():
    """The weakening phrases from spec §7 appear only inside explicit
    prohibitions, never as loose guidance."""
    assert 'never "稳定/有效/胜率尚可"' in QUANT_INSTRUCTIONS


def test_t6_pit_contamination_must_not_be_softened():
    assert "never soften it" in QUANT_INSTRUCTIONS
    assert "基本可靠/影响应该不大" in QUANT_INSTRUCTIONS


def test_t7_chat_responses_default_to_natural_prose():
    assert "natural prose" in QUANT_INSTRUCTIONS
    assert "group chat" in QUANT_INSTRUCTIONS
    # wrap-tolerant: the prohibition may line-break between the words
    assert "for the sake of" in QUANT_INSTRUCTIONS
    assert "looking structured" in QUANT_INSTRUCTIONS


def test_t8_runtime_state_claims_come_from_tools_not_memory():
    assert "never from conversational memory" in QUANT_INSTRUCTIONS


def test_freshness_contract_references_host_derived_fields():
    """The instructions must route the model to the tool facts, not to
    self-derived date math."""
    assert "HOST-derived facts" in QUANT_INSTRUCTIONS
    assert "freshness_status" in QUANT_INSTRUCTIONS
    assert "absence of observation is not an observed zero" in QUANT_INSTRUCTIONS


def test_projection_stays_quant_free():
    """Spec §12 boundary: the interaction projection carries no Quant
    freshness logic — the seam is the Quant tool/context builder."""
    block = project_interaction_context("feishu", "supervisor") or ""
    for token in ("freshness", "READY", "NEAR", "scan"):
        assert token not in block
