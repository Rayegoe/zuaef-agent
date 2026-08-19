"""Deployment-level generalist authorization — SPEC v1.0 §3 (P2-1).

Proves the two-layer model with a hermetic FunctionModel, never a model call:

    effective = host ceiling ∩ profile request

- the profile's ``[generalist]`` section is the deployment request;
- ``AgentSettings`` flags are the host ceiling;
- the composition layer freezes the intersection into the snapshot identity;
- resume rebuilds from the frozen snapshot, so a profile change after a pause
  cannot alter the resumed capabilities.

Backward compatibility: a profile without ``[generalist]`` keeps the current
narrow behavior (``snapshot.generalist is None``).
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

from zuaef_agent.composition import (
    build_agent_from_snapshot,
    build_profile_agent,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError

GENERALIST_PROFILE = """\
schema = 1
name = "policy"

[generalist]
web_search = true
web_fetch = true
tool_search = true
memory = true
shell = false

[[plugins]]
id = "deps-probe"
"""


def _ep() -> EntryPoint:
    return EntryPoint(
        name="deps-probe",
        value="fixture_plugins.deps_probe:create_plugin",
        group="zuaef.plugins",
    )


DISCOVER = {"deps-probe": _ep()}
VERSIONS = {"deps-probe": "0.1.0"}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


def _settings(tmp_path: Path, **flags) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_skills=False,
        **flags,
    )


def _write_profile(tmp_path: Path, *sections: str) -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    body = "schema = 1\nname = \"policy\"\n" + "\n".join(sections) + "\n"
    (config_root / "profiles" / "policy.toml").write_text(body, encoding="utf-8")
    return config_root


def test_profile_without_generalist_keeps_narrow_defaults(tmp_path: Path):
    config_root = _write_profile(tmp_path, '[[plugins]]\nid = "deps-probe"')
    snapshot = resolve_profile(
        "policy",
        _settings(tmp_path),
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert snapshot.generalist is None
    assert not snapshot.plugins[0].defer_tools


def test_effective_is_host_ceiling_intersection(tmp_path: Path):
    settings = _settings(
        tmp_path,
        enable_web_search=True,   # host allows
        enable_tool_search=True,  # host allows
        enable_shell=True,        # host allows
        enable_memory=False,      # host DENIES
    )
    config_root = _write_profile(
        tmp_path,
        "[generalist]",
        "web_search = true",
        "tool_search = true",
        "memory = true",
        "shell = false",
        '[[plugins]]\nid = "deps-probe"',
    )
    snapshot = resolve_profile(
        "policy",
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    eff = snapshot.generalist
    assert eff["enable_web_search"] is True   # host ∩ request = on
    assert eff["enable_tool_search"] is True   # host ∩ request = on
    assert eff["enable_shell"] is False        # profile does not request Shell
    assert eff["enable_memory"] is False       # host ceiling denies Memory
    assert eff["enable_repo_context"] is False
    assert eff["enable_subagents"] is False


def test_profile_requests_web_but_host_denies_web_is_absent(tmp_path: Path):
    settings = _settings(tmp_path)  # host web_search=False (default)
    config_root = _write_profile(
        tmp_path,
        "[generalist]",
        "web_search = true",
        "web_fetch = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    snapshot = resolve_profile(
        "policy",
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    # Host ceiling wins: Web is NOT exposed even though the profile requests it.
    assert snapshot.generalist["enable_web_search"] is False
    assert snapshot.generalist["enable_web_fetch"] is False


def test_policy_changes_the_composition_identity(tmp_path: Path):
    settings = _settings(tmp_path, enable_tool_search=True, enable_memory=True)
    base_cfg = _write_profile(
        tmp_path,
        "[generalist]",
        "tool_search = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    baseline = resolve_profile(
        "policy",
        settings,
        config_root=base_cfg,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    changed_cfg = _write_profile(
        tmp_path,
        "[generalist]",
        "tool_search = true",
        "memory = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    changed = resolve_profile(
        "policy",
        settings,
        config_root=changed_cfg,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert changed.composition_id != baseline.composition_id
    assert changed.generalist["enable_memory"] is True


def _capture_tools(agent, settings: AgentSettings) -> list[str]:
    """Visible tool names on the first model step (deterministic)."""
    import asyncio

    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    captured: dict[str, list[str]] = {"tools": []}

    async def handler(messages, info):
        if not captured["tools"]:
            captured["tools"] = sorted(
                t.name for t in (info.function_tools or [])
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": "done"},
                )
            ]
        )

    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id="r-policy",
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("go", deps=deps))
    return captured["tools"]


def test_frozen_snapshot_reproduces_old_policy_after_profile_change(
    tmp_path: Path,
):
    """Resume authority: the snapshot's effective policy is the only source;
    a mutated current profile must not alter the rebuilt agent's authority."""
    settings = _settings(tmp_path, enable_tool_search=True, enable_memory=True)
    config_root = _write_profile(
        tmp_path,
        "[generalist]",
        "tool_search = true",
        "memory = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    agent, snapshot = build_profile_agent(
        settings,
        run_id="r1",
        profile="policy",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert snapshot.generalist["enable_memory"] is True
    assert "write_memory" in _capture_tools(agent, settings)

    # After the pause the current profile drops memory — but the frozen
    # snapshot must still rebuild the agent WITH memory (same deployment
    # authority), while a fresh resolve of the mutated profile no longer
    # matches the frozen identity.
    _write_profile(
        tmp_path,
        "[generalist]",
        "tool_search = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    rebuilt = build_agent_from_snapshot(
        settings,
        run_id="r2",
        snapshot=snapshot,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert "write_memory" in _capture_tools(rebuilt, settings)
    restored = resolve_profile(
        "policy",
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    assert restored.composition_id != snapshot.composition_id


def test_defer_tools_requires_tool_search_authorization(tmp_path: Path):
    settings = _settings(tmp_path)  # host tool_search=False
    config_root = _write_profile(
        tmp_path,
        "[generalist]",
        "tool_search = true",  # profile requests it...
        '[[plugins]]\nid = "deps-probe"\ndefer_tools = true',
    )
    with pytest.raises(CompositionError, match="defer_tools requires tool_search"):
        resolve_profile(
            "policy",
            settings,
            config_root=config_root,
            discover=lambda: DISCOVER,
            version_for=_vf,
        )


def test_invalid_generalist_key_rejected(tmp_path: Path):
    config_root = _write_profile(
        tmp_path,
        "[generalist]",
        "web_surfing = true",
        '[[plugins]]\nid = "deps-probe"',
    )
    with pytest.raises(CompositionError, match="failed schema validation"):
        resolve_profile(
            "policy",
            _settings(tmp_path),
            config_root=config_root,
            discover=lambda: DISCOVER,
            version_for=_vf,
        )