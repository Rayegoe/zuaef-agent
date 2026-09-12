"""Narrow Intent -> Semantic Tool -> Reality tests (Domain Surface Refoundation P2).

These pin the first semantic-surface slice before any internal Quant engine
migration: each tool is bounded to one evidence scope, run_live_scan and
get_live_signals call the same scan engine, and manage_watchlist is one
verified write path shared with the legacy alias.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zuaef_agent.models import CoreDeps

pytest.importorskip("zuaef_quant")

from zuaef_quant.toolset import make_toolset

TZ = _dt.timezone(_dt.timedelta(hours=8))
NOW = _dt.datetime(2026, 9, 11, 15, 0, tzinfo=TZ)


def _toolset(tmp_path: Path, monkeypatch):
    import zuaef_quant.trading as trading_module

    # read_trading_snapshot (the P6-closure projection authority in
    # zuaef_quant.trading) is the sole now_market consumer for context reads.
    monkeypatch.setattr(trading_module, "now_market", lambda: NOW)
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return (
        make_toolset(quant_python=tmp_path / "quant-python", workspace_root=workspace),
        workspace,
    )


def _write_trading_artifacts(workspace: Path) -> None:
    trading = workspace / "artifacts" / "quant" / "trading"
    trading.mkdir(parents=True, exist_ok=True)
    (trading / "state.json").write_text(
        json.dumps(
            {
                "as_of": "2026-09-11T14:55:00+08:00",
                "day": "2026-09-11",
                "status": "ALERTS",
                "data_trust": "PASS",
                "ready": ["601799"],
                "near": ["600015"],
                "watch": ["600460"],
                "exit_alerts": ["601799"],
                "market_no_trade": False,
                "system_unavailable": False,
                "symbols_scanned": 50,
                "positions": [
                    {
                        "id": "p-0001",
                        "symbol": "601799",
                        "venue": "paper",
                        "shares": 100,
                        "entry_price": 76.32,
                        "state": "EXIT_ALERT",
                        "price": 80.10,
                        "change_pct": 1.2,
                        "exit_reason": "take_profit",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Canonical positions.json is the durable position owner; state.json only
    # carries the monitor's live projection.
    (trading / "positions.json").write_text(
        json.dumps(
            {
                "open": [
                    {
                        "id": "p-0001",
                        "symbol": "601799",
                        "venue": "paper",
                        "shares": 100,
                        "entry_price": 76.32,
                        "state": "EXIT_ALERT",
                    }
                ],
                "closed": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (trading / "forward.json").write_text(
        json.dumps(
            {
                "observations": [
                    {"kind": "EXECUTED", "symbol": "601799", "day": "2026-09-01", "d8": 0.031},
                    {"kind": "EXECUTED", "symbol": "601799", "day": "2026-09-05"},
                    {"kind": "SKIP", "symbol": "600015", "day": "2026-09-05", "d8": 0.01},
                ]
            }
        ),
        encoding="utf-8",
    )
    (trading / "soak.jsonl").write_text(
        '{"ts": "2026-09-11T09:32:00+08:00", "status": "ALERTS", "symbols": 50}\n',
        encoding="utf-8",
    )
    (trading / "alerts.jsonl").write_text(
        '{"ts": "2026-09-11T09:33:00+08:00", "type": "NEW_READY", "symbol": "601799", "what": "none -> READY"}\n',
        encoding="utf-8",
    )
    business = workspace / "artifacts" / "quant" / "business"
    business.mkdir(parents=True, exist_ok=True)
    (business / "last_scan.json").write_text(
        json.dumps({"as_of": "2026-09-11T14:55:00+08:00", "quotes_fetched": 50}),
        encoding="utf-8",
    )


def _ctx(tmp_path: Path, scope: str = "oc_group_a") -> SimpleNamespace:
    return SimpleNamespace(
        deps=CoreDeps(
            workspace_root=tmp_path / "workspace",
            run_id="run-surface-1",
            bindings={"analysis_scope": scope},
        )
    )


def test_observe_tools_are_bounded_to_one_evidence_scope(tmp_path, monkeypatch):
    toolset, workspace = _toolset(tmp_path, monkeypatch)
    _write_trading_artifacts(workspace)

    board = json.loads(toolset.tools["get_signal_board"].function())
    assert board["evidence_scope"] == "CANDIDATE_POOL"
    assert board["ready"] == ["601799"] and board["near"] == ["600015"]
    assert board["freshness_status"] == "FRESH"
    # A narrow READY/NEAR question must not load the position/validation plane.
    assert "positions" not in board
    assert "validation_accounting" not in board

    positions = json.loads(toolset.tools["get_positions"].function())
    assert positions["evidence_scope"] == "TRADING_ACCOUNT"
    assert positions["positions"][0]["symbol"] == "601799"
    assert positions["positions"][0]["price"] == 80.10
    assert positions["exit_alerts"] == ["601799"]
    # A narrow holdings question must not load the candidate board or the
    # strategy-validation block.
    assert "ready" not in positions and "near" not in positions
    assert "validation_accounting" not in positions

    validation = json.loads(toolset.tools["get_validation_status"].function())
    assert validation["evidence_scope"] == "TRADING_ACCOUNT"
    assert validation["strategy_profitability"] == "UNPROVEN"
    assert validation["pit_status"] == "CONTAMINATED"
    accounting = validation["validation_accounting"]
    assert accounting["observations"], "the ledger-derived block must be present"
    assert "ready" not in validation and "near" not in validation
    assert "positions" not in validation


def test_new_semantic_tools_and_legacy_compatibility_share_deferred_discovery(
    tmp_path, monkeypatch
):
    """P2.1-B: legacy tools keep implementation/test compatibility but no
    longer gain resident visibility over the narrow semantic surface."""
    toolset, _ = _toolset(tmp_path, monkeypatch)
    for name in (
        "get_signal_board",
        "get_positions",
        "get_validation_status",
        "run_live_scan",
        "manage_watchlist",
    ):
        assert toolset.tools[name].defer_loading is True, name
        assert callable(toolset.tools[name].function), name
    for legacy in (
        "get_trading_context",
        "get_live_signals",
    ):
        assert toolset.tools[legacy].defer_loading is True, legacy
        assert callable(toolset.tools[legacy].function), legacy


def test_run_live_scan_and_get_live_signals_share_the_same_engine(tmp_path, monkeypatch):
    import zuaef_quant.toolset as toolset_module

    toolset, _ = _toolset(tmp_path, monkeypatch)
    calls: list[tuple[str, list[str]]] = []

    def fake_run_module(module, args, quant_python, timeout):
        calls.append((module, args))
        return json.dumps({"triggers": [{"symbol": "601799"}], "universe_count": 50})

    monkeypatch.setattr(toolset_module, "_run_module", fake_run_module)
    signals = json.loads(toolset.tools["get_live_signals"].function())
    scan = json.loads(toolset.tools["run_live_scan"].function())
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert calls[0][0] == "zuaef_quant.scan_sidecar"
    assert signals["evidence_scope"] == "CANDIDATE_POOL"
    assert scan["evidence_scope"] == "CANDIDATE_POOL"
    assert signals["triggers"] == scan["triggers"] == [{"symbol": "601799"}]


def test_manage_watchlist_is_one_verified_write_interface(tmp_path, monkeypatch):
    import zuaef_quant.toolset as toolset_module

    toolset, workspace = _toolset(tmp_path, monkeypatch)
    captured: dict = {}

    def fake_run(script, args, quant_python, timeout):
        captured["args"] = args
        return json.dumps({"prewarm": {"002415": {"status": "hydrated"}}})

    monkeypatch.setattr(toolset_module, "_run_module", fake_run)
    ctx = _ctx(tmp_path)

    empty = json.loads(toolset.tools["manage_watchlist"].function(ctx, "list", None))
    assert empty["symbols"] == [] and empty["count"] == 0

    added = json.loads(toolset.tools["manage_watchlist"].function(ctx, "add", ["002415"]))
    assert added["changed"] == ["002415"] and added["verified"] is True
    assert added["history_prewarm"]["002415"]["status"] == "hydrated"
    assert captured["args"][captured["args"].index("--symbols") + 1] == "002415"

    listed = json.loads(toolset.tools["manage_watchlist"].function(ctx, "list", None))
    assert listed["symbols"] == ["002415"]

    removed = json.loads(toolset.tools["manage_watchlist"].function(ctx, "remove", ["002415"]))
    assert removed["verified"] is True
    assert (workspace / "artifacts" / "quant" / "watchlist" / "oc_group_a.json").is_file()

    bad = json.loads(toolset.tools["manage_watchlist"].function(ctx, "buy", ["002415"]))
    assert "error" in bad
