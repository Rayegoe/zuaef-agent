"""Context-management baseline — TASKS T008.

Proves (with deterministic FunctionModel scripts, no model/network) that the
released upstream context controls are READY on the platform surface and that
their activation is threshold/task driven:

- ToolOutputLimits: an oversized tool return is reduced once (spilled to the
  result store, model keeps a handle + preview) — host-side, always active.
- ClearToolResults: stale tool returns are cleared once the history exceeds
  the configured bound (threshold-driven).
- Context-control strategy set (ClearToolResults / ClampOversizedMessages /
  WarnNearLimits) and the compaction strategy classes are composed and ready.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import Agent, FunctionToolset
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.tools import Tool
from pydantic_ai_harness.compaction import (
    ClearToolResults,
    SlidingWindowCompaction,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent


def _settings(tmp_path: Path, **cap_flags) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_knowledge=False,
        enable_skills=False,
        **cap_flags,
    )


def _grounded(agent: Agent, *, script) -> None:
    """Run ``agent`` with a scripted FunctionModel that drives ``script``."""

    async def run():
        with agent.override(model=FunctionModel(script)):
            await agent.run("proceed")

    asyncio.run(run())


def _last_tool_return_len(agent: Agent, script) -> int | None:
    captured: dict = {}

    async def handler(messages, info):
        returns = [
            p
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "tool-return"
        ]
        if returns:
            content = getattr(returns[-1], "content", None)
            captured["len"] = len(content) if content is not None else 0
        return script(messages, info)

    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("proceed"))
    return captured.get("len")


def _big_return(n: int) -> str:
    return "X" * 20_000


def test_tool_output_limits_spills_oversized_return(tmp_path):
    """Host-side always-active: a 20k return reaches the model as a spill
    handle + preview, never the raw payload."""
    agent = build_agent(
        _settings(tmp_path),
        extra_toolsets=[
            FunctionToolset(tools=[Tool(_big_return, name="big_return")]),
        ],
    )
    captured: dict = {}

    async def script(messages, info):
        has_return = any(
            getattr(p, "part_kind", None) == "tool-return"
            for m in messages
            for p in getattr(m, "parts", [])
        )
        if not has_return:
            return ModelResponse(parts=[ToolCallPart("big_return", {"n": 1})])
        content = next(
            p.content
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "tool-return"
        )
        captured["content"] = content
        return ModelResponse(
            parts=[TextPart(content="done")]
        )

    _grounded(agent, script=script)
    content = captured["content"]
    assert isinstance(content, str)
    assert 0 < len(content) < 20_000  # reduced once, not re-sent in full
    assert "stored to handle" in content  # spill handle + preview


def _flavor_tool(i: int) -> Tool:
    return Tool(lambda v: f"result-{i}-{'y' * 200}", name=f"tool_{i}")


def test_clear_tool_results_replaces_stale_returns(tmp_path):
    """Threshold-driven: once the history exceeds the configured bound, earlier
    tool returns are cleared instead of growing the context forever."""
    tools = FunctionToolset(tools=[_flavor_tool(i) for i in range(6)])
    agent = build_agent(
        _settings(tmp_path),
        extra_capabilities=[
            ClearToolResults(max_messages=2, keep_pairs=0, placeholder="[cleared]"),
        ],
        extra_toolsets=[tools],
    )
    captured: dict = {}
    cursor = {"i": 0}
    sequence = [f"tool_{i}" for i in range(6)]

    async def script(messages, info):
        returns = [
            p
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "tool-return"
        ]
        if cursor["i"] < len(sequence):
            name = sequence[cursor["i"]]
            cursor["i"] += 1
            return ModelResponse(parts=[ToolCallPart(name, {"v": cursor["i"]})])
        cleared = sum(
            1 for p in returns if str(getattr(p, "content", "")).startswith("[cleared]")
        )
        captured["cleared"] = cleared
        captured["seen"] = len(returns)
        return ModelResponse(
            parts=[TextPart(content="done")]
        )

    _grounded(agent, script=script)
    # Six tool calls happened; by the end at least the earliest returns were
    # cleared out of the active history (threshold of 2 messages + keep_pairs 0).
    assert captured.get("seen", 0) >= 1
    assert captured.get("cleared", 0) > 0, captured


def test_context_controls_capabilities_ready_when_authorized(tmp_path):
    agent = build_agent(_settings(tmp_path, enable_context_controls=True))
    names = {type(c).__name__ for c in agent.root_capability.capabilities}
    assert {"ClearToolResults", "ClampOversizedMessages", "WarnNearLimits"} <= names


def test_compaction_strategy_classes_ready():
    """Released context-window strategy types construct without a custom
    summarization framework."""
    strat = SlidingWindowCompaction(max_tokens=60_000)
    assert strat is not None


def test_context_controls_not_composed_by_default_narrow_surface(tmp_path):
    """The default business surface stays narrow: context controls are only
    composed when a deployment authorizes them (activation by policy)."""
    agent = build_agent(_settings(tmp_path))
    names = {type(c).__name__ for c in agent.root_capability.capabilities}
    assert not ({"ClearToolResults", "WarnNearLimits", "ClampOversizedMessages"} & names)
