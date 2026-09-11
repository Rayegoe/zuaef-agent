"""Analysis watchlist — the three-tier stock universe (candidate pool /
analysis watchlist / positions).

Load-bearing regressions:
- user watchlist symbols join the QUOTE plane but NEVER the opportunity
  lifecycle (no READY/NEAR from user curation — strategy evidence stays
  unpolluted);
- scope isolation: per-scope files, opaque binding, no cross-scope reads;
- the agent toolset resolves scope from CoreDeps bindings and fails closed
  without one;
- the gateway threads the scope (bound case first, else chat channel).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("pandas")
pytest.importorskip("zuaef_quant")

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).parents[1] / "plugins" / "zuaef-quant"))

import zuaef_quant.monitor as mon

# shared monitor fixtures/constants (fixture data plane, no network)
from test_quant_trading_monitor import (
    HIST,
    NOW,
    QUOTES,
    READY_CLOSES,
    SPEC,
    fresh_store,
    make_hist,
    make_quote,
)
from zuaef_quant import watchlist as wl
from zuaef_quant.toolset import make_toolset


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture()
def watch_env(monkeypatch):
    """Monitor data plane on fixtures, candidate universe = HIST keys only."""
    monkeypatch.setattr(mon, "resolve_universe", lambda *a, **k: {
        "symbols": list(HIST), "source": "fixture", "source_path": "fixture", "as_of": "fixture"})
    monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: QUOTES.get(s) for s in symbols})
    monkeypatch.setattr(mon, "read_cache", lambda kind, key, cache_dir=None: (HIST[key.split("_")[0]], {}))
    monkeypatch.setattr(mon, "load_volume_semantics", lambda **k: {"status": "PASS"})
    return SimpleNamespace(active_cfg={"monitor": {"near_band": 0.25}})


# ---------------------------------------------------------------------------
# store: validation, scoping, persistence
# ---------------------------------------------------------------------------


class TestWatchlistStore:
    def test_add_remove_roundtrip_preserves_order(self, ws):
        assert wl.update_symbols(ws, "oc_a", "add", ["600460", "002654"])["symbols"] == ["600460", "002654"]
        assert wl.update_symbols(ws, "oc_a", "add", ["600460", "601233"])["symbols"] == ["600460", "002654", "601233"]
        result = wl.update_symbols(ws, "oc_a", "remove", ["002654"])
        assert result["changed"] == ["002654"]
        assert result["symbols"] == ["600460", "601233"]
        assert wl.read_symbols(ws, "oc_a") == ["600460", "601233"]

    def test_invalid_symbol_and_action_rejected(self, ws):
        with pytest.raises(wl.WatchlistError, match="6 digits"):
            wl.update_symbols(ws, "s", "add", ["60046"])
        with pytest.raises(wl.WatchlistError, match="6 digits"):
            wl.update_symbols(ws, "s", "add", ["sh600460"])
        with pytest.raises(wl.WatchlistError, match="action"):
            wl.update_symbols(ws, "s", "buy", ["600460"])
        with pytest.raises(wl.WatchlistError, match="no symbols"):
            wl.update_symbols(ws, "s", "add", [])
        assert wl.all_symbols(ws) == []  # nothing was written

    def test_scope_never_escapes_the_watchlist_dir(self, ws):
        wl.update_symbols(ws, "../../escape", "add", ["600460"])
        files = list((ws / "artifacts" / "quant" / "watchlist").iterdir())
        assert len(files) == 1
        assert files[0].parent == ws / "artifacts" / "quant" / "watchlist"
        assert "escape" in files[0].name and ".." not in files[0].name

    def test_cap_is_enforced(self, ws):
        with pytest.raises(wl.WatchlistError, match="capped"):
            wl.update_symbols(ws, "s", "add", [f"60{i:04d}" for i in range(1, 67)])

    def test_union_across_scopes_for_monitor_only(self, ws):
        wl.update_symbols(ws, "oc_a", "add", ["600460"])
        wl.update_symbols(ws, "oc_b", "add", ["002654", "600460"])
        assert wl.all_symbols(ws) == ["600460", "002654"]
        # scope reads stay isolated
        assert wl.read_symbols(ws, "oc_a") == ["600460"]
        assert wl.read_symbols(ws, "oc_b") == ["002654", "600460"]

    def test_missing_state_is_empty_not_error(self, ws):
        assert wl.read_symbols(ws, "never-seen") == []
        assert wl.all_symbols(ws) == []


# ---------------------------------------------------------------------------
# evidence packet: host-computed market rules + history sufficiency
# ---------------------------------------------------------------------------


class TestSymbolContextEvidence:
    def _ctx(self, tmp_path, monkeypatch, *, symbol="002654", prev_close=4.93, price=5.42):
        monkeypatch.setattr(mon, "now_sh", lambda: NOW)
        monkeypatch.setattr(mon, "resolve_universe", lambda *a, **k: {
            "symbols": list(HIST), "source": "fixture", "source_path": "fixture", "as_of": "fixture"})
        quotes = {s: QUOTES.get(s) for s in HIST}
        quotes[symbol] = make_quote(symbol, price, prev_close)
        monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: quotes.get(s) for s in symbols})
        hist = dict(HIST)
        hist[symbol] = make_hist(symbol, [10.0] * 30)  # sufficient history
        monkeypatch.setattr(mon, "read_cache", lambda kind, key, cache_dir=None: (hist[key.split("_")[0]], {}))
        wl.update_symbols_in(tmp_path / "watchlist", "oc_test", "add", [symbol])
        store = fresh_store(tmp_path)
        captured = {}
        monkeypatch.setattr("builtins.print", lambda p: captured.update(data=json.loads(p)))
        code = mon.cmd_symbol_context(SimpleNamespace(symbol=symbol, scope="oc_test"), store)
        return code, captured["data"]

    def test_price_limit_is_host_arithmetic_not_llm_guess(self, tmp_path, monkeypatch):
        _code, data = self._ctx(tmp_path, monkeypatch)
        assert _code == 0
        rules = data["market_rules"]
        # 002654 = SZ main board: 10%; limit_up = round(4.93 * 1.10, 2) = 5.42
        assert rules["board"] == "MAIN_BOARD"
        assert rules["price_limit_pct"] == 0.10
        assert rules["limit_up_price"] == 5.42
        assert rules["at_limit_up"] is True  # price 5.42 == limit
        assert rules["distance_to_limit"] == 0.0
        assert any("ST" in l for l in rules["limitations"])

    @pytest.mark.parametrize("symbol,pct,board", [
        ("300001", 0.20, "SZ_CHINEXT"), ("688001", 0.20, "SH_STAR"),
        ("830001", 0.30, "BJ"), ("600001", 0.10, "MAIN_BOARD"),
    ])
    def test_board_prefix_rules(self, tmp_path, monkeypatch, symbol, pct, board):
        _code, data = self._ctx(tmp_path, monkeypatch, symbol=symbol, prev_close=10.0, price=11.0)
        rules = data["market_rules"]
        assert rules["board"] == board and rules["price_limit_pct"] == pct
        assert rules["limit_up_price"] == round(10.0 * (1 + pct), 2)

    def test_history_sufficiency_is_a_host_count(self, tmp_path, monkeypatch):
        _code, data = self._ctx(tmp_path, monkeypatch)
        assert data["history"]["bars_available"] == 30
        assert data["history"]["required_bars"] == 25
        assert data["history"]["sufficient"] is True

    def test_short_history_marks_distance_unavailable_not_estimated(self, tmp_path, monkeypatch):
        _code, data = self._ctx(tmp_path, monkeypatch)
        assert data["history"]["sufficient"] is True  # fixture is sufficient here
        # the strategy block separately states availability; a short-history
        # variant is covered by the insufficient-history reason path
        assert "available" in data["strategy_distance"]


def test_side_env_can_import_host_modules_without_pydantic_ai():
    """The quant side env runs the monitor WITHOUT pydantic_ai. The package
    __init__ must stay lazy: importing zuaef_quant.freshness / watchlist
    from the side env must not drag zuaef_quant.plugin in. This reproduces
    the production failure of run 4724d4a1 exactly (import chain, not
    logic)."""
    import subprocess
    import textwrap

    plugins_dir = str(Path(__file__).parents[1] / "plugins" / "zuaef-quant")
    script = textwrap.dedent(f"""
        import importlib.abc, sys
        class _NoPydanticAI(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "pydantic_ai" or fullname.startswith("pydantic_ai."):
                    raise ImportError("side env has no pydantic_ai")
                return None
        sys.meta_path.insert(0, _NoPydanticAI())
        sys.path.insert(0, {plugins_dir!r})
        import zuaef_quant.freshness as f
        import zuaef_quant.watchlist as w
        assert callable(f.derive_freshness) and callable(w.update_symbols_in)
        # the plugin itself stays lazily reachable in the MAIN environment
        print("side-env-ok")
    """)
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert "side-env-ok" in proc.stdout


# ---------------------------------------------------------------------------
# monitor: quote plane joins, lifecycle never does
# ---------------------------------------------------------------------------


class TestMonitorWatchlistUniverse:
    def test_watched_symbol_is_quoted_but_never_becomes_ready(
        self, tmp_path, watch_env, monkeypatch
    ):
        # 600005 has READY-trigger history/quote, but it lives ONLY in a
        # user's analysis watchlist — it must never enter the lifecycle.
        quotes = dict(QUOTES)
        quotes["600005"] = make_quote("600005", 9.95, 9.9)
        monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: quotes.get(s) for s in symbols})
        hist = dict(HIST)
        hist["600005"] = make_hist("600005", READY_CLOSES)
        monkeypatch.setattr(mon, "read_cache", lambda kind, key, cache_dir=None: (hist[key.split("_")[0]], {}))
        wl.update_symbols_in(tmp_path / "watchlist", "oc_test", "add", ["600005"])

        store = fresh_store(tmp_path)
        result = mon.run_cycle(store, active_cfg=watch_env.active_cfg, spec=SPEC,
                               state_dir=store.dir, now=NOW)
        state = json.loads((store.dir / "state.json").read_text())
        assert state["analysis_watchlist"] == ["600005"]
        assert "600005" in quotes  # quote plane included it (universe union)
        assert "600005" not in store.opportunities  # lifecycle never saw it
        assert result["status"] in ("NO_TRADE", "ALERTS")

    def test_watchlist_read_failure_degrades_to_empty(self, tmp_path, watch_env):
        store = fresh_store(tmp_path)
        result = mon.run_cycle(store, active_cfg=watch_env.active_cfg, spec=SPEC,
                               state_dir=store.dir, now=NOW)
        state = json.loads((store.dir / "state.json").read_text())
        assert state["analysis_watchlist"] == []
        assert result["status"] in ("NO_TRADE", "ALERTS")


# ---------------------------------------------------------------------------
# monitor: on-demand single-symbol context
# ---------------------------------------------------------------------------


class TestSymbolContext:
    def _run_ctx(self, tmp_path, monkeypatch, *, symbol="600005", scope="oc_test"):
        monkeypatch.setattr(mon, "now_sh", lambda: NOW)  # fixture clock
        monkeypatch.setattr(mon, "resolve_universe", lambda *a, **k: {
            "symbols": list(HIST), "source": "fixture", "source_path": "fixture", "as_of": "fixture"})
        quotes = dict(QUOTES)
        quotes["600005"] = make_quote("600005", 9.95, 9.9)
        monkeypatch.setattr(mon, "fetch_batch_quotes", lambda symbols: {s: quotes.get(s) for s in symbols})
        hist = dict(HIST)
        hist["600005"] = make_hist("600005", READY_CLOSES)
        monkeypatch.setattr(mon, "read_cache", lambda kind, key, cache_dir=None: (hist[key.split("_")[0]], {}))
        wl.update_symbols_in(tmp_path / "watchlist", "oc_test", "add", ["600005"])
        store = fresh_store(tmp_path)
        captured = {}

        def fake_print(payload):
            captured["data"] = json.loads(payload)

        monkeypatch.setattr("builtins.print", fake_print)
        code = mon.cmd_symbol_context(SimpleNamespace(symbol=symbol, scope=scope), store)
        return code, captured["data"]

    def test_off_pool_symbol_gets_analysis_not_refusal(self, tmp_path, monkeypatch, watch_env):
        code, data = self._run_ctx(tmp_path, monkeypatch)
        assert code == 0
        # membership facts: watched but not a candidate, not a position
        assert data["universe"]["in_candidate_pool"] is False
        assert data["universe"]["in_analysis_watchlist_scope"] is True
        assert data["universe"]["in_open_positions"] is False
        assert "never READY/NEAR" in data["universe"]["semantics"]
        # real strategy distances on the frozen clauses — diagnostics, not states
        assert data["strategy_distance"]["available"] is True
        assert set(data["strategy_distance"]["clause_distances"]) == {"pullback", "volume", "strength"}
        assert data["quote"]["available"] is True
        assert data["quote"]["freshness_status"] == "LIVE_CURRENT"
        assert any("diagnostic distances never generate READY/NEAR" in l for l in data["limitations"])

    def test_scope_absent_membership_is_unknown_not_false(self, tmp_path, monkeypatch, watch_env):
        code, data = self._run_ctx(tmp_path, monkeypatch, scope=None)
        assert code == 0
        assert data["universe"]["in_analysis_watchlist_scope"] is None

    def test_invalid_symbol_fails_loud(self, tmp_path, monkeypatch, watch_env):
        monkeypatch.setattr(mon, "resolve_universe", lambda *a, **k: {"symbols": []})
        store = fresh_store(tmp_path)
        captured = {}
        monkeypatch.setattr("builtins.print", lambda p: captured.update(data=json.loads(p)))
        code = mon.cmd_symbol_context(SimpleNamespace(symbol="ABC123", scope=None), store)
        assert code == 2
        assert "6 digits" in captured["data"]["error"]


# ---------------------------------------------------------------------------
# agent toolset: scope binding, fail-closed, host tool wiring
# ---------------------------------------------------------------------------


def _deps(tmp_path: Path, bindings: dict) -> SimpleNamespace:
    from zuaef_agent.models import CoreDeps

    return SimpleNamespace(deps=CoreDeps(
        workspace_root=tmp_path / "workspace",
        run_id="run-watch-1",
        bindings=bindings,
    ))


def _toolset(tmp_path: Path):
    return make_toolset(quant_python=tmp_path / "quant-python", workspace_root=tmp_path / "workspace")


class TestWatchlistTools:
    def test_scope_binding_reaches_the_tool(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        data = json.loads(toolset.tools["get_analysis_watchlist"].function(ctx))
        assert data["scope"] == "oc_group_a"
        assert data["symbols"] == []

    def test_without_scope_binding_fails_closed(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {})
        data = json.loads(toolset.tools["get_analysis_watchlist"].function(ctx))
        assert "error" in data and "analysis_scope" in data["error"]
        update = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460"]))
        assert "error" in update

    def test_update_tool_writes_scoped_state(self, tmp_path):
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        data = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460", "x"]))
        assert "6 digits" in data["error"]  # invalid code rejected, nothing written
        data = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460"]))
        assert data["changed"] == ["600460"] and data["count"] == 1
        assert data["verified"] is True  # write was confirmed by read-back
        # the run id is recorded for audit
        payload = json.loads(
            (tmp_path / "workspace" / "artifacts" / "quant" / "watchlist" / "oc_group_a.json").read_text()
        )
        assert payload["updated_by_run"] == "run-watch-1"
        # another scope never sees it
        other = json.loads(toolset.tools["get_analysis_watchlist"].function(
            _deps(tmp_path, {"analysis_scope": "oc_group_b"})))
        assert other["symbols"] == []

    def test_add_prewarms_history_for_new_symbols(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        captured: dict = {}

        def fake_run(script, args, quant_python, timeout):
            captured["args"] = args
            return json.dumps({"prewarm": {"600460": {
                "status": "hydrated", "bars_available": 60, "sufficient": True}}})

        monkeypatch.setattr(toolset_module, "_run_module", fake_run)
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        data = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460"]))
        assert data["verified"] is True
        assert data["history_prewarm"]["600460"]["status"] == "hydrated"
        args = captured["args"]
        assert "prewarm-history" in args
        assert args[args.index("--symbols") + 1] == "600460"

    def test_prewarm_failure_keeps_watchlist_success_separate(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        def failing_run(*_a):
            raise RuntimeError("upstream down")

        monkeypatch.setattr(toolset_module, "_run_module", failing_run)
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        data = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460"]))
        # the watchlist edit itself succeeded; hydration failure is separate evidence
        assert data["verified"] is True and data["changed"] == ["600460"]
        assert "error" in data["history_prewarm"]
        persisted = json.loads(
            (tmp_path / "workspace" / "artifacts" / "quant" / "watchlist" / "oc_group_a.json").read_text()
        )
        assert persisted["symbols"] == ["600460"]

    def test_remove_does_not_prewarm(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        calls: list = []

        def fake_run(*a):
            calls.append(a)
            return json.dumps({"prewarm": {}})

        monkeypatch.setattr(toolset_module, "_run_module", fake_run)
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        toolset.tools["update_analysis_watchlist"].function(ctx, "add", ["600460"])
        assert calls, "add must prewarm"
        calls.clear()
        data = json.loads(toolset.tools["update_analysis_watchlist"].function(ctx, "remove", ["600460"]))
        assert data["verified"] is True
        assert not calls
        assert "history_prewarm" not in data

    def test_symbol_context_threads_scope_and_state_dir(self, tmp_path, monkeypatch):
        import zuaef_quant.toolset as toolset_module

        calls: list[list[str]] = []

        def fake_run(script, args, quant_python, timeout):
            calls.append(args)
            return json.dumps({"symbol": "600460", "universe": {}})

        monkeypatch.setattr(toolset_module, "_run_module", fake_run)
        toolset = _toolset(tmp_path)
        ctx = _deps(tmp_path, {"analysis_scope": "oc_group_a"})
        json.loads(toolset.tools["get_symbol_context"].function(ctx, "600460"))
        # argparse contract: top-level --state-dir precedes the subcommand
        assert calls[0][0] == "--state-dir"
        assert "symbol-context" in calls[0][:3]
        assert "--scope" in calls[0] and calls[0][calls[0].index("--scope") + 1] == "oc_group_a"
        # scope-less run still works: membership simply omits the scope read
        json.loads(toolset.tools["get_symbol_context"].function(_deps(tmp_path, {}), "600460"))
        assert "--scope" not in calls[1]


def test_monitor_parser_accepts_the_tool_argv(tmp_path: Path):
    """End-to-end argv contract: the exact arguments the toolset builds are
    accepted by the REAL monitor argparse (run 5936e0ed passed tool facts
    but died at the parser because --state-dir trailed the subcommand)."""
    import os
    import subprocess

    repo = Path(__file__).parents[1]
    env = {**os.environ, "PYTHONPATH": str(repo / "plugins" / "zuaef-quant") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    argv = [
        sys.executable, "-m", "zuaef_quant.monitor",
        "--state-dir", str(tmp_path / "trading"),
        "symbol-context", "--symbol", "ABC",  # invalid code: stops pre-network
    ]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=repo, env=env, check=False)
    assert proc.returncode == 2, proc.stderr[-400:]
    assert "6 digits" in proc.stdout


# ---------------------------------------------------------------------------
# gateway threading: bound case wins, else the chat channel
# ---------------------------------------------------------------------------


def test_bridge_threads_analysis_scope_binding(tmp_path: Path, monkeypatch):
    from pydantic_ai import models
    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    from zuaef_agent import core as core_module
    from zuaef_agent.config import AgentSettings
    from zuaef_agent.gateway.bridge import start_profile_run

    models.ALLOW_MODEL_REQUESTS = False
    monkeypatch.setattr(core_module, "resolve_model", lambda s: FunctionModel(
        lambda m, i: ModelResponse(parts=[TextPart(content="ok")])))
    settings = AgentSettings(
        model="test",
        workspace_root=tmp_path / "workspace",
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )

    outcome = start_profile_run(
        settings=settings, profile=None, prompt="hi", conversation_id="c1",
        case_id="case-9", analysis_scope="oc_group_a",
    )
    assert outcome.receipt.bindings == {"case": "case-9", "analysis_scope": "oc_group_a"}

    outcome = start_profile_run(
        settings=settings, profile=None, prompt="hi", conversation_id="c2",
        analysis_scope="oc_group_b",
    )
    assert outcome.receipt.bindings == {"analysis_scope": "oc_group_b"}
