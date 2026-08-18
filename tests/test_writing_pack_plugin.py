"""Contract tests for the thin external writing-pack adapter."""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import RunContext, RunUsage
from zuaef_writing_pack import build_plugin

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

EXPECTED_TOOLS = {"sanlian_catalog", "sanlian_search", "sanlian_read"}


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="zuaef-writing-pack",
        plugin_version="0.1.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _pack(tmp_path: Path) -> Path:
    root = tmp_path / "zuaef_writing"
    skill = root / "skills" / "sanlian-editorial-reading"
    commands = skill / "commands"
    commands.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: sanlian-editorial-reading\ndescription: test\n---\n\nread\n",
        encoding="utf-8",
    )
    for name in ("sanlian_catalog.py", "sanlian_search.py", "sanlian_read.py"):
        (commands / name).write_text("print('{}')\n", encoding="utf-8")
    (root / "corpus").mkdir()
    (root / "corpus" / "collections.toml").write_text(
        "[collections.test]\nroot = '.'\n",
        encoding="utf-8",
    )
    return root


def _tool_names(bundle: PluginBundle, tmp_path: Path) -> set[str]:
    ctx = RunContext(
        deps=CoreDeps(workspace_root=tmp_path, run_id="r1"),
        usage=RunUsage(),
        prompt="",
        model=None,
    )
    return set(asyncio.run(bundle.toolsets[0].get_tools(ctx)))


def test_bundle_exposes_only_external_skill_dir_and_three_tools(tmp_path: Path) -> None:
    bundle = build_plugin(_env(tmp_path), {"pack_root": str(_pack(tmp_path))})

    assert isinstance(bundle, PluginBundle)
    assert len(bundle.toolsets) == 1
    assert len(bundle.skill_dirs) == 1
    assert bundle.capabilities == ()
    assert _tool_names(bundle, tmp_path) == EXPECTED_TOOLS


def test_missing_pack_fails_before_run(tmp_path: Path) -> None:
    try:
        build_plugin(_env(tmp_path), {"pack_root": str(tmp_path / "missing")})
    except CompositionError as exc:
        assert "writing pack missing" in str(exc)
    else:
        raise AssertionError("missing writing pack should fail composition")
