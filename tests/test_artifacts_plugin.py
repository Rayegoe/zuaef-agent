"""Composition and capability-truth acceptance for the zuaef-artifacts plugin
(spec pack 10 section A — composition gates; P1 pass criteria).

The plugin under test is the real installed ``zuaef-artifacts`` distribution;
profiles resolve from the repository ``profiles/`` directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zuaef_agent.composition import (
    build_agent_from_snapshot,
    installed_plugins,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.plugin_api import CompositionError, PluginEnv

REPO_ROOT = Path(__file__).parents[1]
PROFILE = "general-knowledge-worker-artifacts"

ARTIFACT_CAPABILITY_IDS = {
    "docx-artifacts",
    "pdf-artifacts",
    "slides-artifacts",
    "spreadsheet-artifacts",
}


def _settings(tmp_path: Path) -> AgentSettings:
    """Production-shaped host ceiling (what .env authorizes on the pilot
    deployment); the profile's [generalist] section intersects with it."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
        enable_tool_search=True,
        enable_memory=True,
        enable_conversation_search=True,
        enable_context_controls=True,
        enable_subagents=True,
    )


def test_artifacts_plugin_is_discoverable_after_install():
    """A1/A2: clean install exposes the entry point (uv sync installed it)."""
    assert ("artifacts", "0.1.0") in installed_plugins()


def test_pilot_profile_resolves_without_model_call(tmp_path):
    """A3/A4: profile check passes pre-run; the plugin is enabled with
    explicit capability permission."""
    snapshot = resolve_profile(PROFILE, _settings(tmp_path), config_root=REPO_ROOT)
    ids = [ref.id for ref in snapshot.plugins]
    assert ids == ["knowledge-worker", "artifacts"]
    artifacts_ref = snapshot.plugins[1]
    assert artifacts_ref.capabilities_allowed is True


def test_pilot_profile_composes_four_deferred_capabilities(tmp_path, monkeypatch):
    """A4: the four artifact capabilities compose through the existing seam
    and are marked for capability-level deferred loading."""
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    snapshot = resolve_profile(PROFILE, settings, config_root=REPO_ROOT)
    agent = build_agent_from_snapshot(settings, run_id="p1-compose", snapshot=snapshot)
    deferred = {
        cap.id
        for cap in agent.root_capability.capabilities
        if getattr(cap, "defer_loading", False) is True
    }
    assert ARTIFACT_CAPABILITY_IDS <= deferred


def test_pilot_profile_shell_stays_disabled(tmp_path):
    """A6: the pilot profile keeps shell disabled and tool search enabled
    under the production-shaped host ceiling."""
    snapshot = resolve_profile(PROFILE, _settings(tmp_path), config_root=REPO_ROOT)
    assert snapshot.generalist is not None
    assert snapshot.generalist["enable_shell"] is False
    assert snapshot.generalist["enable_tool_search"] is True


def test_base_knowledge_worker_profile_is_unchanged(tmp_path):
    """Installing the plugin never changes existing profile composition."""
    snapshot = resolve_profile(
        "general-knowledge-worker", _settings(tmp_path), config_root=REPO_ROOT
    )
    assert [ref.id for ref in snapshot.plugins] == ["knowledge-worker"]


def _plugin_env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="artifacts",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / ".zuaef-state",
    )


def test_unknown_config_key_fails_composition(tmp_path):
    """Misconfiguration is a pre-run process error, never silent behavior."""
    from zuaef_artifacts.plugin import build_plugin

    with pytest.raises(CompositionError, match="unknown key"):
        build_plugin(_plugin_env(tmp_path), {"no_such_key": 1})


def test_out_of_range_config_fails_composition(tmp_path):
    from zuaef_artifacts.plugin import build_plugin

    with pytest.raises(CompositionError, match="process_timeout_seconds"):
        build_plugin(_plugin_env(tmp_path), {"process_timeout_seconds": 1})


def test_bundle_returns_exactly_four_capabilities(tmp_path):
    from zuaef_artifacts.plugin import build_plugin

    bundle = build_plugin(_plugin_env(tmp_path), {})
    assert {cap.id for cap in bundle.capabilities} == ARTIFACT_CAPABILITY_IDS
    assert bundle.toolsets == ()
    assert bundle.skill_dirs == ()
