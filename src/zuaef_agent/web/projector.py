"""Read-only projection of existing runtime facts into view DTOs.

Nothing in this module is durable (SPEC §5): every type here is a transient,
replaceable view DTO computed from ``pydantic_ai_harness`` step events, the
ZUAEF receipt store and persisted snapshots. Unknown stays unknown — a value
is ``None`` unless a persisted fact states it, and no elapsed time is
fabricated for rows without both timestamps.

Pairing rules (SPEC §6):

- model requests pair start/completion/failure only within one ``step_index``
  where the relation is unambiguous; otherwise the row is ``incomplete``;
- tool calls are keyed by ``tool_call_id``; a started-only call counts as
  ``unresolved`` once the run is settled (a receipt exists) and ``started``
  while the run may still be live;
- settlement priority: receipt → step events → conservative ``unknown``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic_ai_harness.step_persistence import (
    ContinuableSnapshot,
    RunRecord,
    StepEvent,
    ToolEffectRecord,
)

from ..models import AnyReceipt, PauseReceipt, RunReceipt

# Per-message content cap for inspector IO previews: bounded transport, the
# UI owns display truncation on top of this.
_MAX_PART_CHARS = 20_000


@dataclass(frozen=True)
class RunFacts:
    """Everything the readers gathered about one run — the projection input.

    ``diagnostics`` carries transient reader warnings (e.g. an ignored
    foreign-schema receipt) for display only; it is never persisted.
    """

    run_id: str
    record: RunRecord | None
    events: tuple[StepEvent, ...]
    receipt: AnyReceipt | None
    snapshot: ContinuableSnapshot | None
    tool_effects: tuple[ToolEffectRecord, ...]
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimelineRow:
    """One trajectory row (SPEC §5 example shape, UI-specific and replaceable)."""

    id: str
    kind: str  # "run" | "model_request" | "tool_call"
    step_index: int | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    status: str | None
    title: str
    detail: str | None
    usage: Mapping[str, Any] | None
    source: tuple[str, ...]
    payload: Mapping[str, Any]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _same_clock(a: datetime | None, b: datetime | None) -> bool:
    """True when both stamps are comparable (both naive or both aware).

    A naive stamp carries no offset — pairing it against an aware stamp
    would invent a timezone, so the derived duration stays unknown instead.
    """
    if a is None or b is None:
        return False
    return (a.tzinfo is None) == (b.tzinfo is None)


def _duration_ms(
    started: datetime | None, finished: datetime | None
) -> int | None:
    if not _same_clock(started, finished) or finished < started:
        return None
    return int((finished - started).total_seconds() * 1000)


def _sort_instant(stamp: datetime) -> datetime:
    """Ordering key only: aware stamps normalized to naive UTC so rows sort
    without raising. Display always uses the original ISO string; a naive
    stamp is left untouched (no timezone is invented for it)."""
    if stamp.tzinfo is None:
        return stamp
    return stamp.astimezone(UTC).replace(tzinfo=None)


def _receipt_started_at(facts: RunFacts) -> datetime | None:
    if isinstance(facts.receipt, (RunReceipt, PauseReceipt)):
        return facts.receipt.started_at
    if facts.record is not None:
        return facts.record.started_at
    stamps = [e.timestamp for e in facts.events]
    return min(stamps, key=timestamp_sort_key) if stamps else None


def _receipt_finished_at(facts: RunFacts) -> datetime | None:
    receipt = facts.receipt
    if isinstance(receipt, (RunReceipt, PauseReceipt)):
        return receipt.finished_at
    for kind in ("run_completed", "run_failed"):
        stamps = [e.timestamp for e in facts.events if e.kind == kind]
        if stamps:
            return max(stamps, key=timestamp_sort_key)
    return None


def timestamp_sort_key(value: datetime | None) -> float:
    """Ordering compatibility policy — never a displayed or stored value.

    The Harness convention is UTC-aware stamps; naive stamps only arise from
    foreign data. For chronological ORDERING a naive stamp is interpreted as
    UTC (documented legacy compatibility); display keeps the original ISO
    string and derived durations refuse mixed-clock arithmetic entirely.
    """
    if value is None:
        return float("inf")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).timestamp()
    return value.timestamp()


def derive_run_status(receipt: AnyReceipt | None, events: Sequence[StepEvent]) -> str:
    """Settlement priority — fixed and total (never raises, never guesses):

    1. valid ``PauseReceipt``            -> ``paused``
    2. valid terminal receipt            -> its ``execution_state``
    3. ``run_failed`` event              -> ``failed``
    4. ``run_completed`` event           -> ``completed``
    5. only ``run_started``              -> ``incomplete``
    6. otherwise                         -> ``unknown``

    An unparsable receipt is absent from this function's inputs, so it can
    never outrank — nor drag down — StepPersistence facts.
    """
    if isinstance(receipt, PauseReceipt):
        return "paused"
    if isinstance(receipt, RunReceipt):
        return receipt.execution_state
    kinds = {e.kind for e in events}
    if "run_failed" in kinds:
        return "failed"
    if "run_completed" in kinds:
        return "completed"
    if "run_started" in kinds:
        return "incomplete"
    return "unknown"


def _display_label(facts: RunFacts) -> str:
    """Deterministic label from explicit metadata — never model-generated."""
    receipt = facts.receipt
    if receipt is not None:
        case = (receipt.bindings or {}).get("case")
        if case:
            return str(case)
        composition = getattr(receipt, "composition", None)
        profile = getattr(composition, "profile", None)
        if profile:
            return str(profile)
    return facts.run_id[:12]


def _event_dict(event: StepEvent) -> dict[str, Any]:
    return {
        "kind": event.kind,
        "step_index": event.step_index,
        "timestamp": _iso(event.timestamp),
        "tool_call_id": event.tool_call_id,
        "tool_name": event.tool_name,
        "error": event.error,
        "metadata": dict(event.metadata),
    }


def _response_usage(message: Any) -> dict[str, int] | None:
    usage = getattr(message, "usage", None)
    if usage is None:
        return None
    extracted: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens"):
        value = getattr(usage, key, None)
        if isinstance(value, int):
            extracted[key] = value
    return extracted or None


def _part_dict(part: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "part_kind": getattr(part, "part_kind", type(part).__name__)
    }
    for attr in ("tool_name", "tool_call_id"):
        value = getattr(part, attr, None)
        if value is not None:
            result[attr] = value
    content = getattr(part, "content", None)
    if content is not None and not isinstance(content, (dict, list)):
        text = str(content)
        result["content"] = text[:_MAX_PART_CHARS]
        result["truncated"] = len(text) > _MAX_PART_CHARS
    elif content is not None:
        result["content"] = content
    args = getattr(part, "args", None)
    if isinstance(args, dict):
        result["args"] = args
    return result


def _snapshot_messages(facts: RunFacts) -> tuple[list[Any], list[Any]]:
    """Split persisted history into request/response messages, in order."""
    if facts.snapshot is None:
        return [], []
    requests: list[Any] = []
    responses: list[Any] = []
    for message in facts.snapshot.messages:
        kind = getattr(message, "kind", None)
        if kind == "response":
            responses.append(message)
        elif kind == "request":
            requests.append(message)
    return requests, responses


def _pair_requests_and_responses(
    facts: RunFacts, request_rows: list[TimelineRow]
) -> list[dict[str, Any] | None]:
    """Attach per-response usage/IO to request rows by order correlation.

    The final persisted snapshot holds the message history in order; the Nth
    response corresponds to the Nth request row. When the snapshot was pruned
    or counts disagree, correlation is not clear and nothing is attached.
    """
    _, responses = _snapshot_messages(facts)
    if len(responses) != len(request_rows):
        return [None] * len(request_rows)
    return [
        {
            "usage": _response_usage(message),
            "parts": [_part_dict(p) for p in getattr(message, "parts", [])],
        }
        for message in responses
    ]


def build_timeline(facts: RunFacts) -> list[TimelineRow]:
    rows: list[TimelineRow] = []
    status = derive_run_status(facts.receipt, facts.events)
    kinds = {e.kind for e in facts.events}
    effect_summaries = {
        effect.tool_call_id: effect.effect_summary
        for effect in facts.tool_effects
        if effect.effect_summary
    }

    # Run boundary row.
    run_started = [e for e in facts.events if e.kind == "run_started"]
    run_ended = [
        e for e in facts.events if e.kind in ("run_completed", "run_failed")
    ]
    if run_started or run_ended:
        started = min(
            (e.timestamp for e in run_started),
            key=timestamp_sort_key,
            default=None,
        )
        ended = min(
            (e.timestamp for e in run_ended),
            key=timestamp_sort_key,
            default=None,
        )
        rows.append(
            TimelineRow(
                id="run",
                kind="run",
                step_index=None,
                started_at=started,
                finished_at=ended,
                duration_ms=_duration_ms(started, ended),
                status=status,
                title="Run",
                detail=next(
                    (e.error for e in run_ended if e.error), None
                ),
                usage=None,
                source=("step_event",),
                payload={"events": [_event_dict(e) for e in facts.events if e.kind.startswith("run_")]},
            )
        )

    # Model requests: pair start/end strictly within one step_index.
    starts = sorted(
        (e for e in facts.events if e.kind == "model_request_started"),
        key=lambda e: timestamp_sort_key(e.timestamp),
    )
    ends_by_step: dict[int, list[StepEvent]] = {}
    for end in sorted(
        (
            e
            for e in facts.events
            if e.kind in ("model_request_completed", "model_request_failed")
        ),
        key=lambda e: timestamp_sort_key(e.timestamp),
    ):
        ends_by_step.setdefault(end.step_index, []).append(end)

    def _make_request_row(
        suffix: str,
        *,
        start: StepEvent | None,
        end: StepEvent | None,
        step_index: int | None,
    ) -> TimelineRow:
        failed = end is not None and end.kind == "model_request_failed"
        events = ([_event_dict(start)] if start else []) + (
            [_event_dict(end)] if end else []
        )
        return TimelineRow(
            id=f"model-request-{suffix}",
            kind="model_request",
            step_index=step_index,
            started_at=start.timestamp if start else None,
            finished_at=end.timestamp if end else None,
            duration_ms=_duration_ms(
                start.timestamp if start else None,
                end.timestamp if end else None,
            ),
            status="failed" if failed else "completed" if end else "incomplete",
            title="Model request",
            detail=end.error if end and end.error else None,
            usage=None,
            source=("step_event",),
            payload={"events": events},
        )

    request_rows: list[TimelineRow] = []
    for index, start in enumerate(starts):
        candidates = ends_by_step.get(start.step_index)
        end = candidates.pop(0) if candidates else None
        request_rows.append(
            _make_request_row(str(index), start=start, end=end, step_index=start.step_index)
        )
    leftover_ends = [end for ends in ends_by_step.values() for end in ends]
    for offset, end in enumerate(leftover_ends):
        request_rows.append(
            _make_request_row(f"end-{offset}", start=None, end=end, step_index=end.step_index)
        )

    # Per-response usage/IO from the persisted snapshot (order correlation).
    attached = _pair_requests_and_responses(facts, request_rows)
    rebuilt: list[TimelineRow] = []
    for row, extra in zip(request_rows, attached):
        if extra is None:
            rebuilt.append(row)
            continue
        payload = dict(row.payload)
        if extra["parts"]:
            payload["response_parts"] = extra["parts"]
        source = list(row.source)
        if extra["usage"] is not None or extra["parts"]:
            source.append("snapshot")
        rebuilt.append(
            TimelineRow(
                id=row.id,
                kind=row.kind,
                step_index=row.step_index,
                started_at=row.started_at,
                finished_at=row.finished_at,
                duration_ms=row.duration_ms,
                status=row.status,
                title=row.title,
                detail=row.detail,
                usage=extra["usage"],
                source=tuple(source),
                payload=payload,
            )
        )
    rows.extend(rebuilt)

    # Tool calls: lifecycle keyed by tool_call_id.
    calls: dict[str, dict[str, Any]] = {}
    for event in facts.events:
        if not event.tool_call_id:
            continue
        entry = calls.setdefault(
            event.tool_call_id,
            {"started": None, "ended": None, "failed": False, "name": event.tool_name, "events": []},
        )
        entry["events"].append(event)
        if event.kind == "tool_call_started":
            entry["started"] = (
                min((entry["started"], event.timestamp), key=timestamp_sort_key)
            )
        elif event.kind in ("tool_call_completed", "tool_call_failed"):
            entry["ended"] = (
                min((entry["ended"], event.timestamp), key=timestamp_sort_key)
            )
            entry["failed"] = entry["failed"] or event.kind == "tool_call_failed"
    for offset, (tool_call_id, entry) in enumerate(
        sorted(
            calls.items(),
            key=lambda item: timestamp_sort_key(item[1]["started"] or item[1]["ended"]),
        ),
        start=1
    ):
        # Settled means settlement evidence exists (any receipt, or a terminal
        # run event): an open call cannot still be in flight, so it is
        # "unresolved". Without settlement evidence the call may genuinely be
        # running right now — it stays "started".
        settled = (
            facts.receipt is not None
            or "run_completed" in kinds
            or "run_failed" in kinds
        )
        if entry["failed"]:
            tool_status = "failed"
        elif entry["ended"] is not None:
            tool_status = "completed"
        elif settled:
            tool_status = "unresolved"
        else:
            tool_status = "started"
        detail = effect_summaries.get(tool_call_id)
        rows.append(
            TimelineRow(
                id=f"tool-call-{offset - 1}",
                kind="tool_call",
                step_index=entry["events"][0].step_index,
                started_at=entry["started"],
                finished_at=entry["ended"],
                duration_ms=_duration_ms(entry["started"], entry["ended"]),
                status=tool_status,
                title=entry["name"] or "Tool call",
                detail=detail,
                usage=None,
                source=("step_event", "tool_effect_ledger") if detail else ("step_event",),
                payload={"events": [_event_dict(e) for e in entry["events"]]},
            )
        )

    def _sort_key(row: TimelineRow) -> float:
        return timestamp_sort_key(row.started_at or row.finished_at)

    rows.sort(key=_sort_key)
    return rows


def usage_summary(facts: RunFacts, timeline: list[TimelineRow]) -> dict[str, Any] | None:
    """Per-response usage when every request has it, else aggregate, else unknown.

    Aggregate receipt usage is never divided across requests (SPEC §6).
    """
    per_response = [row.usage for row in timeline if row.kind == "model_request"]
    if per_response and all(u is not None for u in per_response):
        return {
            "input_tokens": sum(u["input_tokens"] for u in per_response if u),
            "output_tokens": sum(u["output_tokens"] for u in per_response if u),
            "requests": len(per_response),
            "source": "per_response",
        }
    receipt = facts.receipt
    if isinstance(receipt, (RunReceipt, PauseReceipt)) and receipt.usage:
        usage = dict(receipt.usage)
        usage["requests"] = len(per_response)
        usage["source"] = "receipt_aggregate"
        return usage
    return None


def run_view(facts: RunFacts) -> dict[str, Any]:
    receipt = facts.receipt
    composition = getattr(receipt, "composition", None)
    request_count = sum(1 for e in facts.events if e.kind == "model_request_started")
    tool_call_count = len({e.tool_call_id for e in facts.events if e.tool_call_id})
    return {
        "run_id": facts.run_id,
        "conversation_id": getattr(facts.record, "conversation_id", None)
        or (receipt.conversation_id if receipt else None),
        "parent_run_id": getattr(facts.record, "parent_run_id", None),
        "continued_from_run_id": getattr(receipt, "continued_from_run_id", None),
        "status": derive_run_status(facts.receipt, facts.events),
        "model": getattr(receipt, "model", None),
        "profile": getattr(composition, "profile", None),
        "agent_name": getattr(facts.record, "agent_name", None),
        "display_label": _display_label(facts),
        "started_at": _iso(_receipt_started_at(facts)),
        "finished_at": _iso(_receipt_finished_at(facts)),
        "duration_ms": _duration_ms(_receipt_started_at(facts), _receipt_finished_at(facts)),
        "request_count": request_count,
        "tool_call_count": tool_call_count,
    }


def artifacts_view(facts: RunFacts) -> list[dict[str, Any]]:
    receipt = facts.receipt
    if receipt is None:
        return []
    return [
        {
            "path": fact.path,
            "size": fact.size,
            "sha256": fact.sha256,
            "change": fact.change,
            # A hash proves byte identity, not quality (SPEC §6).
            "label": "Artifact changed",
        }
        for fact in receipt.artifact_facts
    ]


def pause_view(facts: RunFacts) -> dict[str, Any] | None:
    receipt = facts.receipt
    if not isinstance(receipt, PauseReceipt):
        return None
    return {
        "pending_approvals": list(receipt.pending_approvals),
        "pending_calls": list(receipt.pending_calls),
    }


def unresolved_effects_view(facts: RunFacts) -> list[dict[str, Any]]:
    receipt = facts.receipt
    if receipt is None:
        return []
    return [fact.model_dump() for fact in getattr(receipt, "unresolved_effects", [])]


def composition_view(facts: RunFacts) -> dict[str, Any] | None:
    composition = getattr(facts.receipt, "composition", None)
    return composition.model_dump() if composition is not None else None


def project_run(facts: RunFacts, *, action_in_flight: bool = False) -> dict[str, Any]:
    """One complete UI projection (API-CONTRACT §4 envelope)."""
    timeline = build_timeline(facts)
    return {
        "run": run_view(facts),
        "usage": usage_summary(facts, timeline),
        "timeline": [
            {
                "id": row.id,
                "kind": row.kind,
                "step_index": row.step_index,
                "started_at": _iso(row.started_at),
                "finished_at": _iso(row.finished_at),
                "duration_ms": row.duration_ms,
                "status": row.status,
                "title": row.title,
                "detail": row.detail,
                "usage": dict(row.usage) if row.usage else None,
                "source": list(row.source),
                "payload": dict(row.payload),
            }
            for row in timeline
        ],
        "artifacts": artifacts_view(facts),
        "pause": pause_view(facts),
        "unresolved_effects": unresolved_effects_view(facts),
        "composition": composition_view(facts),
        # Transient reader diagnostics (e.g. an ignored foreign-schema
        # receipt) — display-only, never persisted, never a domain model.
        "diagnostics": list(facts.diagnostics),
        "action_in_flight": action_in_flight,
    }
