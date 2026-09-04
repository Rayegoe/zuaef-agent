"""Production contract tests for the ``zuaef-quant`` plugin (P3).

Protects the spec boundaries: whitelisted StrategySpec only (no arbitrary
Python), capability gated by profile policy, host-owned evaluator invoked in
the side environment, file-native outcome recording.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zuaef_agent.plugin_api import CompositionError, PluginEnv

pytest.importorskip("zuaef_quant")

from zuaef_quant.plugin import create_plugin, resolve_quant_python
from zuaef_quant.toolset import SpecError, validate_spec

VALID_SPEC = """\
schema = 1
name = "child_one"
universe = "csi500_subset"
max_holding_days = 5
stop_loss_pct = 0.03
take_profit_pct = 0.06
position_fraction = 0.10
max_positions = 5
entry_pullback_max = -0.05
entry_volume_ratio_min = 2.0
"""


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="quant",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _fake_quant_python(tmp_path: Path) -> Path:
    fake = tmp_path / "fakeenv" / "python"
    fake.parent.mkdir(parents=True)
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    return fake


class TestSpecValidation:
    def test_valid_spec_passes(self):
        data = validate_spec(VALID_SPEC)
        assert data["name"] == "child_one"
        assert data["entry_pullback_max"] == -0.05

    def test_unknown_key_rejected(self):
        bad = VALID_SPEC + 'evil = "import os"\n'
        with pytest.raises(SpecError, match="unknown strategy spec keys"):
            validate_spec(bad)

    def test_bad_universe_rejected(self):
        with pytest.raises(SpecError, match="universe"):
            validate_spec(VALID_SPEC.replace('universe = "csi500_subset"', 'universe = "all_a"'))

    def test_stop_must_be_below_take(self):
        with pytest.raises(SpecError, match="stop_loss_pct"):
            validate_spec(
                VALID_SPEC.replace("stop_loss_pct = 0.03", "stop_loss_pct = 0.10")
            )

    def test_fraction_bounds(self):
        with pytest.raises(SpecError, match="position_fraction"):
            validate_spec(
                VALID_SPEC.replace("position_fraction = 0.10", "position_fraction = 0.9")
            )

    def test_non_toml_rejected(self):
        with pytest.raises(SpecError, match="not valid TOML"):
            validate_spec("this is not toml [[[")


class TestPluginFactory:
    def test_missing_side_env_is_loud(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(tmp_path / "nowhere" / "python"))
        with pytest.raises(CompositionError, match="side environment missing"):
            create_plugin(_env(tmp_path), {})

    def test_bundle_has_quant_decision_capability(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        fake = _fake_quant_python(tmp_path)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(fake))
        bundle = create_plugin(_env(tmp_path), {})
        assert len(bundle.capabilities) == 1
        assert bundle.capabilities[0].id == "quant-decision"
        toolset = bundle.capabilities[0].toolsets[0]
        tools = set(toolset.tools.keys()) if hasattr(toolset, "tools") else set()
        assert {"evaluate_strategy", "get_live_signals", "record_trade_outcome"} <= tools

    def test_resolve_quant_python_prefers_env(self, tmp_path, monkeypatch):
        fake = _fake_quant_python(tmp_path)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(fake))
        assert resolve_quant_python(tmp_path) == fake


class TestRecordOutcome:
    def _toolset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        return bundle.capabilities[0].toolsets[0], env

    def test_buy_routes_to_canonical_ack_with_venue_and_note(self, tmp_path, monkeypatch):
        toolset, env = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_trade_outcome"].function
        captured = {}

        def fake_run(script, args, quant_python, timeout):
            captured["script"], captured["args"] = script, args
            return json.dumps({"position": "p-0001", "symbol": "600519", "state": "HOLD", "venue": "paper"})

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        result = json.loads(func(
            symbol="600519", action="BUY", shares=100, price=1297.4,
            venue="paper", executed_at="2026-09-04T11:07:42+08:00", notes="paper entry",
        ))
        assert result["recorded"] is True
        assert result["canonical"] == "workspace/artifacts/quant/trading/"
        assert result["ack"]["position"] == "p-0001"
        args = captured["args"]
        assert "ack-buy" in args
        assert args[args.index("--symbol") + 1] == "600519"
        assert args[args.index("--shares") + 1] == "100"
        assert args[args.index("--venue") + 1] == "paper"
        assert args[args.index("--time") + 1] == "2026-09-04T11:07:42+08:00"
        assert args[args.index("--note") + 1] == "paper entry"
        assert args[args.index("--state-dir") + 1] == str(env.workspace_root / "artifacts" / "quant" / "trading")
        # the legacy outcomes ledger is never written again
        assert not (env.workspace_root / "quant" / "outcomes.jsonl").exists()
        # a human-fact record is a LOCAL write: no approval requirement
        assert not getattr(toolset.tools["record_trade_outcome"], "requires_approval", False)

    def test_sell_routes_to_ack_sell_without_note_flag_when_empty(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_trade_outcome"].function
        captured = {}

        def fake_run(script, args, quant_python, timeout):
            captured["args"] = args
            return json.dumps({"closed": "p-0001", "pnl": 150.0, "venue": "real"})

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        result = json.loads(func(
            symbol="600519", action="SELL", shares=100, price=1320.0,
            venue="real", executed_at="2026-09-04T13:45:00+08:00",
        ))
        assert result["ack"]["closed"] == "p-0001"
        assert "ack-sell" in captured["args"] and "--note" not in captured["args"]

    def test_canonical_host_rejection_surfaces_verbatim(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_trade_outcome"].function

        def rejecting_run(script, args, quant_python, timeout):
            raise RuntimeError("canonical ack rejected the trade record: venue mismatch")

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", rejecting_run)
        with pytest.raises(RuntimeError, match="venue mismatch"):
            func(symbol="600519", action="SELL", shares=100, price=10.0,
                 venue="real", executed_at="2026-09-04T13:45:00+08:00")

    def test_invalid_action_rejected_before_side_env(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_trade_outcome"].function
        with pytest.raises(ValueError, match="action"):
            func(symbol="600519", action="BUY_NOW", shares=100, price=10.0,
                 venue="paper", executed_at="2026-09-04T13:45:00+08:00")
        with pytest.raises(ValueError, match="venue"):
            func(symbol="600519", action="BUY", shares=100, price=10.0,
                 venue="demo", executed_at="2026-09-04T13:45:00+08:00")


class TestGetTradingContext:
    def _toolset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        return bundle.capabilities[0].toolsets[0], env

    def test_absent_artifacts_are_reported_not_fabricated(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        data = json.loads(toolset.tools["get_trading_context"].function())
        assert data["present"] is False
        assert data["data_trust"] == "UNKNOWN"
        assert data["ready"] == [] and data["positions"] == []
        assert data["heartbeat_at"] is None and data["last_scan_at"] is None

    def test_bounded_context_from_canonical_artifacts(self, tmp_path, monkeypatch):
        toolset, env = self._toolset(tmp_path, monkeypatch)
        trading = env.workspace_root / "artifacts" / "quant" / "trading"
        trading.mkdir(parents=True)
        (trading / "state.json").write_text(json.dumps({
            "as_of": "2026-09-04T10:00:00+08:00", "day": "2026-09-04", "status": "ALERTS",
            "data_trust": "PASS", "ready": ["601799"], "near": ["600015"], "exit_alerts": [],
            "market_no_trade": False, "system_unavailable": False,
        }), encoding="utf-8")
        (trading / "positions.json").write_text(json.dumps({
            "open": [{"id": "p-0001", "symbol": "601799", "venue": "paper", "shares": 100,
                      "entry_price": 76.32, "state": "HOLD"}], "closed": [],
        }), encoding="utf-8")
        (trading / "forward.json").write_text(json.dumps({
            "observations": [{"kind": "EXECUTED"}, {"kind": "SKIP", "d8": 0.01}],
        }), encoding="utf-8")
        (trading / "soak.jsonl").write_text(
            '{"ts": "2026-09-04T09:31:00+08:00", "status": "MARKET_CLOSED", "symbols": 0}\n'
            '{"ts": "2026-09-04T09:47:00+08:00", "status": "ALERTS", "symbols": 50}\n', encoding="utf-8")
        (trading / "alerts.jsonl").write_text(
            '{"ts": "2026-09-04T09:47:00+08:00", "type": "NEW_READY", "symbol": "601799", "what": "none -> READY"}\n',
            encoding="utf-8")
        data = json.loads(toolset.tools["get_trading_context"].function())
        assert data["present"] is True and data["status"] == "ALERTS" and data["data_trust"] == "PASS"
        assert data["ready"] == ["601799"] and data["near"] == ["600015"]
        assert data["positions"][0]["venue"] == "paper"
        # heartbeat != last successful scan
        assert data["heartbeat_at"] == "2026-09-04T09:47:00+08:00"
        assert data["last_scan_at"] == "2026-09-04T09:47:00+08:00"
        assert data["forward"] == {"observations": 2, "settled": 1}
        assert data["recent_material_events"][0]["type"] == "NEW_READY"
        assert any("UNPROVEN" in l for l in data["limitations"])


class TestRenderBusinessArtifact:
    def test_renders_into_delivery_dir_with_bounded_summary(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        toolset = bundle.capabilities[0].toolsets[0]
        func = toolset.tools["render_quant_business_artifact"].function
        captured = {}

        def fake_run(script, args, quant_python, timeout):
            captured["script"], captured["args"] = script, args
            return "OK -> /tmp/x.html (90.2 KB, also y); decision=NO_TRADE real_records=5 m1=PARTIAL"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        result = json.loads(func())
        assert captured["script"].name == "quant_render_business_dashboard.py"
        assert "--out" in captured["args"]
        assert result["artifact"].startswith("artifacts/quant/delivery/quant-business-")
        assert not result["artifact"].startswith(str(env.workspace_root))
        assert "m1=PARTIAL" in result["summary"]


class TestEvaluateStrategy:
    def test_child_artifacts_and_bounded_evidence(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        fake = _fake_quant_python(tmp_path)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(fake))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        toolset = bundle.capabilities[0].toolsets[0]
        call = toolset.tools["evaluate_strategy"]
        func = call.function if hasattr(call, "function") else call

        def fake_run(script, args, quant_python, timeout):
            out_dir = Path(args[args.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "evidence.json").write_text(json.dumps({
                "window": {"name": "research", "start": "2018-01-01", "end": "2022-12-31"},
                "intents": {"total": 3},
                "independent_replay": {"annualized_return_pct": 1.5},
                "vector_stage": {"annualized_return_pct": 1.7},
                "blocked_trades": {},
                "consistency": {"within_tolerance": True},
            }), encoding="utf-8")
            # strategy spec must be persisted as a child artifact
            strategy_path = Path(args[args.index("--strategy") + 1])
            assert strategy_path.exists()
            return "{}"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        result = json.loads(func(
            name="child_one", entry_pullback_max=-0.05, entry_volume_ratio_min=2.0
        ))
        assert result["independent_replay"]["annualized_return_pct"] == 1.5
        assert result["consistency"]["within_tolerance"] is True
        children = list((env.workspace_root / "artifacts" / "quant" / "children").glob("*/strategy.toml"))
        assert len(children) == 1

    def test_rejects_spec_before_side_env_call(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        toolset = bundle.capabilities[0].toolsets[0]
        call = toolset.tools["evaluate_strategy"]
        func = call.function if hasattr(call, "function") else call
        with pytest.raises(SpecError, match="stop_loss_pct"):
            func(name="bad_child", stop_loss_pct=0.10, take_profit_pct=0.06)


class TestOneEvaluationPerRound:
    def test_second_evaluation_rejected(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        toolset = bundle.capabilities[0].toolsets[0]
        func = toolset.tools["evaluate_strategy"].function

        def fake_run(script, args, quant_python, timeout):
            out_dir = Path(args[args.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "evidence.json").write_text(json.dumps({
                "window": {"name": "research", "start": "2018-01-01", "end": "2022-12-31"},
                "intents": {"total": 0}, "independent_replay": {}, "vector_stage": {},
                "blocked_trades": {}, "consistency": {"within_tolerance": True},
            }), encoding="utf-8")
            return "{}"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        first = json.loads(func(name="guard_test_a"))
        assert first["intents"] == {"total": 0}
        with pytest.raises(RuntimeError, match="one evaluation per"):
            func(name="guard_test_b")

    def test_result_file_is_workspace_relative(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        toolset = bundle.capabilities[0].toolsets[0]
        func = toolset.tools["evaluate_strategy"].function

        def fake_run(script, args, quant_python, timeout):
            out_dir = Path(args[args.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "evidence.json").write_text(json.dumps({
                "window": {"name": "research", "start": "a", "end": "b"},
                "intents": {"total": 0}, "independent_replay": {}, "vector_stage": {},
                "blocked_trades": {}, "consistency": {"within_tolerance": True},
            }), encoding="utf-8")
            return "{}"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run", fake_run)
        result = json.loads(func(name="relpath_test"))
        assert not result["result_file"].startswith(str(env.workspace_root))
        assert result["result_file"].startswith("artifacts/quant/children/")


class TestRecordDecisionBrief:
    def setup_method(self):
        self.env_workspace = None

    def _toolset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
        monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
        env = _env(tmp_path)
        bundle = create_plugin(env, {})
        return bundle.capabilities[0].toolsets[0], env

    def test_brief_written_with_latency(self, tmp_path, monkeypatch):
        toolset, env = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_decision_brief"].function
        signal_ts = _dt_now_shanghai_minus(120)
        result = json.loads(func(
            decision_id="brief-test-600519",
            symbol="600519",
            action="ENTER_CANDIDATE",
            signal_timestamp=signal_ts,
            why="trigger evidence",
            invalidation="close below entry low",
            expected_holding="8 days",
            strategy_name="s3_longer_hold",
            trigger_facts="pullback -6.2%, ratio 2.1",
        ))
        assert result["recorded"] is True
        assert 110 <= result["signal_to_brief_latency_seconds"] <= 130
        brief_file = env.workspace_root / "artifacts" / "quant" / "briefs" / "brief-test-600519.json"
        assert json.loads(brief_file.read_text(encoding="utf-8"))["action"] == "ENTER_CANDIDATE"

    def test_invalid_action_rejected(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_decision_brief"].function
        with pytest.raises(ValueError, match="action"):
            func(
                decision_id="brief-test-bad",
                symbol="600519",
                action="BUY_NOW",
                signal_timestamp="2026-09-02T14:30:00+08:00",
                why="x", invalidation="x", expected_holding="x",
                strategy_name="s3_longer_hold", trigger_facts="x",
            )


def _dt_now_shanghai_minus(seconds: int) -> str:
    from datetime import datetime, timedelta, timezone
    tz = timezone(timedelta(hours=8))
    return (datetime.now(tz) - timedelta(seconds=seconds)).isoformat()
