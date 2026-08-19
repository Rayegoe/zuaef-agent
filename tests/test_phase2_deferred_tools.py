"""Business progressive disclosure — SPEC v1.0 §4 (P2-2).

The composition layer mechanically wraps an existing plugin Toolset in the
released ``DeferredLoadingToolset`` (``ProfilePluginConfig.defer_tools``),
so the model cannot see the domain's tool schemas until tool search
discovers them. Proof inspects the model-visible tool surface at each step
(deterministic FunctionModel, no model call, no network).

   STEP 1 (initial): eager Case tools + core surface only;
                     writing/budget/wordpress full schemas absent.
   STEP 2 (after search_tools): the writing domain's tools are revealed.
"""

from __future__ import annotations

import asyncio
import json
from importlib.metadata import EntryPoint
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.composition import build_agent_from_snapshot, resolve_profile
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps

WRITING_DEFERRED = """\
schema = 1
name = "deferred"

[generalist]
tool_search = true

[[plugins]]
id = "case-probe"

[[plugins]]
id = "fixture-ace-writing"
defer_tools = true
"""

WRITING_EAGER = WRITING_DEFERRED.replace("defer_tools = true", "defer_tools = false")


def _ep(module: str, name: str) -> EntryPoint:
    return EntryPoint(
        name=name,
        value=f"fixture_plugins.{module}:create_plugin",
        group="zuaef.plugins",
    )


DISCOVER = {
    "case-probe": _ep("case_probe", "case-probe"),
    "fixture-ace-writing": _ep("writing", "fixture-ace-writing"),
}
VERSIONS = {
    "case-probe": "0.1.0",
    "fixture-ace-writing": "0.2.1",
}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_skills=False,
        enable_tool_search=True,
    )


def _write_profile(tmp_path: Path, text: str, name: str = "deferred") -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


def _surface_steps(agent: Agent, sequence: list[tuple[str, dict]], settings: AgentSettings) -> list[list[str]]:
    """Run with a scripted model; return the model-visible tool names per step."""
    steps: list[list[str]] = []
    seq = list(sequence)

    async def handler(messages, info):
        names = sorted(
            getattr(t, "name", "") for t in (info.function_tools or [])
        )
        steps.append(names)
        if seq:
            name, args = seq.pop(0)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(
            parts=[
                TextPart(content="done")
            ]
        )

    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id="r-deferred",
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("write an article demo", deps=deps))
    return steps


def test_initial_surface_excludes_deferred_domains(tmp_path: Path):
    config_root = _write_profile(tmp_path, WRITING_DEFERRED)
    snapshot = resolve_profile(
        "deferred",
        _settings(tmp_path),
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert snapshot.plugins[1].id == "fixture-ace-writing"
    assert snapshot.plugins[1].defer_tools is True
    agent = build_agent_from_snapshot(
        _settings(tmp_path),
        run_id="r1",
        snapshot=snapshot,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    # Step 1: model never sees the deferred writing schemas — search_tools
    # (the framework's compact discovery surface) is what it sees instead.
    steps = _surface_steps(
        agent,
        [("search_tools", {"queries": ["material", "save article"]})],
        _settings(tmp_path),
    )
    first = steps[0]
    assert "load_case_context" in first  # eager Case orientation is visible
    assert not any(
        name in first for name in ("list_materials", "read_material", "save_artifact")
    )
    assert not any(
        name in first
        for name in (
            "parse_budget_csv",
            "budget_summary",
            "wordpress_publish_post",
        )
    )


def test_search_reveals_deferred_writing_tools(tmp_path: Path):
    config_root = _write_profile(tmp_path, WRITING_DEFERRED)
    snapshot = resolve_profile(
        "deferred",
        _settings(tmp_path),
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    agent = build_agent_from_snapshot(
        _settings(tmp_path),
        run_id="r2",
        snapshot=snapshot,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    steps = _surface_steps(
        agent,
        [("search_tools", {"queries": ["materials save artifact"]})],
        _settings(tmp_path),
    )
    assert len(steps) >= 2
    second = steps[1]
    assert "list_materials" in second
    assert "save_artifact" in second


def test_eager_marker_keeps_all_tools_visible(tmp_path: Path):
    """Without defer_tools the writing schemas are present from the start
    (backward-compatible behavior; the marker is an opt-in)."""
    config_root = _write_profile(tmp_path, WRITING_EAGER, name="deferred")
    snapshot = resolve_profile(
        "deferred",
        _settings(tmp_path),
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert snapshot.plugins[1].defer_tools is False
    agent = build_agent_from_snapshot(
        _settings(tmp_path),
        run_id="r3",
        snapshot=snapshot,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    steps = _surface_steps(agent, [], _settings(tmp_path))
    assert "list_materials" in steps[0]
    assert "save_artifact" in steps[0]


def test_defer_tools_frozen_in_identity_and_resume(tmp_path: Path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, WRITING_DEFERRED)
    snapshot1 = resolve_profile(
        "deferred",
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    # Flipping the marker changes the identity — it is an identity fact.
    config_root2 = _write_profile(tmp_path, WRITING_EAGER, name="deferred")
    snapshot2 = resolve_profile(
        "deferred",
        settings,
        config_root=config_root2,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert snapshot1.composition_id != snapshot2.composition_id
    # Resume from the frozen deferred snapshot hides the domain even though
    # the current profile now composes it eagerly.
    agent = build_agent_from_snapshot(
        settings,
        run_id="r4",
        snapshot=snapshot1,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    steps = _surface_steps(agent, [], _settings(tmp_path))
    assert "list_materials" not in steps[0]
    assert "load_case_context" in steps[0]


def test_deferred_snapshot_roundtrip_json(tmp_path: Path):
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, WRITING_DEFERRED)
    snapshot = resolve_profile(
        "deferred",
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    payload = json.loads(snapshot.model_dump_json())
    assert payload["plugins"][1]["defer_tools"] is True
    assert payload["generalist"]["enable_tool_search"] is True