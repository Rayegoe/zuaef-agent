"""Deterministic gateway renderer — SPEC v0.3 §40–§44.

Pure functions, no model involvement, no receipt JSON dumps: terminal/pause/
status/error/profile/artifact messages are composed from host-verified facts
only. Argument previews redact secret-named keys and are length-bounded;
long messages chunk below the Telegram hard limit.
"""

from __future__ import annotations

from collections.abc import Sequence

from zuaef_agent.runtime import PausedRun, TerminalRun

CHUNK_MAX = 3800
PREVIEW_MAX = 1200
REDACTED = "***REDACTED***"

_REDACT_KEYS = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cookie",
    "credential",
)


def preview_arguments(args: dict) -> str:
    """Bounded, redacted preview of one tool call's arguments (SPEC §43)."""
    lines: list[str] = []
    for key, value in (args or {}).items():
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in _REDACT_KEYS):
            lines.append(f"{key}: {REDACTED}")
        else:
            lines.append(f"{key}: {value}")
    text = "\n".join(lines)
    if len(text) > PREVIEW_MAX:
        text = text[:PREVIEW_MAX] + "\n…"
    return text


def _short(run_id: str) -> str:
    return run_id[:8] + "…"


def render_terminal(outcome: TerminalRun) -> str:
    """Terminal card (SPEC §41). The presentation IS the reply (outcome-first);
    audit counts stay in /status and the receipt. When the presentation is
    empty (e.g. a legacy settlement-only terminal), the classic summary card."""
    receipt = outcome.receipt
    emoji = {
        "completed": "✅ Completed",
        "partial": "⚠️ Partial",
        "blocked": "⛔ Blocked",
    }[receipt.status]
    presentation = outcome.presentation.strip()
    if presentation:
        return "\n".join(
            [
                presentation,
                "",
                "—",
                emoji,
                f"Run: {_short(receipt.run_id)}",
            ]
        )
    return "\n".join(
        [
            emoji,
            "",
            receipt.summary.outcome,
            "",
            f"Verified artifacts: {len(receipt.verified_artifacts)}",
            f"Verified effects: {len(receipt.verified_tool_effects)}",
            "",
            f"Run: {receipt.run_id}",
        ]
    )


def render_pause(paused: PausedRun, *, content: str | None = None) -> str:
    """Approval card (SPEC §42, §26): batch-level, redacted argument preview.
    ``content`` is the host-read outbound draft text for customer-visible
    sends — the operator never approves unseen content."""
    approvals = paused.pause_receipt.pending_approvals
    lines = ["⚠️ Approval required"]
    if len(approvals) > 1:
        lines.append("")
        lines.append(f"{len(approvals)} actions require approval")
    for index, entry in enumerate(approvals, 1):
        tool_name = entry.get("tool_name") or "unknown-tool"
        args = entry.get("args") or {}
        if len(approvals) > 1:
            lines.extend(["", f"{index}. {tool_name}"])
        else:
            lines.extend(["", "Action:", tool_name])
        lines.extend(["", "Arguments:", preview_arguments(args)])
    if content:
        lines.extend(["", "Content to send:", content])
    lines.extend(["", "Run:", _short(paused.pause_receipt.run_id)])
    if len(approvals) > 1:
        lines.extend(["", "[Approve all]", "[Deny all]"])
    else:
        lines.extend(["", "[Approve]", "[Deny]"])
    return "\n".join(lines)


def render_status(
    *,
    profile: str | None,
    conversation_id: str,
    state: str,
    case_id: str | None = None,
    run_id: str | None = None,
    pending_approval_count: int = 0,
    pending_tools: list[str] | None = None,
) -> str:
    """Host-grounded /status (SPEC §35): the LLM never composes this."""
    lines = [
        "ZUAEF",
        "",
        f"Profile: {profile or '(none)'}",
        f"Case: {case_id or '(unbound)'}",
        f"Conversation: {_short(conversation_id)}",
        "",
        f"State: {state}",
    ]
    if run_id:
        lines.append(f"Run: {_short(run_id)}")
    if state == "PAUSED":
        lines.append(f"Pending approvals: {pending_approval_count}")
        for tool in pending_tools or []:
            lines.extend(["", "Tool:", tool])
    return "\n".join(lines)


def render_error(message: str) -> str:
    return f"⚠️ {message}"


def render_profile(*, current: str | None, available: list[str]) -> str:
    lines = [f"Current profile: {current or '(none)'}"]
    if available:
        lines.append("")
        lines.append("Available profiles:")
        lines.extend(f"- {name}" for name in available)
    return "\n".join(lines)


def render_new_conversation(profile: str | None) -> str:
    return f"New ZUAEF conversation started.\nProfile: {profile or '(none)'}"


def render_case_card(
    *,
    case_id: str | None,
    profile: str | None,
    conversation_id: str,
    state: str = "READY",
) -> str:
    """Supervisor /case view and post-bind confirmation card. Deterministic
    routing facts only — never model output."""
    return "\n".join(
        [
            "Case binding",
            "",
            f"Case: {case_id or '(unbound)'}",
            f"Profile: {profile or '(none)'}",
            f"Conversation: {_short(conversation_id)}",
            "",
            f"State: {state}",
        ]
    )


def render_cases(entries: Sequence[tuple[str, str]], bound_case: str | None) -> str:
    """/cases listing: one line per case directory, most recent first. Each
    entry is ``(case_id, updated)`` from filesystem metadata only."""
    lines = ["Cases (most recent first)"]
    if not entries:
        lines.extend(["", "No cases found under the workspace cases root."])
    for case_id, updated in entries:
        marker = " (bound)" if case_id == bound_case else ""
        lines.append(f"- {case_id}{marker} · {updated}")
    return "\n".join(lines)


def chunk_text(text: str, max_chars: int = CHUNK_MAX) -> list[str]:
    """Split one message into Telegram-safe chunks (SPEC §44)."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return chunks
