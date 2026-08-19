from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai_harness.filesystem import FileSystem
from pydantic_ai_harness.planning import Planning
from pydantic_ai_harness.skills import Skills
from pydantic_ai_harness.step_persistence import FileStepStore, StepPersistence
from pydantic_ai_harness.tool_output_limits import LocalFileStore, ToolOutputLimits

from .config import AgentSettings
from .knowledge_capability import Knowledge
from .models import CoreDeps
from .providers import resolve_model

CORE_INSTRUCTIONS = """\
You are the single outcome-owning FDE agent.

Own the user's real outcome, not merely the next message. Use available context
and tools when they materially help — tools are capabilities, not a required
workflow; judge for yourself what the task actually needs. For complex work a
short plan helps; do not create process for its own sake.

Inspect existing files and knowledge before creating replacements. Durable
knowledge belongs under workspace/knowledge via the Knowledge tools (knowledge/**
is read-only for general file tools) and requires an observed source; never
fabricate sources. Distinguish observed facts from assumptions and name
unknowns instead of guessing.

For normal analysis, writing, revision and planning, return the useful result
directly to the current user. Long durable work products may be persisted under
workspace/artifacts when the task or domain calls for it.

An external or destructive action may only happen through the corresponding
approval-gated tool. Never infer external delivery merely because a customer
Case exists. Do not claim an external action happened unless the corresponding
tool actually completed.

Large tool outputs are retrieval material, not prompt material: use spill
handles and progressively read only what is needed.
"""

# Harness FileSystem default protections plus the knowledge area: general file
# tools may read knowledge/** but only the Knowledge Capability may write it.
# Case control-plane files (BusinessCase doc, Barry's policy overrides) are
# supervisor-editable only; the model writes situation/trajectory/drafts
# exclusively through the zuaef-case toolset.
FILESYSTEM_PROTECTED_PATTERNS = [
    "knowledge/*",
    "cases/*/case.md",
    "cases/*/policy-overrides.md",
    # Artifacts are written by toolsets (e.g. ACE save_artifact snapshot) and
    # verified by the host (pre/post diff). Generic model-facing file tools
    # must not be able to plant files under artifacts/** and have them counted
    # as verified run output — that would bypass domain validation (Writing
    # v0.2, WRITE-9 provenance invariant).
    "artifacts/*",
    ".git/*",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "**/secrets*",
]


def generalist_capabilities(
    settings: AgentSettings,
    *,
    sub_agents: Sequence[Any] = (),
) -> list[AbstractCapability[CoreDeps]]:
    """Compose the upstream generalist platform surface (SPEC v2.1 §4, T006).

    This is a small constructor/helper over released public primitives — it is
    NOT a ZUAEF harness framework. Capability *availability* here means "the
    runtime can compose this upstream primitive when the deployment authorizes
    it". AUTHORIZATION is per-deployment (settings flags); LOADING and
    INVOKING are task-driven by the model. The default business surface is
    untouched, so no deployment pays tool-schema/context cost for capabilities
    it did not opt in.

    ``sub_agents`` registers named upstream SubAgent delegates; the delegates
    are never the default topology — the one FDE Agent owns the outcome and a
    delegate runs only when isolated/parallel work is genuinely useful.
    """
    capabilities: list[AbstractCapability[CoreDeps]] = []

    if settings.enable_repo_context:
        from pydantic_ai_harness.repo_context import RepoContext

        repo_dir = (settings.repo_context_dir or settings.workspace_root).resolve()
        capabilities.append(
            RepoContext[CoreDeps](
                workspace_dir=repo_dir,
                home_dir=None,
                filenames=("AGENTS.md", "README.md"),
            )
        )

    if settings.enable_web_search:
        from pydantic_ai.capabilities import WebSearch

        # Official WebSearch capability (native provider WebSearchTool when the
        # model supports it). No local reimplementation; deployments needing a
        # custom backend pass `WebSearch(native=False, local=...)` themselves.
        capabilities.append(WebSearch[CoreDeps](native=True))

    if settings.enable_web_fetch:
        from pydantic_ai.capabilities import WebFetch

        capabilities.append(WebFetch[CoreDeps](native=True))

    if settings.enable_tool_search:
        from pydantic_ai.capabilities import ToolSearch

        # Official ToolSearch: compact capability catalog with on-demand tool
        # activation — keeps the active tool/context surface bounded.
        capabilities.append(ToolSearch[CoreDeps]())

    if settings.enable_memory:
        from pydantic_ai_harness.memory import FileStore, Memory

        capabilities.append(
            Memory[CoreDeps](
                store=FileStore(directory=settings.state_root / "memory"),
                agent_name="zuaef",
                namespace="default",
            )
        )

    if settings.enable_conversation_search and settings.enable_step_persistence:
        from pydantic_ai_harness.conversation_search import (
            ConversationSearch,
            SnapshotHistorySource,
        )

        capabilities.append(
            ConversationSearch[CoreDeps](
                source=SnapshotHistorySource(
                    store=FileStepStore(settings.step_store_dir)
                ),
                scope="all",
            )
        )

    if settings.enable_subagents:
        from pydantic_ai_harness.subagents import SubAgents

        capabilities.append(SubAgents[CoreDeps](agents=sub_agents))

    if settings.enable_context_controls:
        from pydantic_ai_harness.compaction import (
            ClampOversizedMessages,
            ClearToolResults,
            WarnNearLimits,
        )

        # Threshold-driven context controls: ClearToolResults needs at least one
        # bound (we use token pressure), oversized parts are clamped, and the
        # model/host are warned near limits. Defaults stay conservative.
        capabilities.append(ClearToolResults[CoreDeps](max_tokens=80_000, keep_pairs=3))
        capabilities.append(ClampOversizedMessages[CoreDeps](max_part_chars=40_000))
        capabilities.append(
            WarnNearLimits[CoreDeps](max_context_fraction=0.8, context_window=200_000)
        )

    if settings.enable_shell:
        from pydantic_ai_harness.shell import Shell

        # Shell is the most privileged generalist primitive: only composed when
        # an authorized, trusted execution environment turns it on. The harness
        # default denied-commands list (rm/rf/dd/…) stays untouched.
        capabilities.append(Shell[CoreDeps](cwd=settings.workspace_root))

    return capabilities


def build_agent(
    settings: AgentSettings,
    *,
    run_id: str | None = None,
    instructions: str | None = None,
    extra_capabilities: Sequence[AbstractCapability[CoreDeps]] = (),
    extra_toolsets: Sequence[AbstractToolset[CoreDeps]] = (),
    extra_skill_dirs: Sequence[Path] = (),
    sub_agents: Sequence[Any] = (),
) -> Agent[CoreDeps, str | DeferredToolRequests]:
    """Build one core agent through explicit composition; there is intentionally no registry.

    ``instructions`` defaults to ``CORE_INSTRUCTIONS``; single-purpose surfaces
    (e.g. the production writer) pass their own so core noise (spill handles,
    knowledge nodes) cannot derail the model.

    ``extra_skill_dirs`` extends the Skills capability's source directories
    (plugin skill dirs; the base ``settings.skills_dir`` stays first, so a
    local skill wins a duplicate id over an installed plugin's).

    ``sub_agents`` are optional registered upstream SubAgent delegates, used
    only when the deployment authorizes the SubAgents capability.
    """
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.state_root.mkdir(parents=True, exist_ok=True)

    capabilities: list[AbstractCapability[CoreDeps]] = []
    if settings.enable_filesystem:
        capabilities.append(
            FileSystem[CoreDeps](
                root_dir=settings.workspace_root,
                protected_patterns=list(FILESYSTEM_PROTECTED_PATTERNS),
            )
        )

    if settings.enable_tool_output_limits:
        capabilities.append(
            ToolOutputLimits[CoreDeps](
                store=LocalFileStore(base_dir=settings.tool_result_dir),
            )
        )

    if settings.enable_step_persistence:
        capabilities.append(
            StepPersistence[CoreDeps](
                store=FileStepStore(
                    settings.step_store_dir,
                    max_snapshots_per_run=settings.max_snapshots_per_run,
                ),
                agent_name="zuaef",
                run_id=run_id,
            )
        )

    if settings.enable_knowledge:
        capabilities.append(Knowledge())
    if settings.enable_planning:
        capabilities.append(Planning[CoreDeps]())
    if settings.enable_skills:
        skill_dirs = [
            directory
            for directory in (settings.skills_dir, *extra_skill_dirs)
            if directory.exists()
        ]
        if skill_dirs:
            capabilities.append(Skills[CoreDeps](skill_dirs))

    capabilities.extend(generalist_capabilities(settings, sub_agents=sub_agents))
    capabilities.extend(extra_capabilities)

    return Agent(
        resolve_model(settings),
        deps_type=CoreDeps,
        output_type=[str, DeferredToolRequests],
        instructions=instructions or CORE_INSTRUCTIONS,
        capabilities=capabilities,
        toolsets=list(extra_toolsets),
        name="zuaef",
    )
