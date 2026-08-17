from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

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
from .models import CoreDeps, RunSummary
from .providers import resolve_model

CORE_INSTRUCTIONS = """\
You are the single outcome-owning core agent.

Execution rules:
1. Own the user's outcome, not merely the next message.
2. For complex work, make a short plan and then execute it; do not create process for its own sake.
3. Inspect existing files/knowledge before creating replacements.
4. Put long deliverables in workspace/artifacts and return only a thin RunSummary.
5. Durable knowledge belongs under workspace/knowledge via the Knowledge tools; knowledge/** is read-only for general file tools. concept/claim/method/reference nodes require at least one observed source; never fabricate sources.
6. Prefer an existing Capability, Toolset, or deferred Skill over changing the core.
7. If evidence or access is insufficient, end partial/blocked and name the unknown instead of guessing.
8. Large tool outputs are retrieval material, not prompt material. Use spill handles and progressively read only what is needed.
9. External or destructive side effects must use PydanticAI native approval on the tool definition. Model intent is not authorization.
10. Durable step logs and receipts are evidence of execution; do not invent success when a tool effect is unresolved.

RunSummary claims are verified by the host, not trusted:
11. `artifacts` lists workspace-relative paths under artifacts/ that THIS run created or modified. Claiming a pre-existing unchanged file is rejected and downgrades the run.
12. `evidence` entries must be parseable refs: `artifact:<path>`, `knowledge:<id>`, or `tool-effect:<tool_call_id>`. Unverifiable refs are dropped and downgrade a completed claim.
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
    ".git/*",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "**/secrets*",
]


def build_agent(
    settings: AgentSettings,
    *,
    run_id: str | None = None,
    instructions: str | None = None,
    extra_capabilities: Sequence[AbstractCapability[CoreDeps]] = (),
    extra_toolsets: Sequence[AbstractToolset[CoreDeps]] = (),
    extra_skill_dirs: Sequence[Path] = (),
) -> Agent[CoreDeps, RunSummary | DeferredToolRequests]:
    """Build one core agent through explicit composition; there is intentionally no registry.

    ``instructions`` defaults to ``CORE_INSTRUCTIONS``; single-purpose surfaces
    (e.g. the production writer) pass their own so core noise (spill handles,
    knowledge nodes) cannot derail the model.

    ``extra_skill_dirs`` extends the Skills capability's source directories
    (plugin skill dirs; the base ``settings.skills_dir`` stays first, so a
    local skill wins a duplicate id over an installed plugin's).
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
    capabilities.extend(extra_capabilities)

    return Agent(
        resolve_model(settings),
        deps_type=CoreDeps,
        output_type=[RunSummary, DeferredToolRequests],
        instructions=instructions or CORE_INSTRUCTIONS,
        capabilities=capabilities,
        toolsets=list(extra_toolsets),
        name="zuaef",
    )
