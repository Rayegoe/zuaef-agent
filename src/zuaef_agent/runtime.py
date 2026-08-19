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
from .knowledge_store import KnowledgeStore
from .models import (
    ArtifactVerification,
    CompositionSnapshot,
    CoreDeps,
    PauseReceipt,
    RunReceipt,
    RunSummary,
    ToolEffectVerification,
)
from .receipt_store import ReceiptStore
from .verification import (
    VerificationError,
    latest_tool_effects,
    parse_evidence_ref,
    read_tool_effects,
    snapshot_artifacts,
    verify_artifact,
    verify_knowledge,
    verify_tool_effect,
)


def _verify_inherited_artifact(
    recorded: ArtifactVerification,
    *,
    workspace_root: Any,
) -> ArtifactVerification:
    """Re-read a pause-settled artifact and require its bytes to remain unchanged."""
    current = verify_artifact(recorded.path, workspace_root=workspace_root, snapshot={})
    if current.size != recorded.size or current.sha256 != recorded.sha256:
        raise VerificationError(
            f"inherited artifact changed after pause: {recorded.path!r}"
        )
    return current


def _usage_payload(result: object) -> dict[str, Any]:
    """Best-effort compatibility adapter across PydanticAI result usage shapes."""
    value = result if isinstance(result, RunUsage) else getattr(result, "usage", None)
    if callable(value):
        value = value()
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if is_dataclass(value):
        return asdict(value)
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


def _assert_pending_case_isolation(
    requests: DeferredToolRequests,
    deps: CoreDeps,
) -> None:
    """Business authorization boundary at the pause frontier (SPEC v1.0 §5.6).

    Approval-gated tools (e.g. ``send_to_customer``) never execute their
    function body — the framework pauses the run BEFORE the tool's own guard
    could run. The host therefore re-checks every pending approval against the
    run's bound Case here: a pending call naming a different ``case_id`` fails
    the run loudly instead of pausing, so a bound run can never reach an
    operator queue for the wrong Case. Unbound runs are untouched.
    """
    if deps.case_id is None:
        return
    for call in requests.approvals:
        snapshot = _call_snapshot(call)
        args = snapshot["args"]
        requested = args.get("case_id") if isinstance(args, dict) else None
        if requested is not None and requested != deps.case_id:
            raise ValueError(
                f"pending approval {snapshot['tool_name']!r} targets case "
                f"{requested!r} but this run is bound to case {deps.case_id!r} "
                "— Case operations are isolated to the bound Case"
            )


@dataclass(kw_only=True)
class TerminalRun:
    """A run that reached a business terminal state with a host-verified receipt."""

    summary: RunSummary
    receipt: RunReceipt


@dataclass(kw_only=True)
class PausedRun:
    """A run paused awaiting approval; continue it via message history + DeferredToolResults."""

    requests: DeferredToolRequests
    message_history: list[Any]
    conversation_id: str
    pause_receipt: PauseReceipt


RuntimeOutcome = TerminalRun | PausedRun


def finalize_terminal(
    summary: RunSummary,
    *,
    settings: AgentSettings,
    run_id: str,
    conversation_id: str,
    model_label: str,
    started_at: datetime,
    usage: dict[str, Any],
    snapshot: dict[str, str],
    prior_pause_receipt: PauseReceipt | None = None,
    error: str | None = None,
    composition: CompositionSnapshot | None = None,
    case_id: str | None = None,
) -> TerminalRun:
    """Host verification boundary: verify model claims, degrade, and settle the receipt.

    Importable and unit-testable on its own; this is where "completed" stops
    being the model's opinion and becomes a verified fact.
    """
    degraded: list[str] = []
    verified_artifacts: list[ArtifactVerification] = []
    verified_knowledge: list[str] = []
    verified_tool_effects: list[ToolEffectVerification] = []
    verified_evidence_refs: list[str] = []

    workspace = settings.workspace_root.resolve()
    knowledge_store = KnowledgeStore(workspace)
    inherited_artifacts: dict[str, ArtifactVerification] = {}
    inherited_knowledge: set[str] = set()
    if prior_pause_receipt is not None:
        for recorded in prior_pause_receipt.verified_artifacts:
            try:
                inherited_artifacts[recorded.path] = _verify_inherited_artifact(
                    recorded,
                    workspace_root=workspace,
                )
                verified_artifacts.append(inherited_artifacts[recorded.path])
            except VerificationError as exc:
                degraded.append(str(exc))
        for knowledge_id in prior_pause_receipt.verified_knowledge:
            try:
                verify_knowledge(
                    knowledge_id,
                    store=knowledge_store,
                    run_id=prior_pause_receipt.run_id,
                )
                inherited_knowledge.add(knowledge_id)
                verified_knowledge.append(knowledge_id)
            except VerificationError as exc:
                degraded.append(str(exc))
    raw_effect_records = (
        latest_tool_effects(read_tool_effects(settings.step_store_dir, run_id))
        if settings.enable_step_persistence
        else []
    )
    effect_records: list[dict[str, Any]] = []
    for record in raw_effect_records:
        call_id = record.get("tool_call_id")
        tool_name = record.get("tool_name")
        status = record.get("status")
        if (
            not isinstance(call_id, str)
            or not call_id
            or not isinstance(tool_name, str)
            or not tool_name
        ):
            degraded.append("malformed tool-effect ledger record")
        elif status not in {"started", "completed", "failed"}:
            degraded.append(f"invalid tool-effect status for {call_id!r}: {status!r}")
        elif record.get("run_id") != run_id:
            degraded.append(f"tool-effect not owned by run {run_id}: {call_id!r}")
        else:
            effect_records.append(record)

    # Host-discover artifacts changed before any terminal path, including a
    # provider/usage failure whose model summary cannot restate those files.
    for path, digest in snapshot_artifacts(workspace).items():
        if snapshot.get(path) == digest:
            continue
        try:
            verified = verify_artifact(
                path, workspace_root=workspace, snapshot=snapshot
            )
            if all(existing.path != verified.path for existing in verified_artifacts):
                verified_artifacts.append(verified)
        except VerificationError as exc:
            degraded.append(str(exc))

    for path_str in summary.artifacts:
        try:
            verified = inherited_artifacts.get(path_str) or verify_artifact(
                path_str,
                workspace_root=workspace,
                snapshot=snapshot,
            )
            if all(existing.path != verified.path for existing in verified_artifacts):
                verified_artifacts.append(verified)
        except VerificationError as exc:
            degraded.append(str(exc))

    for ref in summary.evidence:
        try:
            kind, value = parse_evidence_ref(ref)
            if kind == "artifact":
                verified = inherited_artifacts.get(value) or verify_artifact(
                    value,
                    workspace_root=workspace,
                    snapshot=snapshot,
                )
                if all(
                    existing.path != verified.path for existing in verified_artifacts
                ):
                    verified_artifacts.append(verified)
            elif kind == "knowledge":
                knowledge_id = value.removesuffix(".md")
                if knowledge_id not in inherited_knowledge:
                    verify_knowledge(value, store=knowledge_store, run_id=run_id)
                if knowledge_id not in verified_knowledge:
                    verified_knowledge.append(knowledge_id)
                verified_evidence_refs.append(f"knowledge:{knowledge_id}")
            else:
                record = verify_tool_effect(
                    value,
                    step_store_dir=settings.step_store_dir,
                    run_id=run_id,
                    records=effect_records,
                )
                verification = ToolEffectVerification(
                    tool_call_id=record["tool_call_id"],
                    tool_name=record["tool_name"],
                    status=record["status"],
                )
                verified_tool_effects.append(verification)
                verified_evidence_refs.append(f"tool-effect:{value}")
        except (VerificationError, ValueError) as exc:
            degraded.append(str(exc))

    # The host owns the effect ledger; do not require the model to copy opaque
    # tool_call_ids into its final prose before a completed effect can settle.
    for record in effect_records:
        if record.get("status") != "completed":
            continue
        if any(
            existing.tool_call_id == record["tool_call_id"]
            for existing in verified_tool_effects
        ):
            continue
        verified_tool_effects.append(
            ToolEffectVerification(
                tool_call_id=record["tool_call_id"],
                tool_name=record["tool_name"],
                status=record["status"],
            )
        )
        verified_evidence_refs.append(f"tool-effect:{record['tool_call_id']}")

    verified_evidence_refs = [
        f"artifact:{v.path}" for v in verified_artifacts
    ] + verified_evidence_refs

    # Host-discovered knowledge written by this run, even when the model forgot to claim it.
    knowledge_updates = knowledge_store.list_generated_by_run(run_id)
    for path in knowledge_updates:
        knowledge_id = path.removesuffix(".md").removeprefix("knowledge/")
        try:
            verify_knowledge(knowledge_id, store=knowledge_store, run_id=run_id)
            if knowledge_id not in verified_knowledge:
                verified_knowledge.append(knowledge_id)
                verified_evidence_refs.append(f"knowledge:{knowledge_id}")
        except VerificationError as exc:
            degraded.append(str(exc))

    unresolved = [
        ToolEffectVerification(
            tool_call_id=r["tool_call_id"], tool_name=r["tool_name"], status=r["status"]
        )
        for r in effect_records
        if r.get("status") == "started"
    ]

    status = summary.status
    if unresolved:
        status = "blocked"
    elif status == "completed" and degraded:
        status = "partial"

    unknowns = list(summary.unknowns)
    if degraded:
        unknowns = unknowns + degraded

    receipt_store = ReceiptStore(settings.state_root)
    receipt_path = receipt_store.display_path_for(run_id)
    final_summary = summary.model_copy(
        update={
            "status": status,
            "artifacts": [v.path for v in verified_artifacts],
            "evidence": verified_evidence_refs,
            "unknowns": unknowns,
            "run_id": run_id,
            "receipt": receipt_path,
        }
    )
    receipt = RunReceipt(
        run_id=run_id,
        conversation_id=conversation_id,
        continued_from_run_id=prior_pause_receipt.run_id
        if prior_pause_receipt is not None
        else None,
        case_id=case_id,
        model=model_label,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        status=final_summary.status,
        summary=final_summary,
        usage=usage,
        usage_complete=_usage_complete(usage),
        verified_artifacts=verified_artifacts,
        verified_knowledge=verified_knowledge,
        verified_tool_effects=verified_tool_effects,
        knowledge_updates=knowledge_updates,
        unresolved_effects=unresolved,
        degraded=degraded,
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
    return TerminalRun(summary=final_summary, receipt=receipt)


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
    case_id: str | None = None,
) -> PausedRun:
    effect_records = (
        latest_tool_effects(read_tool_effects(settings.step_store_dir, run_id))
        if settings.enable_step_persistence
        else []
    )
    settled = [
        f"tool-effect:{record['tool_call_id']}"
        for record in effect_records
        if record.get("status") in ("completed", "failed")
    ]
    workspace = settings.workspace_root.resolve()
    current_artifacts = snapshot_artifacts(workspace)
    verified_artifacts = [
        verify_artifact(path, workspace_root=workspace, snapshot=snapshot)
        for path, digest in current_artifacts.items()
        if snapshot.get(path) != digest
    ]
    knowledge_store = KnowledgeStore(workspace)
    verified_knowledge: list[str] = []
    for path in knowledge_store.list_generated_by_run(run_id):
        knowledge_id = path.removesuffix(".md").removeprefix("knowledge/")
        verify_knowledge(knowledge_id, store=knowledge_store, run_id=run_id)
        verified_knowledge.append(knowledge_id)
    settled += [f"artifact:{item.path}" for item in verified_artifacts]
    settled += [f"knowledge:{knowledge_id}" for knowledge_id in verified_knowledge]
    pause_receipt = PauseReceipt(
        run_id=run_id,
        conversation_id=conversation_id,
        case_id=case_id,
        model=model_label,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        pending_approvals=[_call_snapshot(call) for call in requests.approvals],
        pending_calls=[_call_snapshot(call) for call in requests.calls],
        settled_evidence=settled,
        verified_artifacts=verified_artifacts,
        verified_knowledge=verified_knowledge,
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
    host outcome verification and receipt settlement. It never builds agents —
    composition (build_agent + deps + business toolsets) is the caller's job.
    Run acceptance happens here: any failure after this point leaves a receipt.

    ``composition`` is frozen into the receipt; a continuation must pass the
    pause receipt's own snapshot.

    ``case_id`` comes from ``deps`` (server-owned): the Gateway threads the
    session's bound Case into the run and the receipts record it, so Case
    identity survives pause/resume and is part of the durable evidence.

    ``retries`` is passed through to ``agent.run`` as the tool-retry budget
    (a bare int, or ``{"tools": N}`` / ``{"output": N}``). It only raises the
    ceiling for how many times the model may retry a failing or withdrawn
    tool call before the run is blocked — it never re-offers withdrawn tools.
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

    # Run acceptance: bounded pre-run artifact snapshot (ownership never uses mtime).
    snapshot = snapshot_artifacts(settings.workspace_root.resolve())
    limits = UsageLimits(
        request_limit=settings.request_limit,
        tool_calls_limit=settings.tool_calls_limit,
        total_tokens_limit=settings.total_tokens_limit,
    )

    usage_tracker = RunUsage()

    def _partial_or_blocked(summary: RunSummary, error: str | None) -> TerminalRun:
        return finalize_terminal(
            summary,
            settings=settings,
            run_id=run_id,
            conversation_id=conversation_id,
            model_label=model_label,
            started_at=started_at,
            usage=_usage_payload(usage_tracker),
            snapshot=snapshot,
            prior_pause_receipt=prior_pause_receipt,
            error=error,
            composition=composition,
            case_id=deps.case_id,
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
        return _partial_or_blocked(
            RunSummary(
                status="partial",
                outcome="Run stopped at an enforced usage boundary.",
                unknowns=[str(exc)],
                next_action="Review produced artifacts/evidence and resume with a narrower task if needed.",
            ),
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — receipt boundary: no unrecorded runtime failure
        return _partial_or_blocked(
            RunSummary(
                status="blocked",
                outcome="Run failed before reaching a business terminal state.",
                unknowns=[f"{type(exc).__name__}: {exc}"],
                next_action="Inspect the receipt error field and the step store, then retry.",
            ),
            error=f"{type(exc).__name__}: {exc}",
        )

    usage = _usage_payload(result)
    output = result.output
    if isinstance(output, DeferredToolRequests):
        # Host authorization boundary: a bound run must not pause for an
        # approval that targets a different Case — that is a blocked run, not
        # an operator queue entry (SPEC v1.0 §5.6).
        try:
            _assert_pending_case_isolation(output, deps)
        except ValueError as exc:
            return _partial_or_blocked(
                RunSummary(
                    status="blocked",
                    outcome=str(exc),
                    unknowns=[str(exc)],
                ),
                error=str(exc),
            )
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
            case_id=deps.case_id,
        )
    summary = (
        output
        if isinstance(output, RunSummary)
        else RunSummary(status="partial", outcome=str(output))
    )
    return finalize_terminal(
        summary,
        settings=settings,
        run_id=run_id,
        conversation_id=conversation_id,
        model_label=model_label,
        started_at=started_at,
        usage=usage,
        snapshot=snapshot,
        prior_pause_receipt=prior_pause_receipt,
        composition=composition,
        case_id=deps.case_id,
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
