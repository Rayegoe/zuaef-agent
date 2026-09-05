"""H007 — model-visible tool surface diff for harness alignment lane.

Captures the observable tool surface (AgentInfo.function_tools) for
representative profiles using a deterministic FunctionModel, exactly like
tests/test_generalist_activation.py. Asserts nothing; prints so the host can
diff baseline-vs-candidate output.

Usage:
    python surface_diff.py <config_root>
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps

CONFIG_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
BASE = Path("/tmp/zuaef-surface-diff")
_DEPS = CoreDeps(workspace_root=BASE / "ws", run_id="surface-diff")

CONFIG_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
BASE = Path("/tmp/zuaef-surface-diff")
_DEPS = CoreDeps(workspace_root=BASE / "ws", run_id="surface-diff")
load_dotenv(CONFIG_ROOT / ".env")  # local-only secrets (telegram/wp creds)

# Host ceiling applied equally to every profile run (same blueprint in both
# environments). Core surface stays part of the ceiling; generalist follows
# each profile's own [generalist] requests.
BASE_CEILING = {
    "enable_filesystem": True,
    "enable_tool_output_limits": True,
    "enable_step_persistence": True,
    "enable_knowledge": True,
    "enable_planning": True,
    "enable_skills": True,
}
PROFILE_GENERALIST = {
    "stillevo-fde": {
        "enable_web_search": True,
        "enable_web_fetch": True,
        "enable_tool_search": True,
        "enable_memory": True,
        "enable_conversation_search": True,
        "enable_subagents": True,
        "enable_context_controls": True,
    },
    "quant-decision": {
        "enable_web_search": True,
        "enable_tool_search": True,
        "enable_memory": True,
        "enable_context_controls": True,
    },
}


def capture(agent: Agent[Any, Any]) -> list[str]:
    seen: dict[str, list[str]] = {}

    async def handler(messages, info):
        if "tools" not in seen:
            seen["tools"] = sorted(t.name for t in info.function_tools)
        return ModelResponse(parts=[TextPart(content="done")])

    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("proceed", deps=_DEPS))
    return seen["tools"]


def settings_for(name: str, **flags: bool) -> AgentSettings:
    ws = BASE / name / "workspace"
    st = BASE / name / "state"
    ws.mkdir(parents=True, exist_ok=True)
    st.mkdir(parents=True, exist_ok=True)
    # Only enable_* capability flags flow into the constructor.
    kwargs = cast(dict[str, Any], {k: v for k, v in flags.items() if k.startswith("enable_")})
    return AgentSettings(
        model="test", workspace_root=ws, runtime_state_root=st, **kwargs
    )


def dump(label: str, tools: list[str]) -> None:
    print(f"## {label} ({len(tools)} tools)")
    for tool in tools:
        print(f"  {tool}")


for profile in ("ace-writing", "stillevo-fde", "quant-decision"):
    flags = {**BASE_CEILING, **PROFILE_GENERALIST.get(profile, {})}
    settings = settings_for(profile, **flags)
    try:
        agent, _snap = build_profile_agent(settings, profile=profile, config_root=CONFIG_ROOT)
        dump(f"profile:{profile}", capture(agent))
    except Exception as exc:  # noqa: BLE001 - lane evidence, record only
        print(f"## profile:{profile} COMPOSE_FAILED {type(exc).__name__}: {exc}")

# Representative host-authorized surfaces not default in any shipped profile.
host_surfaces = (
    ("host:repo+shell", {"enable_repo_context": True, "enable_shell": True}),
    # Deferred loading is driven by enable_tool_search + plugin defer_tools
    # (covered by test_phase2_deferred_tools); the host surface here keeps
    # the ToolSearch composition path only.
    ("host:toolsearch", {"enable_tool_search": True}),
)
for label, flags in host_surfaces:
    settings = settings_for(label, **{**BASE_CEILING, **flags})
    agent = build_agent(settings)
    dump(label, capture(agent))