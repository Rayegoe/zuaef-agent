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

        def fake_run(module, args, quant_python, timeout):
            captured["module"], captured["args"] = module, args
            return json.dumps({"position": "p-0001", "symbol": "600519", "state": "HOLD", "venue": "paper"})

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
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

        def fake_run(module, args, quant_python, timeout):
            captured["args"] = args
            return json.dumps({"closed": "p-0001", "pnl": 150.0, "venue": "real"})

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
        result = json.loads(func(
            symbol="600519", action="SELL", shares=100, price=1320.0,
            venue="real", executed_at="2026-09-04T13:45:00+08:00",
        ))
        assert result["ack"]["closed"] == "p-0001"
        assert "ack-sell" in captured["args"] and "--note" not in captured["args"]

    def test_canonical_host_rejection_surfaces_verbatim(self, tmp_path, monkeypatch):
        toolset, _ = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_trade_outcome"].function

        def rejecting_run(module, args, quant_python, timeout):
            raise RuntimeError("canonical ack rejected the trade record: venue mismatch")

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", rejecting_run)
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
        # D2: ledger-computed maturity replaces the old 2-field forward dict
        va = data["validation_accounting"]
        assert va["observations"] == 2
        assert va["observations_executed"] == 1 and va["observations_skipped"] == 1
        # the fixture's EXECUTED observation carries no d8 yet: accumulating
        assert va["observations_settled_full_horizon"] == 0
        assert va["observations_accumulating"] == 1
        assert va["open_positions"] == 1
        assert va["lifecycle"][0]["symbol"] == "601799"
        assert "d8" in va["limitations"][0]
        assert data["last_scan_at"] == "2026-09-04T09:47:00+08:00"
        assert "forward" not in data  # replaced by validation_accounting (D2)
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

        def fake_run(module, args, quant_python, timeout):
            captured["module"], captured["args"] = module, args
            return "OK -> /tmp/x.html (90.2 KB, also y); decision=NO_TRADE real_records=5 m1=PARTIAL"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
        result = json.loads(func())
        assert captured["module"] == "zuaef_quant.dashboard.render"
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

        def fake_run(module, args, quant_python, timeout):
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
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
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

        def fake_run(module, args, quant_python, timeout):
            out_dir = Path(args[args.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "evidence.json").write_text(json.dumps({
                "window": {"name": "research", "start": "2018-01-01", "end": "2022-12-31"},
                "intents": {"total": 0}, "independent_replay": {}, "vector_stage": {},
                "blocked_trades": {}, "consistency": {"within_tolerance": True},
            }), encoding="utf-8")
            return "{}"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
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

        def fake_run(module, args, quant_python, timeout):
            out_dir = Path(args[args.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "evidence.json").write_text(json.dumps({
                "window": {"name": "research", "start": "a", "end": "b"},
                "intents": {"total": 0}, "independent_replay": {}, "vector_stage": {},
                "blocked_trades": {}, "consistency": {"within_tolerance": True},
            }), encoding="utf-8")
            return "{}"

        import zuaef_quant.toolset as toolset_mod
        monkeypatch.setattr(toolset_mod, "_run_module", fake_run)
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

    def test_brief_writes_reply_marker_for_terminal_delivery(self, tmp_path, monkeypatch):
        """Terminal Delivery Guard (incident 9c1c9abb): the brief is the
        user-facing answer; recording it publishes the domain reply marker
        the Gateway delivers when a run ends without the model's reply."""
        toolset, env = self._toolset(tmp_path, monkeypatch)
        func = toolset.tools["record_decision_brief"].function
        func(
            decision_id="brief-20260908-1755-002415",
            symbol="002415",
            action="WATCH",
            signal_timestamp=_dt_now_shanghai_minus(30),
            why="002415今日进入NEAR带但未触发READY: 当日强度为负(-1.22%)阻断入场。",
            invalidation="强度子句转非负并触发READY -> 升级评估。",
            expected_holding="视触发而定",
            strategy_name="s3_longer_hold",
            trigger_facts="9-08扫描: READY=空, NEAR=[002415,601996]",
        )
        marker_file = env.workspace_root / "artifacts" / "quant" / "briefs" / "last-reply.json"
        marker = json.loads(marker_file.read_text(encoding="utf-8"))
        assert marker["decision_id"] == "brief-20260908-1755-002415"
        assert marker["recorded_at"]
        assert "002415：WATCH（s3_longer_hold）" in marker["text"]
        assert "阻断入场" in marker["text"]
        assert "失效条件：强度子句转非负" in marker["text"]
        assert "依据：9-08扫描" in marker["text"]
        # atomic publish: no temp residue beside the marker
        assert not list(marker_file.parent.glob(".last-reply.json.tmp"))

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


# ---------------------------------------------------------------------------
# research sandbox (CodeMode): config-gated capability, read-only data seam
# ---------------------------------------------------------------------------


class TestCodeModeSandbox:
    def test_default_composition_has_no_sandbox(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # no data/quant-cache in cwd
        bundle = create_plugin(_env(tmp_path), {})
        assert bundle.capabilities, "quant capability always present"
        from pydantic_ai_harness.code_mode import CodeMode
        assert not any(isinstance(c, CodeMode) for c in bundle.capabilities)

    def test_code_mode_disabled_by_absent_flag_even_with_cache(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "quant-cache").mkdir(parents=True)
        bundle = create_plugin(_env(tmp_path), {})
        from pydantic_ai_harness.code_mode import CodeMode
        assert not any(isinstance(c, CodeMode) for c in bundle.capabilities)

    def test_code_mode_enabled_gives_readonly_cache_mount(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cache = tmp_path / "data" / "quant-cache"
        cache.mkdir(parents=True)
        (cache / "daily").mkdir()
        bundle = create_plugin(_env(tmp_path), {"code_mode": True})
        from pydantic_ai_harness.code_mode import CodeMode
        sandboxed = [c for c in bundle.capabilities if isinstance(c, CodeMode)]
        assert len(sandboxed) == 1
        mode = sandboxed[0]
        # the five evidence tools are sandboxed as callables; the rest of the
        # agent's surface (native tools) stays untouched
        assert mode.tools == {
            "get_trading_context": True, "get_symbol_context": True,
            "get_live_signals": True, "get_analysis_watchlist": True,
            "evaluate_strategy": True,
        }
        mounts = mode.mount if isinstance(mode.mount, list) else [mode.mount]
        host_paths = [str(m.host_path) for m in mounts]
        assert any(h.endswith("data/quant-cache") for h in host_paths)
        assert all(m.mode == "read-only" for m in mounts)

    def test_code_mode_without_cache_fails_loud(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # no data/quant-cache anywhere
        with pytest.raises(CompositionError, match="data/quant-cache"):
            create_plugin(_env(tmp_path), {"code_mode": True})


def test_code_mode_sandbox_executes_real_analysis_over_mount(tmp_path, monkeypatch):
    """End-to-end sandbox proof: run_code reads the read-only history cache
    and computes a real statistic in pure Python (monty runtime). Pins the
    documented constraints: open().read() (not iteration), os.listdir (no
    pathlib.glob), no statistics module."""
    import asyncio
    import textwrap

    from pydantic_ai import Agent
    from pydantic_ai import models as pai_models
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    pai_models.ALLOW_MODEL_REQUESTS = False
    cache = tmp_path / "data" / "quant-cache" / "daily"
    cache.mkdir(parents=True)
    (cache / "000001_qfq.csv").write_text(
        "date,symbol,open,high,low,close,volume,amount,turnover\n"
        + "".join(f"2026-08-{d:02d},000001,10,10,10,10.5,1,1,1\n" for d in range(1, 11)),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    from pydantic_ai_harness import CodeMode
    from pydantic_monty import MountDir

    code = textwrap.dedent("""
        import os
        names = os.listdir("/quant-cache/daily")
        with open("/quant-cache/daily/000001_qfq.csv") as f:
            text = f.read()
        lines = text.strip().splitlines()
        header = lines[0].split(",")
        rows = [l.split(",") for l in lines[1:] if l]
        ci = header.index("close")
        closes = [float(r[ci]) for r in rows]
        up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
        print({"files": len(names), "rows": len(rows), "up_days": up})
    """)
    calls = {"n": 0}

    def fn(messages: list, info) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(parts=[ToolCallPart("run_code", {"code": code})])
        return ModelResponse(parts=[TextPart(content="done")])

    agent = Agent(FunctionModel(fn), capabilities=[CodeMode(
        mount=MountDir(virtual_path="/quant-cache", host_path=str(cache.parent), mode="read-only"),
        max_retries=3,
    )])
    result = asyncio.run(agent.run("probe"))
    returns = [
        str(p.content)
        for m in result.all_messages()
        for p in getattr(m, "parts", [])
        if getattr(p, "part_kind", "") == "tool-return"
    ]
    assert len(returns) == 1
    assert "'files': 1" in returns[0] and "'rows': 10" in returns[0] and "'up_days': 0" in returns[0]


def test_code_mode_forward_distribution_recipe_runs(tmp_path, monkeypatch):
    """T010: the quant-research skill's forward-distribution recipe runs in
    the real sandbox and reports its sample size (n) — the disclosure the
    skill contract requires. Cache: closes 10,10.5,...,14.5 — the state
    'close >= 13' hits 3 sessions; forward 1-day returns are +3.8%..+3.6%."""
    import asyncio
    import textwrap

    from pydantic_ai import Agent
    from pydantic_ai import models as pai_models
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    pai_models.ALLOW_MODEL_REQUESTS = False
    cache = tmp_path / "data" / "quant-cache" / "daily"
    cache.mkdir(parents=True)
    closes = [round(10 + 0.5 * i, 2) for i in range(10)]  # 10.0 .. 14.5
    rows = "".join(
        f"2026-08-{d + 1:02d},000001,10,10,10,{c},100000,{c * 100000},1\n"
        for d, c in enumerate(closes)
    )
    (cache / "000001_qfq.csv").write_text(
        "date,symbol,open,high,low,close,volume,amount,turnover\n" + rows,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    from pydantic_ai_harness import CodeMode
    from pydantic_monty import MountDir

    code = textwrap.dedent("""
        text = open("/quant-cache/daily/000001_qfq.csv").read()
        lines = text.strip().splitlines()
        header = lines[0].split(",")
        rows = [l.split(",") for l in lines[1:] if l]
        ci = header.index("close")
        closes = [float(r[ci]) for r in rows]
        state_th = 13.0
        horizon = 1
        fwd = []
        i = 0
        while i < len(closes):
            if closes[i] >= state_th and i + horizon < len(closes):
                fwd.append((closes[i + horizon] - closes[i]) / closes[i])
            i += 1
        n = len(fwd)
        best = 0.0
        worst = 0.0
        if n > 0:
            best = max(fwd)
            worst = min(fwd)
        print({"n": n, "best": round(best, 4), "worst": round(worst, 4)})
    """)
    calls = {"n": 0}

    def fn(messages: list, info) -> ModelResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            return ModelResponse(parts=[ToolCallPart("run_code", {"code": code})])
        return ModelResponse(parts=[TextPart(content="done")])

    agent = Agent(FunctionModel(fn), capabilities=[CodeMode(
        mount=MountDir(virtual_path="/quant-cache", host_path=str(cache.parent), mode="read-only"),
        max_retries=3,
    )])
    result = asyncio.run(agent.run("recipe probe"))
    returns = [
        str(p.content)
        for m in result.all_messages()
        for p in getattr(m, "parts", [])
        if getattr(p, "part_kind", "") == "tool-return"
    ]
    assert len(returns) == 1
    # state hit at closes 13.0, 13.5, 14.0 (14.5 has no forward bar) -> n=3
    assert "'n': 3" in returns[0]
    assert "'best': 0.0385" in returns[0] and "'worst': 0.0357" in returns[0]


def test_instructions_carry_validation_accounting_contract():
    """D2: maturity metrics are ledger facts, not prose estimates."""
    from zuaef_quant.plugin import QUANT_INSTRUCTIONS

    assert "validation_accounting" in QUANT_INSTRUCTIONS
    assert "validation_age_trading_days" in QUANT_INSTRUCTIONS
    assert "约三周多" in QUANT_INSTRUCTIONS  # the named defect stays named
    skill = (
        Path(__file__).parents[1]
        / "plugins/zuaef-quant/skills/quant-research/SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    assert "Validation accounting" in text
    assert "validation_age_trading_days" in text
    assert "still OPEN until the human executes" in text


# ---------------------------------------------------------------------------
# Evidence scope is first-class (Task Boundary Repair P3)
# ---------------------------------------------------------------------------


def _quant_toolset(tmp_path: Path, monkeypatch):
    from zuaef_quant.plugin import create_plugin

    monkeypatch.delenv("ZUAEF_QUANT_PYTHON", raising=False)
    monkeypatch.setenv("ZUAEF_QUANT_PYTHON", str(_fake_quant_python(tmp_path)))
    env = _env(tmp_path)
    bundle = create_plugin(env, {})
    return bundle.capabilities[0].toolsets[0], env


def test_candidate_and_symbol_tools_expose_evidence_scope(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import zuaef_quant.toolset as toolset_module

    from zuaef_agent.models import CoreDeps

    toolset, _ = _quant_toolset(tmp_path, monkeypatch)
    monkeypatch.setattr(
        toolset_module,
        "_run_module",
        lambda *a, **kw: json.dumps({"triggers": [], "universe_count": 50}),
    )
    live = json.loads(toolset.tools["get_live_signals"].function())
    assert live["evidence_scope"] == "CANDIDATE_POOL"
    assert live["universe_count"] == 50

    monkeypatch.setattr(
        toolset_module,
        "_run_module",
        lambda *a, **kw: json.dumps({"symbol": "600519", "quote": {}}),
    )
    ctx = SimpleNamespace(
        deps=CoreDeps(
            workspace_root=tmp_path,
            run_id="r-scope",
            bindings={"analysis_scope": "chat"},
        )
    )
    symbol = json.loads(toolset.tools["get_symbol_context"].function(ctx, "600519"))
    assert symbol["evidence_scope"] == "SINGLE_SYMBOL"

    monkeypatch.setattr(
        toolset_module,
        "_run_module",
        lambda *a, **kw: json.dumps({"symbol": "600550", "count": 0, "items": []}),
    )
    intel = json.loads(toolset.tools["get_market_intelligence"].function("600550"))
    assert intel["evidence_scope"] == "SINGLE_SYMBOL_NEWS"


def test_trading_context_exposes_scope_map_not_one_broad_claim(tmp_path, monkeypatch):
    toolset, _ = _quant_toolset(tmp_path, monkeypatch)
    data = json.loads(toolset.tools["get_trading_context"].function())
    # The projection intentionally mixes candidate-pool and account scopes,
    # so there is no valid single top-level scope.
    assert data["evidence_scope"] is None
    assert data["scope_map"] == {
        "ready": "CANDIDATE_POOL",
        "near": "CANDIDATE_POOL",
        "positions": "TRADING_ACCOUNT",
        "exit_alerts": "TRADING_ACCOUNT",
    }


def test_market_context_routes_to_side_env_and_is_market_wide(tmp_path, monkeypatch):
    import zuaef_quant.toolset as toolset_module

    toolset, _ = _quant_toolset(tmp_path, monkeypatch)
    captured: dict = {}

    def fake_run(module, args, quant_python, timeout):
        captured["module"], captured["args"], captured["timeout"] = module, args, timeout
        return json.dumps(
            {
                "as_of": "2026-09-11T15:05:00+08:00",
                "evidence_scope": "A_SHARE_MARKET_WIDE",
                "a_share": {"indices": [], "breadth": {}, "turnover": {}, "sectors": {}},
                "external": {},
                "news": [],
                "missing": [],
                "limitations": [],
            }
        )

    monkeypatch.setattr(toolset_module, "_run_module", fake_run)
    tool = toolset.tools["get_market_context"]
    out = json.loads(tool.function())
    assert captured["module"] == "zuaef_quant.market_context"
    assert captured["args"] == []
    assert out["evidence_scope"] == "A_SHARE_MARKET_WIDE"
    assert tool.defer_loading is True

    # CJK discovery vocabulary required by P2.4 must be present in the
    # ToolSearch description (no hand-written keyword router).
    description = tool.description or ""
    for term in (
        "A股", "大盘", "市场", "全市场", "今天", "为什么", "跌", "大跌",
        "暴跌", "普跌", "上涨", "下跌", "板块", "行业", "原因", "宏观",
        "外盘", "亚洲股市", "原油", "利率", "美债", "美元", "风险偏好",
    ):
        assert term in description, term


def test_scope_invariant_instructions_and_market_recipe():
    from zuaef_quant.plugin import QUANT_INSTRUCTIONS

    assert "A claim's scope may never exceed the scope of the evidence supporting it." in QUANT_INSTRUCTIONS
    assert "Prediction alignment is not causal validation." in QUANT_INSTRUCTIONS
    assert "Previous assistant prose is not evidence." in QUANT_INSTRUCTIONS
    assert "get_market_context exactly once" in QUANT_INSTRUCTIONS
    assert "OBSERVED" in QUANT_INSTRUCTIONS
    assert "INTERPRETATION" in QUANT_INSTRUCTIONS
    assert "UNKNOWN" in QUANT_INSTRUCTIONS
    skill = (
        Path(__file__).parents[1]
        / "plugins/zuaef-quant/skills/quant-research/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "get_market_context` exactly once" in skill
    assert "A claim's scope may never exceed the scope of the evidence supporting it." in skill
    assert "A股普跌" in skill  # explicit forbidden overgeneralization


def test_adversarial_scope_fixture_cannot_authorise_market_claim(tmp_path, monkeypatch):
    """Gate C fixture: candidate pool 45/50 down, market-wide up 3000/down 1800.

    The host surfaces the contradictory scopes as first-class fields; the
    instructions and skill make "A股普跌" claimable only from market-wide
    evidence.  Model wording itself is pinned by the real-model canary.
    """
    import zuaef_quant.toolset as toolset_module

    toolset, _ = _quant_toolset(tmp_path, monkeypatch)
    monkeypatch.setattr(
        toolset_module,
        "_run_module",
        lambda *a, **kw: json.dumps(
            {"triggers": [], "universe_count": 50, "down": 45, "up": 5}
        ),
    )
    candidate = json.loads(toolset.tools["get_live_signals"].function())
    assert candidate["evidence_scope"] == "CANDIDATE_POOL"

    market_payload = {
        "as_of": "2026-09-11T15:05:00+08:00",
        "evidence_scope": "A_SHARE_MARKET_WIDE",
        "a_share": {"breadth": {"up": 3000, "down": 1800}},
    }
    assert candidate["evidence_scope"] != market_payload["evidence_scope"]
    assert market_payload["a_share"]["breadth"]["up"] > market_payload["a_share"]["breadth"]["down"]
    assert candidate["down"] > candidate["up"]
    # Host evidence does not claim market-wide direction from candidate data.
    assert "evidence_scope" in candidate and candidate["evidence_scope"] == "CANDIDATE_POOL"
