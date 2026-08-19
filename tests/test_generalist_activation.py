"""Activation-policy tests: the five capability lifecycle states stay distinct.

SPEC v2.1 §2 (AVAILABLE / AUTHORIZED / DISCOVERABLE / LOADED / INVOKED),
§5 (default activation policy) and TASKS T007 Cases A–D.

How each state is proven with a deterministic FunctionModel (no model
request, no network):

- AVAILABLE    — the generalist composition helper builds the capability.
- AUTHORIZED   — the settings flag controlling it is on for this deployment.
- DISCOVERABLE — the capability's tools appear as schema entries the model can
                 see (captured from ``AgentInfo.function_tools``).
- LOADED       — the relevant tool is present in the active schema.
- INVOKED      — the scripted model actually emits a ToolCallPart for it.
- DORMANT      — a capability present-but-unused stays uncalled for the task;
                 an unrelated capability is simply not composed.

The exact tool-name set is asserted on the observable surface, never on
internal registries.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.capabilities import WebSearch
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.tools import RunContext
from pydantic_ai_harness.subagents import SubAgent

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent


def _settings(tmp_path: Path, **cap_flags) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_skills=False,
        **cap_flags,
    )


def _run_capture(
    agent: Agent,
    *,
    sequence: list[tuple[str, dict]],
) -> tuple[list[str], list[str]]:
    """Run ``agent`` with a scripted model; return (visible_tools, invoked_tools).

    The script is an ordered list of ``(tool_name, args)`` the model "chooses"
    to call; once exhausted the model returns natural text.
    """
    captured: dict[str, list[str]] = {"tools": [], "invoked": []}
    seq = list(sequence)

    async def handler(messages, info):
        if not captured["tools"]:
            captured["tools"] = sorted(t.name for t in info.function_tools)
        if seq:
            name, args = seq.pop(0)
            captured["invoked"].append(name)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart(content="done")])

    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("proceed"))
    return captured["tools"], captured["invoked"]


def _writing_agent(tmp_path: Path) -> Agent:
    """Core agent with the ACE-writing business toolset composed."""
    from fixture_plugins import writing as writing_plugin

    from zuaef_agent.plugin_api import PluginEnv

    bundle = writing_plugin.create_plugin(
        PluginEnv(
            plugin_id="fixture-ace-writing",
            plugin_version="0.2.1",
            workspace_root=tmp_path / "workspace",
            state_root=tmp_path / ".zuaef-state",
        ),
        {"ace_root": "/v1"},
    )
    return build_agent(
        _settings(tmp_path),
        extra_toolsets=list(bundle.toolsets),
    )


# ── Case A — internal writing task ──────────────────────────────────────────


def test_case_a_internal_writing_web_shell_subagent_dormant(tmp_path):
    agent = _writing_agent(tmp_path)
    tools, invoked = _run_capture(agent, sequence=[("list_materials", {"query": "demo"})])

    # Writing capability is LOADED and gets INVOKED for the task.
    assert "list_materials" in tools
    assert invoked == ["list_materials"]

    # Web, shell and subagent remain DORMANT for an internal writing task:
    # present-but-unused tools stay uncalled.
    assert not any(
        name in invoked for name in ("web_search", "run_command", "web_fetch")
    )


# ── Case B — current external research task ─────────────────────────────────


def test_case_b_external_research_web_loads_invokes_domains_dormant(tmp_path):
    def web_search(ctx: RunContext, query: str) -> str:
        return f"stub results for {query}"

    agent = build_agent(
        _settings(tmp_path),
        # Official WebSearch capability backed by an offline local strategy —
        # IO-free, so the deterministic test can prove LOAD + INVOKE without a
        # search backend. The local callable is named `web_search` so the tool
        # surface exposes exactly that name.
        extra_capabilities=[WebSearch(native=False, local=web_search)],
    )
    tools, invoked = _run_capture(agent, sequence=[("web_search", {"query": "latest API"})])

    # Web capability is DISCOVERABLE + LOADED, and is INVOKED for research.
    assert "web_search" in tools
    assert invoked == ["web_search"]

    # Unrelated WordPress/budget domain capabilities stay DORMANT.
    assert not any(
        name in tools for name in ("web_fetch", "list_materials", "publish_article")
    )


# ── Case C — repository task ────────────────────────────────────────────────


def test_case_c_repo_task_repo_and_shell_available(tmp_path):
    agent = build_agent(_settings(tmp_path, enable_repo_context=True, enable_shell=True))
    tools, invoked = _run_capture(
        agent,
        sequence=[("inventory_agent_context", {})],
    )

    # RepoContext AVAILABLE + LOADED for a repository task; it is INVOKED.
    assert "inventory_agent_context" in tools
    assert "inventory_agent_context" in invoked
    # Shell is AUTHORIZED in this trusted deployment and present in the surface.
    assert "run_command" in tools
    # A client-writing capability is unrelated and stays dormant (not composed).
    assert "list_materials" not in tools

    # `inventory_agent_context` requires no args and runs against the repo dir.
    assert invoked == ["inventory_agent_context"]


# ── Case D — isolated parallel task ─────────────────────────────────────────


def _subagent_agent(tmp_path: Path) -> Agent:
    delegate = Agent(
        FunctionModel(
            lambda messages, info: ModelResponse(parts=[TextPart("delegate done")])
        ),
        output_type=str,
        name="reporter",
    )
    return build_agent(
        _settings(tmp_path, enable_subagents=True),
        sub_agents=[
            SubAgent(agent=delegate, name="reporter", description="isolated research")
        ],
    )


def test_case_d_subagent_available_and_discoverable(tmp_path):
    agent = _subagent_agent(tmp_path)
    tools, invoked = _run_capture(agent, sequence=[])
    # SubAgent capability is available and the `delegate_task` tool (with the
    # `reporter` delegate) is discoverable in the tool surface...
    assert "delegate_task" in tools
    # ...but SubAgents are never the default topology: no delegate is invoked
    # unless the task needs it.
    assert invoked == []


def test_case_d_subagent_tool_can_be_invoked(tmp_path):
    agent = _subagent_agent(tmp_path)
    tools, _ = _run_capture(agent, sequence=[])
    assert "delegate_task" in tools
    _, invoked = _run_capture(
        agent,
        sequence=[("delegate_task", {"agent_name": "reporter", "task": "summarize"})],
    )
    assert invoked[0] == "delegate_task"
