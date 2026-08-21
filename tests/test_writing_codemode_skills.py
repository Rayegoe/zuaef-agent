"""Legacy CodeMode selection and deferred skill-library tests.

Zero model calls. These tests belong with the CodeMode experiment and the
writing skills (not with the production driver contract), so they can be
reverted independently of the agent-owned production path (SPEC §30 / v0.2
commit discipline).

  - the benchmark-only CodeMode profile wraps pull_context; save_article stays native
  - the ace-writing plugin returns CodeMode only when configured
  - the ace-writing-codemode profile composes with CodeMode present
  - the four writing skills exist as deferred capabilities (catalog = id +
    description only; SKILL.md body loads on demand)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.tools import ToolDefinition, matches_tool_selector
from pydantic_ai_harness.skills import Skills

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import (
    WritingEnvironmentToolset,
    build_writing_toolset,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps

PLUGIN_INSTALLED = "ace-writing" in {
    ep.name
    for ep in __import__(
        "importlib.metadata", fromlist=["entry_points"]
    ).entry_points(group="zuaef.plugins")
}
PROFILE_EXISTS = (REPO / "profiles" / "ace-writing.toml").is_file()
NEEDS_PLUGIN = pytest.mark.skipif(
    not (PLUGIN_INSTALLED and PROFILE_EXISTS),
    reason="ace-writing plugin entry point and/or profiles/ace-writing.toml missing",
)


def _settings(tmp_path: Path) -> AgentSettings:
    return AgentSettings(
        model="test",
        workspace_root=tmp_path / "ws",
        runtime_state_root=tmp_path / "state",
        request_limit=8,
    )


def _tool_def(name: str, *, code_mode: bool) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        parameters_json_schema={"type": "object", "properties": {}},
        metadata={"code_mode": True} if code_mode else None,
    )


async def _selected(selector, defs, deps: CoreDeps) -> set[str]:
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    selected: set[str] = set()
    for td in defs:
        if await matches_tool_selector(selector, ctx, td):
            selected.add(td.name)
    return selected


def test_codemode_selector_wraps_context_and_excludes_save():
    deps = CoreDeps(workspace_root=Path("."), run_id="cm")
    definitions = [
        _tool_def("pull_context", code_mode=True),
        _tool_def("save_article", code_mode=False),
    ]
    selected = asyncio.run(_selected({"code_mode": True}, definitions, deps))
    assert selected == {"pull_context"}
    assert "save_article" not in selected


def test_environment_toolset_tags_only_context_for_legacy_codemode():
    toolset = build_writing_toolset(ace_root=REPO / "missing-ace")
    assert isinstance(toolset, WritingEnvironmentToolset)
    assert toolset.tools["pull_context"].metadata.get("code_mode") is True
    assert toolset.tools["save_article"].metadata is None or (
        toolset.tools["save_article"].metadata.get("code_mode") is not True
    )


@NEEDS_PLUGIN
def test_plugin_returns_codemode_capability_when_configured(tmp_path):
    """code_mode=true adds the Harness CodeMode capability to the bundle;
    off by default (SPEC Phase 5: initially disabled)."""
    from pydantic_ai_harness.code_mode import CodeMode
    from zuaef_ace_writing import create_plugin

    from zuaef_agent.plugin_api import PluginEnv

    env = PluginEnv(
        plugin_id="ace-writing",
        plugin_version="0.2.0",
        workspace_root=tmp_path,
        state_root=tmp_path / "state",
    )
    bundle_off = create_plugin(env, {"code_mode": False})
    assert not any(isinstance(c, CodeMode) for c in bundle_off.capabilities)
    bundle_on = create_plugin(env, {"code_mode": True})
    assert any(isinstance(c, CodeMode) for c in bundle_on.capabilities)


@NEEDS_PLUGIN
def test_codemode_profile_composes(tmp_path):
    """The experimental ace-writing-codemode profile composes with CodeMode in
    the capability list and the writing toolset intact (WRITE-1 for the A/B
    side)."""
    from pydantic_ai_harness.code_mode import CodeMode

    from zuaef_agent.composition import build_profile_agent

    settings = _settings(tmp_path)
    agent, snapshot = build_profile_agent(
        settings,
        run_id="wc-cm",
        profile="ace-writing-codemode",
        config_root=REPO,
    )
    assert snapshot.profile == "ace-writing-codemode"
    caps = agent.root_capability.capabilities
    assert any(isinstance(c, CodeMode) for c in caps)
    assert any(isinstance(t, WritingEnvironmentToolset) for t in agent.toolsets)


def test_writing_skills_exist_as_deferred_capabilities():
    """The four writing skills are present in the skill library as deferred
    capabilities: catalog carries id + description only; the SKILL.md body is
    NOT part of the catalog entry (SPEC §8, Phase 4 gate)."""
    caps = Skills[object]([REPO / ".agents" / "skills"])
    deferred = getattr(caps, "_deferred_capabilities", ())
    ids = {getattr(c, "id", None) for c in deferred}
    writing = {
        "longform-feature-writing",
        "scene-preserving-writing",
        "editorial-revision",
        "beauty-wechat-writing",
    }
    assert writing <= ids
    for c in deferred:
        if getattr(c, "id", None) in writing:
            desc = getattr(c, "description", "") or ""
            assert len(desc) > 50  # catalog description present
            assert "Detect the flattening" not in desc  # body deferred
            assert "summary trap" not in desc
