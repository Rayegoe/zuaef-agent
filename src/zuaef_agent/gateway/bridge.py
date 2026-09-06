"""Gateway runtime bridge — SPEC v0.3 §20, §22, §27.

The bridge is the ONLY place the Gateway touches the shared core seam. It
never imports a business toolset directly: new runs compose through
``build_profile_agent`` and resumes execute the shared ``resume_paused_run``
continuation. Prompt projection is mechanical (attachment paths), profile
validation is resolve-only — no business understanding, no model, no
approval logic here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from ..composition import (
    Discover,
    VersionFor,
    build_profile_agent,
    discover_entry_points,
    resolve_profile,
    version_for,
)
from ..config import AgentSettings
from ..continuation import resume_paused_run
from ..models import CoreDeps
from ..receipt_store import ReceiptStore
from ..runtime import RuntimeOutcome, execute_run
from .interaction_projection import ActorRole, project_interaction_context
from .models import InboundEnvelope

ATTACHMENT_BLOCK = "Attached files available in the workspace:"
CONTEXT_SEPARATOR = "\n\n---\n\n"


def project_prompt(envelope: InboundEnvelope) -> str:
    """Mechanical prompt projection (SPEC §20): the inbound text plus
    workspace-relative attachment paths. No summarization, no domain
    detection, no tool selection."""
    prompt = envelope.text.strip()
    if not envelope.attachments:
        return prompt
    lines = [prompt, "", ATTACHMENT_BLOCK]
    lines.extend(f"- {ref.local_path}" for ref in envelope.attachments)
    return "\n".join(lines)


def validate_profile(
    profile: str,
    settings: AgentSettings,
    *,
    config_root: Path | None = None,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> None:
    """Resolve-only profile validation (SPEC §22): raises ``CompositionError``
    before the process or a ``/profile`` switch trusts the name."""
    resolve_profile(
        profile,
        settings,
        config_root=config_root,
        discover=discover,
        version_for=version_for,
    )


def prior_run_history(
    settings: AgentSettings,
    *,
    run_id: str,
    conversation_id: str,
    receipts: ReceiptStore,
) -> list[Any] | None:
    """Restore a prior terminal run's message history through the public
    StepStore API (SPEC v2.1 §15 / T010).

    Returns ``None`` when the prior run is unknown, belongs to a different
    conversation (a reset /new session must not leak history), or has no
    restorable ``complete`` snapshot. The restored history is handed to the
    next ``Agent.run(message_history=...)`` with a fresh ``run_id`` and the
    same ``conversation_id`` — real continuity, not a fresh prompt.
    """
    try:
        receipt = receipts.read(run_id)
    except (FileNotFoundError, ValueError):
        return None
    if getattr(receipt, "conversation_id", None) != conversation_id:
        return None
    from pydantic_ai_harness.step_persistence import FileStepStore, fork_run

    store = FileStepStore(settings.step_store_dir)
    try:
        history = asyncio.run(fork_run(store, run_id=run_id))
    except LookupError:
        return None
    return list(history) if history else None


def start_profile_run(
    *,
    settings: AgentSettings,
    profile: str | None,
    prompt: str,
    conversation_id: str,
    config_root: Path | None = None,
    run_id: str | None = None,
    message_history: Sequence[Any] | None = None,
    case_id: str | None = None,
    surface: str | None = None,
    actor_role: ActorRole | None = None,
) -> RuntimeOutcome:
    """Compose a new run through the shared seam (SPEC §27).

    ``profile=None`` composes the core agent without a profile; the Gateway
    production proof must use a profile. ``run_id`` defaults to a fresh id;
    the Gateway pre-mints it so the session binding can record the active run
    before execution (SPEC §29).

    ``message_history`` carries the prior turn's restored history (T010) so a
    new run in the same conversation starts from real prior context.

    ``case_id`` is the session's deterministically bound Case (SPEC v1.0 §5):
    the server threads it into the run's CoreDeps, where Case tools enforce
    isolation. The model never guesses it.

    ``surface``/``actor_role`` are host-grounded interaction facts (P3B-3
    T001/T002): the model-visible request assembles in a deterministic order —
    host-grounded current interaction (who is talking now, where a normal
    reply goes), then the literal raw user request, untouched. A bound Case's
    durable background is contributed by the composed Case plugin capability
    (v1.2 T005) — the bridge has no Case-specific context branch.
    """
    run_id = run_id or uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile=profile,
        config_root=config_root,
    )
    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id=run_id,
        # Opaque bindings (v1.2 SPEC §4): the server threads the session's
        # bound identities into the run; the kernel preserves them across
        # pause/resume but never inspects their meaning.
        bindings={"case": case_id} if case_id else {},
    )
    # Context assembly (P3B-2 §6 / P3B-3 T003): host-grounded interaction
    # facts precede the raw user request, which stays byte-literal at the
    # tail. Case background is NOT projected here — the composed Case plugin
    # capability contributes it as dynamic instructions (v1.2 T005).
    blocks: list[str] = []
    interaction = project_interaction_context(
        surface, actor_role, case_id=case_id, active_profile=profile
    )
    if interaction:
        blocks.append(interaction)
    blocks.append(prompt)
    return execute_run(
        agent,
        deps,
        prompt=CONTEXT_SEPARATOR.join(blocks),
        settings=settings,
        run_id=run_id,
        conversation_id=conversation_id,
        message_history=list(message_history) if message_history is not None else None,
        composition=snapshot,
    )


def resume_for_surface(
    settings: AgentSettings,
    paused_run_id: str,
    *,
    decision: Literal["approve", "deny"],
    reason: str | None = None,
) -> RuntimeOutcome:
    """Thin typed alias over the shared continuation seam — the Gateway never
    owns resume logic of its own (SPEC §24)."""
    return resume_paused_run(
        settings,
        paused_run_id,
        decision=decision,
        reason=reason,
    )
