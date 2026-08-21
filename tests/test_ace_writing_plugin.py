"""Production contract tests for the small ``ace-writing`` environment."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic_ai import RunContext, RunUsage
from zuaef_ace_writing import create_plugin
from zuaef_ace_writing.plugin import _resolve_ace_root
from zuaef_ace_writing.writing_toolset import build_writing_toolset as plugin_toolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

EXPECTED_TOOLS = {
    "pull_context",
    "save_article",
}


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="ace-writing",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _fake_ace_root(tmp_path: Path) -> Path:
    ace = tmp_path / "ace"
    (ace / "tools").mkdir(parents=True, exist_ok=True)
    (ace / "tools" / "ctx.py").write_text("", encoding="utf-8")
    return ace


def _tool_names(bundle: PluginBundle, tmp_path: Path) -> set[str]:
    deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    return set(asyncio.run(bundle.toolsets[0].get_tools(ctx)))


class TestPluginContract:
    def test_bundle_is_one_toolset_only(self, tmp_path: Path) -> None:
        bundle = create_plugin(_env(tmp_path), {"ace_root": str(_fake_ace_root(tmp_path))})
        assert isinstance(bundle, PluginBundle)
        assert len(bundle.toolsets) == 1
        assert bundle.skill_dirs == ()
        assert bundle.capabilities == ()

    def test_expected_tool_names(self, tmp_path: Path) -> None:
        bundle = create_plugin(_env(tmp_path), {"ace_root": str(_fake_ace_root(tmp_path))})
        assert _tool_names(bundle, tmp_path) == EXPECTED_TOOLS

    def test_ace_root_from_config_wins_over_env(self, tmp_path: Path, monkeypatch) -> None:
        fake = _fake_ace_root(tmp_path)
        monkeypatch.setenv("ACE_ROOT", "/nonexistent/env/ace")
        assert _resolve_ace_root({"ace_root": str(fake)}) == fake.resolve()

    def test_ace_root_from_env_when_config_absent(self, tmp_path: Path, monkeypatch) -> None:
        fake = _fake_ace_root(tmp_path)
        monkeypatch.setenv("ACE_ROOT", str(fake))
        assert _resolve_ace_root({}) == fake.resolve()

    def test_missing_ctx_py_fails_loud(self, tmp_path: Path) -> None:
        bad = tmp_path / "not-ace"
        bad.mkdir()
        with pytest.raises(CompositionError, match="tools/ctx.py"):
            create_plugin(_env(tmp_path), {"ace_root": str(bad)})

    def test_plugin_surface_is_not_the_legacy_proof_surface(self, tmp_path: Path) -> None:
        plugin = plugin_toolset(_fake_ace_root(tmp_path))
        deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
        ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
        names = set(asyncio.run(plugin.get_tools(ctx)))
        assert names == EXPECTED_TOOLS
        assert names.isdisjoint({"list_materials", "check_claim", "save_artifact"})
