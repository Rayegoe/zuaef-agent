"""Gateway runtime bridge — SPEC v0.3 §20, §22, §27.

The bridge is the ONLY place the Gateway touches the shared core seam. It
never imports a business toolset directly: new runs compose through
``build_profile_agent`` and resumes execute the shared ``resume_paused_run``
continuation. Prompt projection is mechanical (attachment paths), profile
validation is resolve-only — no business understanding, no model, no
approval logic here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
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
from ..runtime import RuntimeOutcome, execute_run
from .models import InboundEnvelope

ATTACHMENT_BLOCK = "Attached files available in the workspace:"


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


def start_profile_run(
    *,
    settings: AgentSettings,
    profile: str | None,
    prompt: str,
    conversation_id: str,
    config_root: Path | None = None,
    run_id: str | None = None,
) -> RuntimeOutcome:
    """Compose a new run through the shared seam (SPEC §27).

    ``profile=None`` composes the core agent without a profile; the Gateway
    production proof must use a profile. ``run_id`` defaults to a fresh id;
    the Gateway pre-mints it so the session binding can record the active run
    before execution (SPEC §29).
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
    )
    return execute_run(
        agent,
        deps,
        prompt=prompt,
        settings=settings,
        run_id=run_id,
        conversation_id=conversation_id,
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
