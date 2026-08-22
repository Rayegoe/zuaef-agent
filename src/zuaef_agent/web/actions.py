"""Bounded supervisor actions — an adapter, not a second continuation.

Every action routes through ``continuation.resume_paused_run`` (the single
resume implementation shared with the CLI and the Gateway). This module owns
only: pause-state validation, one in-flight guard per run, and a transient
result note for the UI. Nothing here is durable and no approval semantics
live here — the runtime owns the decision vocabulary.

``resume_paused_run`` is blocking and synchronous (it executes the continued
run to its terminal state), so the API layer runs it on a worker thread and
answers immediately; the UI polls the projection like any other run.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Literal

from ..config import AgentSettings
from ..continuation import resume_paused_run
from ..models import PauseReceipt
from . import readers


class ActionError(Exception):
    """API error with a stable machine code (API-CONTRACT §7)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ActionResult:
    state: str  # "completed" | "failed" | "limit_reached" | "paused" | "error"
    continuation_run_id: str | None
    error: str | None = None


_lock = threading.Lock()
_in_flight: set[str] = set()
_results: dict[str, ActionResult] = {}


def require_paused(settings: AgentSettings, run_id: str) -> PauseReceipt:
    """Validate the pause state before any action is offered or accepted."""
    receipt = readers.read_receipt(settings, run_id)
    if receipt is None:
        raise ActionError("RUN_NOT_FOUND", f"Run {run_id} not found")
    if not isinstance(receipt, PauseReceipt):
        raise ActionError(
            "RUN_NOT_PAUSED", f"Run {run_id} is not paused"
        )
    return receipt


def validate_target(
    receipt: PauseReceipt, tool_call_id: str | None
) -> None:
    """An explicit ``tool_call_id`` must name one of the pending approvals."""
    if tool_call_id is None:
        return
    pending = {
        entry.get("tool_call_id") for entry in receipt.pending_approvals
    }
    if tool_call_id not in pending:
        raise ActionError(
            "INVALID_ACTION",
            f"tool_call_id {tool_call_id!r} is not a pending approval of run {receipt.run_id}",
        )


def is_in_flight(run_id: str) -> bool:
    with _lock:
        return run_id in _in_flight


def action_state(run_id: str) -> dict[str, Any] | None:
    with _lock:
        if run_id in _in_flight:
            return {"state": "in_flight", "continuation_run_id": None}
        result = _results.get(run_id)
    if result is None:
        return None
    return {
        "state": result.state,
        "continuation_run_id": result.continuation_run_id,
        "error": result.error,
    }


def start_resume(
    settings: AgentSettings,
    paused_run_id: str,
    *,
    decision: Literal["approve", "deny"],
    reason: str | None = None,
) -> None:
    """Register and launch one resume on a worker thread; returns immediately.

    Raises :class:`ActionError` when the run is missing, not paused, or
    already being resumed. The thread is a daemon: if the console process
    exits mid-resume the runtime's own durable frontier (interrupted
    snapshot + pause receipt) stays recoverable — durability is owned by the
    runtime, not by this process.
    """
    require_paused(settings, paused_run_id)
    with _lock:
        if paused_run_id in _in_flight:
            raise ActionError(
                "INVALID_ACTION",
                f"Run {paused_run_id} already has a resume in flight",
            )
        _in_flight.add(paused_run_id)
    thread = threading.Thread(
        target=_run_resume,
        args=(settings, paused_run_id, decision, reason),
        name=f"zuaef-web-resume-{paused_run_id[:8]}",
        daemon=True,
    )
    thread.start()


def _run_resume(
    settings: AgentSettings,
    paused_run_id: str,
    decision: Literal["approve", "deny"],
    reason: str | None,
) -> None:
    try:
        outcome = resume_paused_run(
            settings,
            paused_run_id,
            decision=decision,
            reason=reason or None,
        )
        if hasattr(outcome, "pause_receipt"):
            result = ActionResult(
                state="paused",
                continuation_run_id=outcome.pause_receipt.run_id,
            )
        else:
            result = ActionResult(
                state=outcome.receipt.execution_state,
                continuation_run_id=outcome.receipt.run_id,
                error=outcome.receipt.error,
            )
    # Deliberately broad: this runs on a bare worker thread — any escape would
    # kill the thread silently. The error is surfaced verbatim to the operator.
    except Exception as exc:  # noqa: BLE001
        result = ActionResult(
            state="error", continuation_run_id=None, error=str(exc)
        )
    with _lock:
        _in_flight.discard(paused_run_id)
        _results[paused_run_id] = result
