"""P5 operator CLI contract tests (deterministic, zero-model).

The CLI is allowed to orchestrate domain authorities; it must not contain
scan/watchlist/monitor business calculations of its own.  These tests pin the
small command tree, the shared watchlist write path, bounded JSON output and
the scan delegation to the domain-owned sidecar rather than the historical
tools/ script.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from zuaef_quant import ops

TOP_LEVEL = {"status", "scan", "watchlist", "monitor", "dashboard", "bridge"}


def test_top_level_command_tree_stays_small_and_intent_named(capsys):
    with pytest.raises(SystemExit) as exc:
        ops.main(["--help"])
    assert exc.value.code == 0
    text = capsys.readouterr().out
    for command in TOP_LEVEL:
        assert command in text
    for forbidden in ("ask", "analyze", "service", "run_code"):
        assert forbidden not in text


def test_status_json_is_bounded_and_never_model_backed(monkeypatch, capsys):
    payload = {
        "market_date": "2026-09-11",
        "market_state": "ALERTS",
        "freshness_status": "FRESH",
        "freshness_reason": "today",
        "last_scan_at": "2026-09-11T15:00:00+08:00",
        "ready": 2,
        "near": 5,
        "open_positions": 1,
        "exit_alert_count": 0,
        "data_trust": "PASS",
        "validation": {"observations": 4},
        "monitor": {"status": "ALERTS", "market_phase": "OPEN_PM", "heartbeat_at": "t"},
        "dashboard": {"present": False, "rendered_at": None},
    }
    monkeypatch.setattr(ops, "_status_payload", lambda: payload)
    assert ops.main(["status", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out == payload


def test_scan_uses_domain_sidecar_module_not_root_script(monkeypatch, tmp_path):
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps({"triggers": [], "universe_size": 50}), stderr="")

    monkeypatch.setattr(ops, "_quant_python", lambda: Path("/fake/quant/python"))
    monkeypatch.setattr(ops, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ops, "_side_env", lambda: {"PYTHONPATH": "/fake/plugins"})
    monkeypatch.setattr(ops.subprocess, "run", fake_run)
    args = SimpleNamespace(max_triggers=10, universe_file=None, json=True)
    payload = ops._scan_sidecar(args)
    assert payload == {"triggers": [], "universe_size": 50}
    cmd = captured["cmd"]
    assert cmd[1:3] == ["-m", "zuaef_quant.scan_sidecar"]
    assert "quant_live_scan.py" not in " ".join(cmd)
    assert captured["kwargs"]["cwd"] == str(tmp_path)


def test_scan_human_output_is_small(monkeypatch, capsys):
    monkeypatch.setattr(
        ops,
        "_scan_sidecar",
        lambda args: {
            "as_of": "2026-09-11T15:00:00+08:00",
            "universe": "candidate_pool_active",
            "universe_size": 50,
            "quotes_fetched": 50,
            "triggers": [{"symbol": "600001"}],
            "volume_semantics": {"status": "PASS"},
        },
    )
    assert ops.main(["scan"]) == 0
    out = capsys.readouterr().out
    assert "Scan completed" in out
    assert "READY triggers: 1" in out
    assert "{" not in out


def test_watchlist_mutations_share_the_domain_store(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(ops, "_workspace_root", lambda: workspace)

    assert ops.main(["watchlist", "add", "002415", "--scope", "ops-test"]) == 0
    out = capsys.readouterr().out
    assert "Watchlist add verified" in out
    path = workspace / "artifacts" / "quant" / "watchlist" / "ops-test.json"
    assert json.loads(path.read_text(encoding="utf-8"))["symbols"] == ["002415"]

    assert ops.main(["watchlist", "list", "--scope", "ops-test", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["symbols"] == ["002415"] and listed["count"] == 1

    assert ops.main(["watchlist", "remove", "002415", "--scope", "ops-test"]) == 0
    removed = json.loads((workspace / "artifacts" / "quant" / "watchlist" / "ops-test.json").read_text(encoding="utf-8"))
    assert removed["symbols"] == []


def test_watchlist_without_scope_fails_closed(monkeypatch, capsys):
    monkeypatch.delenv(ops.OPERATOR_SCOPE_ENV, raising=False)
    assert ops.main(["watchlist", "list"]) == 1
    err = capsys.readouterr().err
    assert "scope is not configured" in err


def test_watchlist_scope_can_come_from_existing_env(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(ops, "_workspace_root", lambda: workspace)
    monkeypatch.setenv(ops.OPERATOR_SCOPE_ENV, "ops-env")
    assert ops.main(["watchlist", "add", "600519", "--json"]) == 0
    payload = json.loads((workspace / "artifacts" / "quant" / "watchlist" / "ops-env.json").read_text(encoding="utf-8"))
    assert payload["scope"] == "ops-env"


def test_monitor_once_and_status_delegate_to_shared_projection(monkeypatch, capsys):
    monkeypatch.setattr(
        ops,
        "_monitor_once_payload",
        lambda *a, **k: {"status": "NO_TRADE", "symbols": 50, "events": []},
    )
    assert ops.main(["monitor", "once"]) == 0
    assert "Monitor tick completed" in capsys.readouterr().out

    status = {
        "market_date": "2026-09-11",
        "market_state": "NO_TRADE",
        "freshness_status": "FRESH",
        "last_scan_at": "2026-09-11T15:00:00+08:00",
        "open_positions": 0,
        "exit_alert_count": 0,
        "monitor": {"status": "NO_TRADE", "market_phase": "OPEN_PM", "heartbeat_at": "t", "symbols_scanned": 50},
    }
    monkeypatch.setattr(ops, "_status_payload", lambda: status)
    assert ops.main(["monitor", "status", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["monitor"]["status"] == "NO_TRADE"


def test_dashboard_and_bridge_commands_delegate(monkeypatch, tmp_path):
    captured: list[list[str]] = []

    def fake_capture(cmd, **kwargs):
        captured.append(cmd)
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(ops, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ops, "_run_capture", fake_capture)
    assert ops.main(["dashboard", "render", "--out", str(tmp_path / "out.html")]) == 0
    assert captured[0][1:3] == ["-m", "zuaef_quant.dashboard.render"]
    assert ops.main(["bridge", "once"]) == 0
    assert captured[1][1:3] == ["-m", "zuaef_quant.bridge"]
    assert captured[1][0]


def test_migrated_systemd_entries_use_the_operator_cli():
    repo = Path(__file__).parents[1]
    dashboard = (repo / "ops" / "systemd" / "zuaef-quant-dashboard.service").read_text(encoding="utf-8")
    bridge = (repo / "ops" / "systemd" / "zuaef-quant-bridge.service").read_text(encoding="utf-8")
    monitor = (repo / "ops" / "systemd" / "zuaef-quant-monitor.service").read_text(encoding="utf-8")
    installer = (repo / "ops" / "install_orangepi_node.sh").read_text(encoding="utf-8")
    assert "ExecStart=%h/zuaef-agent/.venv/bin/zuaef-quant dashboard serve" in dashboard
    assert "ExecStart=%h/zuaef-agent/.venv/bin/zuaef-quant bridge once" in bridge
    assert ".venv-quant/bin/python -m zuaef_quant.monitor session" in monitor
    assert ".venv/bin/zuaef-quant monitor once" in installer
    assert ".venv/bin/zuaef-quant bridge once --dry-run" in installer


def test_monitor_once_uses_domain_module_not_root_script(monkeypatch):
    captured: dict = {}

    def fake_capture(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout=json.dumps({"status": "NO_TRADE", "events": []}), stderr="")

    monkeypatch.setattr(ops, "_quant_python", lambda: Path("/fake/quant/python"))
    monkeypatch.setattr(ops, "_repo_root", lambda: Path("/fake/repo"))
    monkeypatch.setattr(ops, "_side_env", lambda: {"PYTHONPATH": "/fake/plugins"})
    monkeypatch.setattr(ops, "_run_capture", fake_capture)
    payload = ops._monitor_once_payload()
    assert payload["status"] == "NO_TRADE"
    assert captured["cmd"][1:4] == ["-m", "zuaef_quant.monitor", "once"]
    assert "quant_trading_monitor.py" not in captured["cmd"]


def test_extracted_authority_modules_do_not_depend_on_root_wrappers():
    """P5.8 static authority gate: plugin monitor/bridge must not import or
    spawn the historical root implementation scripts."""
    plugin_dir = Path(__file__).parents[1] / "plugins" / "zuaef-quant" / "zuaef_quant"
    monitor_source = (plugin_dir / "monitor.py").read_text(encoding="utf-8")
    bridge_source = (plugin_dir / "bridge.py").read_text(encoding="utf-8")
    for source in (monitor_source, bridge_source):
        assert "quant_trading_monitor" not in source
        assert "quant_telegram_bridge" not in source
        assert "tools/quant_trading_monitor.py" not in source
        assert "tools/quant_telegram_bridge.py" not in source

    repo = Path(__file__).parents[1]
    assert not (repo / "tools" / "quant_trading_monitor.py").exists()
    assert not (repo / "tools" / "quant_telegram_bridge.py").exists()

    toolset_source = (plugin_dir / "toolset.py").read_text(encoding="utf-8")
    ops_source = (plugin_dir / "ops.py").read_text(encoding="utf-8")
    assert "quant_trading_monitor.py" not in toolset_source
    assert "quant_trading_monitor.py" not in ops_source
    assert "quant_telegram_bridge.py" not in ops_source
    assert '_run_module("zuaef_quant.monitor"' in toolset_source
    assert '"zuaef_quant.monitor"' in ops_source
    assert '"zuaef_quant.bridge"' in ops_source
