"""P6 shadow-layer retirement guards (static, no model, no network).

P5.9 moved production authority into ``zuaef_quant``.  P6 deletes every root
compatibility wrapper with zero remaining production/deployment caller and
keeps only genuine developer/audit/benchmark tools under ``tools/``.

The P6 closure (pre-P7 boundary cleanup) extends the guards to every root
``tools/quant_*`` file type, deletes the one-key daily workflow, and pins
operator-layer neutrality: ``ops`` consumes only neutral domain modules.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).parents[1]
PLUGIN = REPO / "plugins" / "zuaef-quant" / "zuaef_quant"

#: Wrappers retired in P6: production callers were migrated to the plugin
#: modules, tests/docs were migrated, and no deployment/external caller remains.
DELETED_WRAPPERS = {
    "quant_core.py",
    "quant_live_scan.py",
    "quant_trading_monitor.py",
    "quant_telegram_bridge.py",
    "quant_market_context.py",
    "quant_market_intel.py",
    "quant_build_candidates.py",
    "quant_eval_qlib.py",
    "quant_render_business_dashboard.py",
    "quant_serve.py",
}

PLUGIN_OWNERS = {
    "quant_core.py": None,
    "market_context.py": "zuaef_quant.market_context",
    "market_intel.py": "zuaef_quant.market_intel",
    "candidates_sidecar.py": "zuaef_quant.candidates_sidecar",
    "eval_sidecar.py": "zuaef_quant.eval_sidecar",
    "monitor.py": "zuaef_quant.monitor",
    "scan_sidecar.py": "zuaef_quant.scan_sidecar",
    "bridge.py": "zuaef_quant.bridge",
    "dashboard/render.py": "zuaef_quant.dashboard.render",
    "dashboard/serve.py": "zuaef_quant.dashboard.serve",
}

#: Retained root Quant files (every file type, not only ``*.py`` — the P6
#: closure closes the gap that let ``quant_daily.sh`` escape classification).
#: Every one must be useful engineering tooling (audit/benchmark/developer/
#: diagnostic) and must have no production runtime dependency.
RETAINED_TOOLS = {
    "quant_anti_leakage_check.py",
    "quant_fetch_universe.py",
    "quant_p05_reconcile.py",
    "quant_p0_data_proof.py",
    "quant_pit_audit.py",
    "quant_render_dashboard.py",
    "quant_v31.py",
    "quant_validate_semantics.py",
}


def test_all_zero_caller_wrappers_are_deleted():
    for name in DELETED_WRAPPERS:
        assert not (REPO / "tools" / name).exists(), f"obsolete wrapper still present: {name}"


def test_plugin_owned_production_authorities_exist():
    for name in PLUGIN_OWNERS:
        assert (PLUGIN / name).is_file(), name
    for module in (
        "zuaef_quant.market_context",
        "zuaef_quant.market_intel",
        "zuaef_quant.candidates_sidecar",
        "zuaef_quant.eval_sidecar",
        "zuaef_quant.dashboard.render",
        "zuaef_quant.dashboard.serve",
    ):
        assert module  # module map documented above; import guards below use files


def test_toolset_routes_model_visible_semantic_paths_to_plugin_modules():
    source = (PLUGIN / "toolset.py").read_text(encoding="utf-8")
    for module in (
        "zuaef_quant.market_context",
        "zuaef_quant.market_intel",
        "zuaef_quant.eval_sidecar",
        "zuaef_quant.dashboard.render",
    ):
        assert f'"{module}"' in source, module
    for root_name in DELETED_WRAPPERS:
        assert root_name not in source, root_name
    assert "QUANT_EVAL_SCRIPT" not in source
    assert "TOOLS_DIR" not in source


def test_operator_cli_routes_production_commands_to_plugin_modules():
    source = (PLUGIN / "ops.py").read_text(encoding="utf-8")
    for module in (
        "zuaef_quant.dashboard.render",
        "zuaef_quant.dashboard.serve",
        "zuaef_quant.scan_sidecar",
        "zuaef_quant.monitor",
        "zuaef_quant.bridge",
    ):
        assert f'"{module}"' in source, module
    assert "tools/quant_" not in source


def test_serve_uses_side_environment_module_commands():
    source = (PLUGIN / "dashboard" / "serve.py").read_text(encoding="utf-8")
    assert '"zuaef_quant.scan_sidecar"' in source
    assert '"zuaef_quant.monitor"' in source
    for root_name in DELETED_WRAPPERS:
        assert root_name not in source, root_name
    assert "tools/quant_" not in source


def test_retained_root_tools_are_developer_only():
    actual = {path.name for path in (REPO / "tools").glob("quant_*")}
    assert actual == RETAINED_TOOLS, actual ^ RETAINED_TOOLS

    for name in actual:
        source = (REPO / "tools" / name).read_text(encoding="utf-8")
        for module in (
            "quant_core",
            "quant_live_scan",
            "quant_trading_monitor",
            "quant_telegram_bridge",
            "quant_market_context",
            "quant_market_intel",
            "quant_build_candidates",
            "quant_eval_qlib",
            "quant_render_business_dashboard",
            "quant_serve",
        ):
            assert not re.search(
                rf"^\s*from\s+{re.escape(module)}\b", source, re.MULTILINE
            ), (name, module)
            assert not re.search(
                rf"^\s*import\s+{re.escape(module)}\b", source, re.MULTILINE
            ), (name, module)


def test_systemd_units_do_not_reference_retired_root_wrappers():
    for unit in sorted((REPO / "ops" / "systemd").glob("*")):
        if not unit.is_file():
            continue
        source = unit.read_text(encoding="utf-8")
        for name in DELETED_WRAPPERS:
            assert f"tools/{name}" not in source, (unit.name, name)


def test_systemd_monitor_uses_plugin_module_in_side_environment():
    unit = (REPO / "ops" / "systemd" / "zuaef-quant-monitor.service").read_text(
        encoding="utf-8"
    )
    assert ".venv-quant/bin/python -m zuaef_quant.monitor session" in unit
    assert "tools/quant_" not in unit


def test_daily_product_workflow_absent_from_root_tools():
    """P6 closure: the one-key daily workflow was deleted — a root product
    workflow (any file type) must not come back under tools/."""
    assert not (REPO / "tools" / "quant_daily.sh").exists()


def test_operator_layer_has_no_model_layer_reverse_dependency():
    """P6 closure: ``ops`` consumes neutral domain modules (runtime, trading,
    watchlist, sidecar modules), never the model-facing toolset/plugin
    layers, for runtime resolution or state projection."""
    source = (PLUGIN / "ops.py").read_text(encoding="utf-8")
    banned_patterns = (
        r"^\s*from\s+\.toolset\b",
        r"^\s*from\s+\.plugin\b",
        r"^\s*import\s+\.toolset\b",
        r"^\s*import\s+\.plugin\b",
        r"^\s*from\s+\.+\s+import\s+[^\n]*\b(toolset|plugin)\b",
    )
    for pattern in banned_patterns:
        assert not re.search(pattern, source, re.MULTILINE), pattern
    # ...and it routes through the neutral authorities positively.
    assert "from .trading import read_trading_snapshot" in source
    assert "from .runtime import resolve_quant_python" in source


def test_trading_snapshot_and_path_rules_have_one_authority():
    """P6 closure: one deterministic snapshot projection authority shared by
    toolset and ops, and one quant-python path-rule authority in runtime."""
    trading_source = (PLUGIN / "trading.py").read_text(encoding="utf-8")
    toolset_source = (PLUGIN / "toolset.py").read_text(encoding="utf-8")
    plugin_source = (PLUGIN / "plugin.py").read_text(encoding="utf-8")
    runtime_source = (PLUGIN / "runtime.py").read_text(encoding="utf-8")
    assert "def read_trading_snapshot" in trading_source
    assert "def _read_trading_snapshot" not in toolset_source
    # Path rules (env name + default interpreter) are defined only in runtime.
    assert "QUANT_PYTHON_DEFAULT = " in runtime_source
    assert "QUANT_PYTHON_DEFAULT = " not in plugin_source
    # plugin's resolver must not reach back into the toolset for repo state.
    assert "from .toolset import REPO_ROOT" not in plugin_source
