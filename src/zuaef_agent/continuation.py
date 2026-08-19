"""Shared pause-continuation seam — the single resume implementation.

Both the CLI (``zuaef-agent resume``) and the Gateway approval flow execute
exactly this orchestration; there is no second resume logic anywhere. A
paused run is rebuilt from its own frozen evidence: the ``PauseReceipt`` is
the composition authority, StepPersistence supplies the message history, and
the operator decision becomes ``DeferredToolResults`` for the pending
approvals/calls. The mutable current profile is never consulted.
"""

from __future__ import annotations

import asyncio
from typing import Literal
from uuid import uuid4

from pydantic_ai import (
    DeferredToolRequests,
    DeferredToolResults,
    ToolDenied,
    ToolFailed,
)
from pydantic_ai.messages import ToolCallPart

from .composition import (
    Discover,
    VersionFor,
    build_profile_agent,
    discover_entry_points,
    version_for,
)
from .config import AgentSettings
from .core import build_agent
from .models import CoreDeps, PauseReceipt
from .receipt_store import ReceiptStore
from .runtime import RuntimeOutcome, execute_run

DEFAULT_DENY_REASON = "denied by operator"


def resume_paused_run(
    settings: AgentSettings,
    paused_run_id: str,
    *,
    decision: Literal["approve", "deny"],
    reason: str | None = None,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> RuntimeOutcome:
    """Resume a paused run exactly once, from its frozen composition and history.

    Contract (SPEC v0.3 §25), in strict order:

    1. ``ReceiptStore.read(paused_run_id)``
    2. require ``state == paused`` (raises ``ValueError`` otherwise)
    3. ``FileStepStore(settings.step_store_dir)``
    4. ``continue_run(store, run_id=paused_run_id)`` — real StepPersistence
       message history, not a fresh prompt
    5. rebuild ``DeferredToolRequests`` from ``pending_approvals``
    6. ``DeferredToolResults()``
    7. every pending approval: ``approve`` → ``True``, ``deny`` → ``ToolDenied``
    8. every pending external call: ``ToolFailed``
    9. new continuation ``run_id``
    10. rebuild the agent from ``receipt.composition`` (frozen snapshot) or the
        core agent when the pause receipt has no composition
    11. ``CoreDeps(new run_id)``
    12. ``execute_run`` with the restored history, resolved tool results,
        prior pause receipt, conversation id and frozen composition

    A version/entry-point drift against the frozen snapshot fails here
    (``CompositionError``) before any model request.
    """
    receipt = ReceiptStore(settings.state_root).read(paused_run_id)
    if getattr(receipt, "state", "terminal") != "paused":
        raise ValueError(
            f"run {paused_run_id} is not paused; resume needs a pause receipt"
        )
    assert isinstance(receipt, PauseReceipt)

    from pydantic_ai_harness.step_persistence import FileStepStore, continue_run

    store = FileStepStore(settings.step_store_dir)
    # The pause frontier is persisted as an `interrupted` snapshot (the pending
    # approvals are unresolved tool calls by definition); include_interrupted
    # makes continue_run return exactly that frontier.
    history = asyncio.run(
        continue_run(store, run_id=paused_run_id, include_interrupted=True)
    )

    requests = DeferredToolRequests(
        approvals=[
            ToolCallPart(
                tool_name=entry.get("tool_name") or "",
                args=entry.get("args") or {},
                tool_call_id=entry.get("tool_call_id") or "",
            )
            for entry in receipt.pending_approvals
        ]
    )
    results = DeferredToolResults()
    for call in requests.approvals:
        results.approvals[call.tool_call_id] = (
            True if decision == "approve" else ToolDenied(reason or DEFAULT_DENY_REASON)
        )
    for entry in receipt.pending_calls:
        results.calls[entry["tool_call_id"]] = ToolFailed(
            "no external executor configured"
        )

    run_id = uuid4().hex
    composition = receipt.composition
    if composition is not None:
        # The pause receipt is the composition authority; the mutable
        # current profile is ignored, and an installed version/entry point
        # that drifted from the frozen snapshot fails here (process error).
        agent, _ = build_profile_agent(
            settings,
            run_id=run_id,
            snapshot=composition,
            discover=discover,
            version_for=version_for,
        )
    else:
        agent = build_agent(settings, run_id=run_id)
    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id=run_id,
        # The pause receipt freezes Case identity: a continuation resumes the
        # SAME bound Case, never a different one (SPEC v1.0 §5.6/§7.3).
        case_id=getattr(receipt, "case_id", None),
    )
    return execute_run(
        agent,
        deps,
        settings=settings,
        run_id=run_id,
        conversation_id=receipt.conversation_id,
        message_history=history,
        deferred_tool_results=results,
        prior_pause_receipt=receipt,
        composition=composition,
    )
