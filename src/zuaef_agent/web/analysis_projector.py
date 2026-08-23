"""T014 — bounded agent-readable projection of one run (RUN_ANALYSIS_SPEC §3).

Derived view over the SAME public reader inputs the Console projector uses
(``RunFacts``). Shallow, replaceable, never durable execution truth: every
number here is computed from persisted facts, ``None`` means unknown, and
message excerpts are explicitly observable parts only — never reconstructed
chain-of-thought. Actual input: RunFacts (readers.load_run_facts).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from pydantic_ai_harness.step_persistence import ContinuableSnapshot

from ..models import PauseReceipt, RunReceipt
from .projector import RunFacts, derive_run_status, project_run

# Bounded excerpts (RUN_ANALYSIS_SPEC §3.2): caps per part and total.
_MAX_PART_CHARS = 2_000
_MAX_TOTAL_EXCERPT_CHARS = 12_000
_MAX_TOOL_SEQUENCE = 120
_MAX_REQUESTS = 60
_MAX_TOOLS = 40
_MAX_ARTIFACTS = 40
_MAX_DIAGNOSTICS = 20


# ── deterministic fact extraction ───────────────────────────────────────────


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _known_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _run_status(facts: RunFacts) -> str:
    return derive_run_status(facts.receipt, facts.events)


def _request_metrics(facts: RunFacts, projection: Mapping[str, Any]) -> dict[str, Any]:
    """Per-request facts from the projector's timeline rows.

    Rows carry duration/usage only when the persisted events prove them;
    unknown stays unknown (never distributed into 0).
    """
    timeline = projection.get("timeline") or []
    rows: list[dict[str, Any]] = []
    for row in timeline:
        if row.get("kind") != "model_request":
            continue
        usage = row.get("usage") or {}
        rows.append(
            {
                "request": row.get("title") or f"request-{row.get('step_index')}",
                "step": row.get("step_index"),
                "status": row.get("status"),
                "latency_ms": row.get("duration_ms"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
            }
        )
        if len(rows) >= _MAX_REQUESTS:
            break
    return {"requests": rows, "omitted": 0}


def _tool_sequence(facts: RunFacts, projection: Mapping[str, Any]) -> dict[str, Any]:
    """Ordered tool lifecycle from the projector's timeline rows (already
    paired/statused; the raw event ledger holds started+completed pairs)."""
    timeline = projection.get("timeline") or []
    sequence: list[dict[str, Any]] = []
    for row in timeline:
        if row.get("kind") != "tool_call":
            continue
        sequence.append(
            {
                "tool": row.get("title"),
                "step": row.get("step_index"),
                "status": row.get("status"),
                "latency_ms": row.get("duration_ms"),
            }
        )
        if len(sequence) >= _MAX_TOOL_SEQUENCE:
            break
    counts: dict[str, int] = {}
    for entry in sequence:
        counts[entry["tool"]] = counts.get(entry["tool"], 0) + 1
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:_MAX_TOOLS]
    consecutive: list[dict[str, int]] = []
    if sequence:
        current = sequence[0]["tool"]
        run = 1
        for entry in sequence[1:]:
            if entry["tool"] == current:
                run += 1
            else:
                consecutive.append({"tool": current, "consecutive": run})
                current = entry["tool"]
                run = 1
        consecutive.append({"tool": current, "consecutive": run})
    return {
        "sequence": sequence,
        "counts": [{"tool": name, "calls": count} for name, count in top],
        "consecutive_runs": [
            entry for entry in consecutive if entry["consecutive"] >= 2
        ],
    }


def _artifacts_facts(facts: RunFacts) -> list[dict[str, Any]]:
    receipt = facts.receipt
    if not isinstance(receipt, (RunReceipt, PauseReceipt)):
        return []
    return [
        {
            "path": fact.path,
            "size": fact.size,
            "change": fact.change,
        }
        for fact in receipt.artifact_facts[:_MAX_ARTIFACTS]
    ]


def _observable_excerpts(facts: RunFacts) -> dict[str, Any]:
    """Bounded excerpts of persisted observable message parts.

    Only parts the harness already persisted in the latest snapshot are
    exposed (user prompt text, text responses, tool-call arguments and
    tool-return content). This is a transcript excerpt, never a claim about
    hidden reasoning.
    """
    snapshot: ContinuableSnapshot | None = facts.snapshot
    parts: list[dict[str, Any]] = []
    total = 0
    if snapshot is not None:
        for message in snapshot.messages:
            for part in getattr(message, "parts", []):
                kind = getattr(part, "part_kind", None)
                text = _part_text(part)
                if text is None or not text.strip():
                    continue
                snippet = text.strip()[:_MAX_PART_CHARS]
                parts.append({"kind": kind, "text": snippet})
                total += len(snippet)
                if total >= _MAX_TOTAL_EXCERPT_CHARS:
                    parts.append(
                        {"kind": "truncation", "text": "(excerpt budget reached)"}
                    )
                    break
            if total >= _MAX_TOTAL_EXCERPT_CHARS:
                break
    # The model-visible tool args/results are the crucial decision evidence
    # for research runs; the persisted args/returns may live in tool-call
    # parts of the snapshot — mirrored from the projector's own extraction.
    return {"parts": parts[:40], "total_chars": total}


def _part_text(part: Any) -> str | None:
    kind = getattr(part, "part_kind", None)
    if kind == "user-prompt":
        content = getattr(part, "content", None)
        if isinstance(content, str):
            return content
    if kind == "text":
        return getattr(part, "content", None)
    if kind == "tool-call":
        args = getattr(part, "args", None)
        if args is not None:
            if not isinstance(args, str):
                args = json.dumps(args, ensure_ascii=False)
            return f"{getattr(part, 'tool_name', '')}: {args}"
    if kind == "tool-return":
        content = getattr(part, "content", None)
        if content is not None:
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            return f"result: {content}"
    return None


def render_projection_markdown(facts: RunFacts) -> str:
    """Canonical human/agent reading surface (RUN_ANALYSIS_SPEC §3.4)."""
    projection = project_run(facts)
    status = _run_status(facts)
    receipt = facts.receipt
    outgoing: list[str] = [
        f"# Run {facts.run_id}",
        "",
        "## Outcome / status facts",
        f"- status: {status}",
        f"- started_at: {_iso(getattr(facts.record, 'started_at', None) or (receipt.started_at if receipt else None))}",
        f"- finished_at: {_iso(receipt.finished_at if receipt else None)}",
        f"- model: {(receipt.model if receipt else None) or 'unknown'}",
        f"- execution_state: {(receipt.execution_state if isinstance(receipt, RunReceipt) else 'paused' if isinstance(receipt, PauseReceipt) else 'unknown')}",
        f"- error: {(receipt.error if isinstance(receipt, RunReceipt) else None) or 'unknown'}",
        "",
        "## Requests",
    ]
    metrics = _request_metrics(facts, projection)
    if not metrics["requests"]:
        outgoing.append("- none persisted")
    for row in metrics["requests"]:
        outgoing.append(
            f"- {row.get('request') or '?'} | step={row.get('step')} | "
            f"status={row.get('status')} | latency_ms={row.get('latency_ms')} | "
            f"in={row.get('input_tokens')} out={row.get('output_tokens')}"
        )
    if metrics["omitted"]:
        outgoing.append(f"- ({metrics['omitted']} older requests omitted)")
    outgoing += ["", "## Context / usage"]
    usage = projection.get("usage")
    if usage:
        for key, value in usage.items():
            outgoing.append(f"- {key}: {value}")
    else:
        outgoing.append("- unknown")
    outgoing += ["", "## Tool sequence"]
    tool_facts = _tool_sequence(facts, projection)
    for entry in tool_facts["sequence"]:
        outgoing.append(f"- {entry['tool']} [step {entry['step']}] {entry['status']}")
    outgoing += ["", "## Tool counts"]
    for entry in tool_facts["counts"]:
        outgoing.append(f"- {entry['tool']}: {entry['calls']}")
    outgoing += ["", "## Artifacts"]
    for artifact in _artifacts_facts(facts):
        outgoing.append(
            f"- {artifact['path']} ({artifact['size']} bytes, {artifact['change']})"
        )
    outgoing += ["", "## Composition"]
    composition = projection.get("composition") or {}
    if composition:
        outgoing.append(f"- profile: {composition.get('profile') or 'none'}")
        outgoing.append(
            "- plugins: "
            + ", ".join(
                plugin.get("id", "?") for plugin in (composition.get("plugins") or [])
            )
        )
    outgoing += ["", "## Observable message excerpts"]
    excerpts = _observable_excerpts(facts)
    if not excerpts["parts"]:
        outgoing.append("- none persisted in the latest snapshot")
    for part in excerpts["parts"]:
        outgoing.append(f"- [{part['kind']}] {part['text'][:180]}")
    outgoing += ["", "## Diagnostics"]
    if facts.diagnostics:
        for diagnostic in facts.diagnostics[:_MAX_DIAGNOSTICS]:
            outgoing.append(f"- {diagnostic}")
    else:
        outgoing.append("- none")
    return "\n".join(outgoing) + "\n"


def render_projection_json(facts: RunFacts) -> dict[str, Any]:
    """Shallow transport representation of the derived view (§3.3)."""
    projection = project_run(facts)
    return {
        "schema": "run-analysis-projection-v1",
        "run_id": facts.run_id,
        "status": _run_status(facts),
        "request_metrics": _request_metrics(facts, projection),
        "tool_sequence": _tool_sequence(facts, projection),
        "usage": projection.get("usage"),
        "artifacts": _artifacts_facts(facts),
        "composition": projection.get("composition"),
        "diagnostics": list(facts.diagnostics[:_MAX_DIAGNOSTICS]),
        "observable_messages": _observable_excerpts(facts),
    }


def render_projection_json_text(facts: RunFacts) -> str:
    return json.dumps(render_projection_json(facts), ensure_ascii=False, indent=2)


__all__ = [
    "render_projection_json",
    "render_projection_json_text",
    "render_projection_markdown",
]
