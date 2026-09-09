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


def render_run_natural_ack(*, profile: str | None, is_continuation: bool) -> str:
    """Short natural acknowledgment at run acceptance, composed from host
    state (continuation or fresh, profile) — never a run id, never a
    mechanical status card."""
    scope = f"（{profile}）" if profile else ""
    if is_continuation:
        return f"收到，接着上一轮继续处理{scope}，结果出来直接回你。"
    return f"收到，开始处理{scope}，结果出来直接回你。"


def render_run_progress(
    *,
    requests: int | None = None,
    tool_name: str | None = None,
    elapsed_seconds: int | None = None,
) -> str:
    """One bounded mid-run progress line, composed from persisted
    operational facts (model requests settled, tool currently running,
    elapsed seconds). Facts that do not exist stay out of the sentence —
    the host never invents a percentage or a stage name."""
    facts: list[str] = []
    if requests:
        facts.append(f"已完成 {requests} 轮模型调用")
    if tool_name:
        facts.append(f"正在调用 {tool_name}")
    if elapsed_seconds is not None:
        facts.append(f"已 {elapsed_seconds} 秒")
    if not facts:
        return "还在处理，结果出来直接回你。"
    return "还在处理：" + "，".join(facts) + "，出结果直接回你。"


def render_terminal(outcome: TerminalRun, *, reply_artifact: str | None = None) -> str:
    """Terminal card (SPEC §41). The presentation IS the reply (outcome-first);
    audit counts stay in /status and the receipt. Surface policy: a completed
    run's reply is pure business output. A FAILED/LIMIT_REACHED run never
    shows tokens, tool counts, usage limits, unresolved effects or run ids
    here (research service v0.2, T014 / runtime spec §11): the chat surface
    gets a bounded business-first notice, the operational truth stays in
    /inspect, /status and Console.

    ``reply_artifact`` is the host-read, domain-marked deliverable text
    (Terminal Delivery Guard, incident 9c1c9abb): when a run ends without the
    model's final reply but its business result was already recorded, the
    recorded result is delivered instead of silence — no extra model request.
    """
    receipt = outcome.receipt
    presentation = outcome.presentation.strip()
    if receipt.execution_state != "completed":
        note = (
            "本次研究没有完整结束，因此没有使用不完整证据给出预测。"
            "系统已保留运行诊断，可直接重试。"
            if receipt.execution_state == "failed"
            else "本轮已达到运行预算上限，先停在这里；可直接重试继续。"
        )
        if reply_artifact and reply_artifact.strip():
            return (
                f"{note}\n\n"
                "以下是本轮已落盘的决策结论（来自运行产物，非重新推理）：\n\n"
                f"{reply_artifact.strip()}\n\n"
                "/inspect — 完整运行诊断（操作员）"
            )
        return f"{note}\n/inspect — 完整运行诊断（操作员）"
    if presentation:
        return presentation
    return "\n".join(
        [
            "✅ Completed",
            "",
            receipt.outcome,
            "",
            f"Artifact byte facts: {len(receipt.artifact_facts)}",
            f"Tool-effect facts: {len(receipt.tool_effect_facts)}",
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
