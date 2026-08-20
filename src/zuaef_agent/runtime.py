from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic_ai import (
    DeferredToolRequests,
    DeferredToolResults,
    RunUsage,
    ToolDenied,
    ToolFailed,
    UsageLimitExceeded,
    UsageLimits,
)

from .config import AgentSettings
from .core import build_agent
from .integrity import (
    IntegrityError,
    latest_tool_effects,
    read_tool_effects,
    snapshot_artifacts,
    verify_artifact,
)
from .knowledge_store import KnowledgeStore
from .models import (
    ArtifactFact,
    CompositionSnapshot,
    CoreDeps,
    ExecutionState,
    PauseReceipt,
    RunReceipt,
    ToolEffectFact,
)
from .receipt_store import ReceiptStore


def _usage_payload(result: object) -> dict[str, Any]:
    """Best-effort compatibility adapter across PydanticAI result usage shapes."""
    value = result if isinstance(result, RunUsage) else getattr(result, "usage", None)
    if callable(value):
        value = value()
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())  # type: ignore[attr-defined,union-attr]
    if is_dataclass(value):
        return asdict(value)  # type: ignore[arg-type]
    if isinstance(value, dict):
        return dict(value)
    return {"repr": repr(value)}


def _usage_complete(payload: dict[str, Any]) -> bool:
    """True only when the usage accounting is actually complete."""
    requests = payload.get("requests")
    total = payload.get("total_tokens")
    input_tokens = payload.get("input_tokens")
    output_tokens = payload.get("output_tokens")
    if not isinstance(requests, int) or requests <= 0:
        return False
    return total is not None or (input_tokens is not None and output_tokens is not None)


def _model_label(settings: AgentSettings) -> str:
    if settings.openai_base_url and settings.compat_model:
        return settings.compat_model
    return str(settings.model)


def _call_snapshot(call: Any) -> dict[str, Any]:
    args = getattr(call, "args", None)
    if not isinstance(args, dict):
        as_dict = getattr(call, "args_as_dict", None)
        if callable(as_dict):
            try:
                args = as_dict()
            except Exception:  # noqa: BLE001 — best-effort arg snapshot for receipts
                args = str(args)
    return {
        "tool_name": getattr(call, "tool_name", None),
        "tool_call_id": getattr(call, "tool_call_id", None),
        "args": args,
    }


@dataclass(kw_only=True)
class TerminalRun:
    """A run that reached a business terminal state with an operational receipt.

    ``presentation`` is the user-facing natural-language result (the model's
    terminal text on a normal completion, a bounded user-safe explanation on
    failure); ``receipt`` records execution facts only. Presentation never
    depends on the receipt schema.
    """

    presentation: str
    receipt: RunReceipt


@dataclass(kw_only=True)
class PausedRun:
    """A run paused awaiting approval; continue it via message history + DeferredToolResults."""

    requests: DeferredToolRequests
    message_history: list[Any]
    conversation_id: str
    pause_receipt: PauseReceipt


RuntimeOutcome = TerminalRun | PausedRun

# Bounded host summary for a natural-text terminal (P3B-2 §4.1): the receipt
# records that the run returned its result, never the result text itself.
NATURAL_COMPLETION_OUTCOME = "Returned the result to the current user."


def _recheck_inherited_artifact(
    recorded: ArtifactFact,
    *,
    workspace_root: Any,
) -> ArtifactFact:
    """Re-read a pause-settled artifact and require its bytes to remain unchanged."""
    current = verify_artifact(recorded.path, workspace_root=workspace_root, snapshot={})
    if current.size != recorded.size or current.sha256 != recorded.sha256:
        raise IntegrityError(
            f"inherited artifact changed after pause: {recorded.path!r}"
        )
    return current


def _changed_artifact_facts(
    workspace_root: Any,
    snapshot: dict[str, str],
    *,
    inherited: Sequence[ArtifactFact] = (),
) -> list[ArtifactFact]:
    """Byte facts for every artifact this run created or modified.

    ``inherited`` are pause-settled facts whose bytes must remain unchanged.
    """
    facts: list[ArtifactFact] = []
    seen: set[str] = set()
    for recorded in inherited:
        try:
            facts.append(_recheck_inherited_artifact(recorded, workspace_root=workspace_root))
        except IntegrityError:
            continue  # integrity anomaly is recorded by the caller as unresolved
        seen.add(recorded.path)
    for path, digest in snapshot_artifacts(workspace_root).items():
        if snapshot.get(path) == digest:
            continue
        if path in seen:
            continue
        try:
            facts.append(verify_artifact(path, workspace_root=workspace_root, snapshot=snapshot))
        except IntegrityError:
            continue
    return facts


def _tool_effect_facts(
    settings: AgentSettings,
    run_id: str,
) -> tuple[list[ToolEffectFact], list[ToolEffectFact]]:
    """Ledger facts and unresolved (started-never-settled) facts for a run."""
    effect_records = (
        latest_tool_effects(read_tool_effects(settings.step_store_dir, run_id))
        if settings.enable_step_persistence
        else []
    )
    facts: list[ToolEffectFact] = []
    unresolved: list[ToolEffectFact] = []
    for record in effect_records:
        call_id = record.get("tool_call_id")
        tool_name = record.get("tool_name")
        status = record.get("status")
        if (
            not isinstance(call_id, str)
            or not call_id
            or not isinstance(tool_name, str)
            or not tool_name
        ):
            continue  # malformed ledger row — not a settled fact
        if status not in {"started", "completed", "failed"}:
            continue
        if record.get("run_id") != run_id:
            continue  # foreign run: outside this ledger
        fact = ToolEffectFact(
            tool_call_id=call_id,
            tool_name=tool_name,
            status=status,  # type: ignore[arg-type]
        )
        if status == "started":
            unresolved.append(fact)
        facts.append(fact)
    return facts, unresolved


def finalize_terminal(
    *,
    settings: AgentSettings,
    run_id: str,
    conversation_id: str,
    model_label: str,
    started_at: datetime,
    usage: dict[str, Any],
    snapshot: dict[str, str],
    execution_state: ExecutionState,
    outcome: str,
    presentation: str | None = None,
    prior_pause_receipt: PauseReceipt | None = None,
    error: str | None = None,
    composition: CompositionSnapshot | None = None,
    bindings: dict[str, str] | None = None,
) -> TerminalRun:
    """Host settlement boundary: record operational execution facts only.

    This is where the run's execution state becomes a durable fact. The
    runtime never parses model-claimed evidence, never validates knowledge
    semantics, and never downgrades a run because a source field is absent.
    """
    workspace = settings.workspace_root.resolve()

    inherited = (
        list(prior_pause_receipt.artifact_facts)
        if prior_pause_receipt is not None
        else []
    )
    artifact_facts = _changed_artifact_facts(
        workspace, snapshot, inherited=inherited
    )
    tool_effect_facts, unresolved_effects = _tool_effect_facts(settings, run_id)
    knowledge_updates = KnowledgeStore(workspace).list_generated_by_run(run_id)

    if unresolved_effects and execution_state == "completed":
        # A started-but-never-settled tool call means execution did not
        # cleanly finish: represent that as failed execution, not a semantic
        # downgrade. The unresolved facts remain inspectable.
        execution_state = "failed"  # type: ignore[assignment]
        error = error or "run ended with unresolved tool call(s)"

    receipt_store = ReceiptStore(settings.state_root)
    receipt = RunReceipt(
        run_id=run_id,
        conversation_id=conversation_id,
        continued_from_run_id=prior_pause_receipt.run_id
        if prior_pause_receipt is not None
        else None,
        bindings=bindings or {},
        model=model_label,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        execution_state=execution_state,
        outcome=outcome,
        usage=usage,
        usage_complete=_usage_complete(usage),
        artifact_facts=artifact_facts,
        tool_effect_facts=tool_effect_facts,
        knowledge_updates=knowledge_updates,
        unresolved_effects=unresolved_effects,
        error=error,
        step_store=str(settings.step_store_dir)
        if settings.enable_step_persistence
        else None,
        tool_result_store=str(settings.tool_result_dir)
        if settings.enable_tool_output_limits
        else None,
        composition=composition,
    )
    receipt_store.write(receipt)
    return TerminalRun(
        presentation=presentation if presentation is not None else outcome,
        receipt=receipt,
    )


def _persist_pause_frontier(
    settings: AgentSettings,
    *,
    run_id: str,
    conversation_id: str,
    messages: list[Any],
) -> None:
    """Persist the pause frontier as a continuable harness snapshot.

    A paused run ends with unresolved tool calls (the pending approvals), so
    the harness classifies its history as ``interrupted`` and saves nothing on
    its own — after process exit ``continue_run()`` would find no snapshot to
    rebuild the history from. This saves exactly that frontier through the
    harness primitive (``FileStepStore.save_snapshot``, state ``interrupted``);
    resume reads it back with ``continue_run(..., include_interrupted=True)``.
    Best-effort: a failing snapshot save must not lose the pause receipt, so
    the pause still settles and only the durable resume frontier degrades.
    """
    try:
        from pydantic_ai_harness.step_persistence import (
            ContinuableSnapshot,
            FileStepStore,
        )

        store = FileStepStore(
            settings.step_store_dir,
            max_snapshots_per_run=settings.max_snapshots_per_run,
        )
        asyncio.run(
            store.save_snapshot(
                ContinuableSnapshot(
                    run_id=run_id,
                    step_index=0,
                    messages=list(messages),
                    conversation_id=conversation_id,
                    parent_run_id=None,
                    agent_name="zuaef",
                    state="interrupted",
                )
            )
        )
    except Exception:  # noqa: BLE001 — best-effort durable frontier
        logging.getLogger(__name__).warning(
            "pause frontier snapshot could not be persisted for run %s", run_id
        )


def _build_paused(
    requests: DeferredToolRequests,
    *,
    result: Any,
    settings: AgentSettings,
    run_id: str,
    conversation_id: str,
    model_label: str,
    started_at: datetime,
    usage: dict[str, Any],
    snapshot: dict[str, str],
    composition: CompositionSnapshot | None = None,
    bindings: dict[str, str] | None = None,
) -> PausedRun:
    workspace = settings.workspace_root.resolve()
    artifact_facts = _changed_artifact_facts(workspace, snapshot)
    tool_effect_facts, _ = _tool_effect_facts(settings, run_id)
    pause_receipt = PauseReceipt(
        run_id=run_id,
        conversation_id=conversation_id,
        bindings=bindings or {},
        model=model_label,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        pending_approvals=[_call_snapshot(call) for call in requests.approvals],
        pending_calls=[_call_snapshot(call) for call in requests.calls],
        artifact_facts=artifact_facts,
        tool_effect_facts=tool_effect_facts,
        knowledge_updates=KnowledgeStore(workspace).list_generated_by_run(run_id),
        usage=usage,
        usage_complete=_usage_complete(usage),
        step_store=str(settings.step_store_dir)
        if settings.enable_step_persistence
        else None,
        tool_result_store=str(settings.tool_result_dir)
        if settings.enable_tool_output_limits
        else None,
        composition=composition,
    )
    ReceiptStore(settings.state_root).write(pause_receipt)
    message_history = list(result.all_messages())
    if settings.enable_step_persistence:
        _persist_pause_frontier(
            settings,
            run_id=run_id,
            conversation_id=conversation_id,
            messages=message_history,
        )
    return PausedRun(
        requests=requests,
        message_history=message_history,
        conversation_id=conversation_id,
        pause_receipt=pause_receipt,
    )


def execute_run(
    agent: Any,
    deps: CoreDeps,
    *,
    prompt: str | None = None,
    settings: AgentSettings | None = None,
    run_id: str | None = None,
    conversation_id: str | None = None,
    message_history: Sequence[Any] | None = None,
    deferred_tool_results: DeferredToolResults | None = None,
    prior_pause_receipt: PauseReceipt | None = None,
    retries: int | dict[str, int] | None = None,
    composition: CompositionSnapshot | None = None,
) -> RuntimeOutcome:
    """Shared execution seam: run an already-composed agent through the common runtime.

    The runtime owns usage limits, the exception boundary, pause/continuation,
    operational receipt settlement. It never builds agents — composition
    (build_agent + deps + business toolsets) is the caller's job. Run
    acceptance happens here: any failure after this point leaves a receipt.

    ``composition`` is frozen into the receipt; a continuation must pass the
    pause receipt's own snapshot.

    ``bindings`` come from ``deps`` (host-owned, opaque to the kernel): the
    Gateway threads the session's bound identities into the run and the
    receipts preserve them across pause/resume.
    """
    settings = settings or AgentSettings.from_env()
    run_id = run_id or deps.run_id
    if run_id != deps.run_id:
        raise ValueError("run_id must match deps.run_id")
    if deps.workspace_root.resolve() != settings.workspace_root.resolve():
        raise ValueError("deps.workspace_root must match settings.workspace_root")
    if prior_pause_receipt is not None:
        if run_id == prior_pause_receipt.run_id:
            raise ValueError("a continuation requires a new run_id")
        if conversation_id is None:
            conversation_id = prior_pause_receipt.conversation_id
        elif conversation_id != prior_pause_receipt.conversation_id:
            raise ValueError(
                "continuation conversation_id must match the pause receipt"
            )
    conversation_id = conversation_id or uuid4().hex
    model_label = _model_label(settings)
    started_at = datetime.now(UTC)

    bindings = dict(deps.bindings)

    # Run acceptance: bounded pre-run artifact snapshot (ownership never uses mtime).
    snapshot = snapshot_artifacts(settings.workspace_root.resolve())
    limits = UsageLimits(
        request_limit=settings.request_limit,
        tool_calls_limit=settings.tool_calls_limit,
        total_tokens_limit=settings.total_tokens_limit,
    )

    usage_tracker = RunUsage()

    def _settle(
        execution_state: ExecutionState,
        outcome: str,
        *,
        error: str | None = None,
        presentation: str | None = None,
    ) -> TerminalRun:
        return finalize_terminal(
            settings=settings,
            run_id=run_id,
            conversation_id=conversation_id,
            model_label=model_label,
            started_at=started_at,
            usage=_usage_payload(usage_tracker),
            snapshot=snapshot,
            execution_state=execution_state,
            outcome=outcome,
            presentation=presentation,
            prior_pause_receipt=prior_pause_receipt,
            error=error,
            composition=composition,
            bindings=bindings,
        )

    try:
        result = asyncio.run(
            agent.run(
                prompt,
                deps=deps,
                message_history=list(message_history)
                if message_history is not None
                else None,
                deferred_tool_results=deferred_tool_results,
                conversation_id=conversation_id,
                usage_limits=limits,
                usage=usage_tracker,
                retries=retries,
            )
        )
    except UsageLimitExceeded as exc:
        return _settle(
            "limit_reached",
            "Run stopped at an enforced usage boundary.",
            error=str(exc),
            presentation=(
                "The run stopped at an enforced usage boundary. The technical "
                "detail is recorded in the run receipt."
            ),
        )
    except Exception as exc:  # noqa: BLE001 — receipt boundary: no unrecorded runtime failure
        return _settle(
            "failed",
            "Run failed before reaching a business terminal state.",
            error=f"{type(exc).__name__}: {exc}",
            presentation=(
                "The run failed before completing. The technical detail is "
                "recorded in the run receipt."
            ),
        )

    usage = _usage_payload(result)
    output = result.output
    if isinstance(output, DeferredToolRequests):
        return _build_paused(
            output,
            result=result,
            settings=settings,
            run_id=run_id,
            conversation_id=conversation_id,
            model_label=model_label,
            started_at=started_at,
            usage=usage,
            snapshot=snapshot,
            composition=composition,
            bindings=bindings,
        )
    # Natural terminal: the model returned plain text. The host settles the
    # receipt from operational facts (artifact byte diff, effect ledger,
    # knowledge writes) — never from model-crafted settlement fields.
    return _settle(
        "completed",
        NATURAL_COMPLETION_OUTCOME,
        presentation=str(output),
    )


def decide(
    paused: PausedRun, *, approve: bool, message: str | None = None
) -> DeferredToolResults:
    """Build the DeferredToolResults resolving a paused run's pending approvals."""
    results = DeferredToolResults()
    for call in paused.requests.approvals:
        results.approvals[call.tool_call_id] = (
            True if approve else ToolDenied(message or "denied by operator")
        )
    for call in paused.requests.calls:
        results.calls[call.tool_call_id] = ToolFailed(
            "no external executor configured in this process"
        )
    return results


def run_task(prompt: str, settings: AgentSettings | None = None) -> RuntimeOutcome:
    """Convenience wrapper: default core composition through the shared execute_run seam."""
    settings = settings or AgentSettings.from_env()
    run_id = uuid4().hex
    agent = build_agent(settings, run_id=run_id)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    return execute_run(agent, deps, prompt=prompt, settings=settings, run_id=run_id)
