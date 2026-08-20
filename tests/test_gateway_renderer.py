"""Renderer tests — SPEC v0.3 §40–§44: deterministic, redacting, bounded."""

from __future__ import annotations

from datetime import UTC, datetime

from zuaef_agent.gateway.renderer import (
    CHUNK_MAX,
    chunk_text,
    preview_arguments,
    render_case_card,
    render_cases,
    render_error,
    render_new_conversation,
    render_pause,
    render_profile,
    render_status,
    render_terminal,
)
from zuaef_agent.models import (
    ArtifactFact,
    PauseReceipt,
    RunReceipt,
    ToolEffectFact,
)
from zuaef_agent.runtime import PausedRun, TerminalRun


def _paused(approvals: list[dict]) -> PausedRun:
    now = datetime.now(UTC)
    receipt = PauseReceipt(
        run_id="run-paused-1234",
        conversation_id="conv-1",
        model="test",
        started_at=now,
        finished_at=now,
        pending_approvals=approvals,
    )
    return PausedRun(
        requests=None,  # type: ignore[arg-type]
        message_history=[],
        conversation_id="conv-1",
        pause_receipt=receipt,
    )


def _terminal(state="completed", presentation=None) -> TerminalRun:
    now = datetime.now(UTC)
    receipt = RunReceipt(
        run_id="run-term-1234",
        model="test",
        started_at=now,
        finished_at=now,
        execution_state=state,  # type: ignore[arg-type]
        outcome="post published",
        artifact_facts=[ArtifactFact(path="a.md", size=1, sha256="x" * 64, change="created")],
        tool_effect_facts=[
            ToolEffectFact(tool_call_id="c1", tool_name="wordpress_publish_post", status="completed")
        ],
    )
    if presentation is None:
        presentation = receipt.outcome
    return TerminalRun(presentation=presentation, receipt=receipt)


def test_preview_redacts_secret_named_keys():
    preview = preview_arguments(
        {
            "post_id": 123,
            "auth_token": "secret-value",
            "api_key": "key-value",
            "password": "pw",
        }
    )
    assert "post_id: 123" in preview
    assert "auth_token: ***REDACTED***" in preview
    assert "api_key: ***REDACTED***" in preview
    assert "password: ***REDACTED***" in preview
    assert "secret-value" not in preview
    assert "key-value" not in preview
    assert "pw" not in preview.replace("post_id: 123", "")


def test_preview_bounded_to_1200_chars():
    preview = preview_arguments({"payload": "x" * 5000})
    assert len(preview) <= 1200 + 5
    assert preview.endswith("…")


def test_render_terminal_classic_card_when_no_presentation():
    text = render_terminal(_terminal(presentation=""))
    assert "✅ Completed" in text
    assert "post published" in text
    assert "Artifact byte facts: 1" in text
    assert "Tool-effect facts: 1" in text
    assert "Run: run-term-1234" in text


def test_render_terminal_failed_and_limit():
    assert "⛔ Failed" in render_terminal(_terminal("failed"))
    assert "⏹ Limit reached" in render_terminal(_terminal("limit_reached"))


def test_render_terminal_presentation_is_the_reply():
    article = "### 夏天的指尖\n\n到了八月,美甲似乎也该从好看里退一步。"
    text = render_terminal(_terminal(presentation=article))
    assert text.startswith(article)
    assert "✅ Completed" in text
    assert "Run: run-term" in text  # short id on the outcome-first card
    assert "post published" not in text  # audit prose is Console-only here
    assert "Artifact byte facts" not in text


def test_render_pause_shows_outbound_content():
    text = render_pause(
        _paused(
            [{"tool_name": "send_to_customer", "args": {"draft_ref": "msg-004.md"}}]
        ),
        content="给客户的正文——不会批没看过的东西",
    )
    assert "Content to send:" in text
    assert "给客户的正文——不会批没看过的东西" in text
    assert "[Approve]" in text and "[Deny]" in text


def test_render_pause_single_approval():
    text = render_pause(_paused([{"tool_name": "wordpress_publish_post", "args": {"post_id": 123, "auth_token": "s"}}]))
    assert "⚠️ Approval required" in text
    assert "wordpress_publish_post" in text
    assert "post_id: 123" in text
    assert "***REDACTED***" in text
    assert "[Approve]" in text
    assert "[Deny]" in text


def test_render_pause_batch_approval():
    text = render_pause(
        _paused(
            [
                {"tool_name": "t1", "args": {}},
                {"tool_name": "t2", "args": {}},
                {"tool_name": "t3", "args": {}},
            ]
        )
    )
    assert "3 actions require approval" in text
    assert "1. t1" in text
    assert "[Approve all]" in text
    assert "[Deny all]" in text


def test_render_status_states():
    base = {"profile": "wordpress-operator", "conversation_id": "conversation-abc"}
    ready = render_status(**base, state="READY")
    assert "State: READY" in ready
    assert "Profile: wordpress-operator" in ready
    paused = render_status(
        **base, state="PAUSED", run_id="run-1", pending_approval_count=2, pending_tools=["t"]
    )
    assert "State: PAUSED" in paused
    assert "Pending approvals: 2" in paused


def test_render_status_includes_case_binding_line():
    card = render_status(
        profile="stillevo-fde",
        conversation_id="conversation-abc",
        case_id="stillevo-beauty",
        state="READY",
    )
    assert "Case: stillevo-beauty" in card
    unbound = render_status(
        profile="stillevo-fde", conversation_id="conversation-abc", state="READY"
    )
    assert "Case: (unbound)" in unbound


def test_render_case_card_bound_and_unbound():
    bound = render_case_card(
        case_id="stillevo-beauty",
        profile="stillevo-fde",
        conversation_id="conversation-abc",
    )
    assert "Case: stillevo-beauty" in bound
    assert "Profile: stillevo-fde" in bound
    assert "State: READY" in bound
    unbound = render_case_card(
        case_id=None, profile=None, conversation_id="conversation-abc"
    )
    assert "Case: (unbound)" in unbound
    assert "Profile: (none)" in unbound


def test_render_cases_listing_marks_bound_case():
    text = render_cases(
        [("newer-case", "2026-08-19"), ("older-case", "2026-08-01")],
        bound_case="older-case",
    )
    assert "newer-case" in text and "older-case" in text
    assert "- older-case (bound)" in text
    assert "- newer-case ·" in text
    assert "No cases found" in render_cases([], bound_case=None)


def test_render_profile_and_new_and_error():
    profile = render_profile(current="writing", available=["writing", "wordpress-operator"])
    assert "Current profile: writing" in profile
    assert "- wordpress-operator" in profile
    assert "Profile: writing" in render_new_conversation("writing")
    assert render_error("boom") == "⚠️ boom"


def test_chunk_text_respects_max():
    text = "line\n" * 3000
    chunks = chunk_text(text)
    assert all(len(chunk) <= CHUNK_MAX for chunk in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")
    assert chunk_text("short") == ["short"]
