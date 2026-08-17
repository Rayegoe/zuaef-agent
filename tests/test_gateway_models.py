"""Gateway domain model tests — SPEC v0.3 §73."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from zuaef_agent.gateway.models import (
    ApprovalBinding,
    AttachmentRef,
    InboundEnvelope,
    SessionBinding,
)


def test_attachment_ref_minimal():
    ref = AttachmentRef(kind="document", local_path="inbox/telegram/a1-x.csv")
    assert ref.original_name is None
    assert ref.size is None
    assert ref.kind == "document"


def test_attachment_ref_kind_is_restricted():
    with pytest.raises(ValidationError):
        AttachmentRef(kind="video", local_path="inbox/x.mp4")


def test_inbound_envelope_defaults():
    env = InboundEnvelope(
        surface="telegram", user_id="42", channel_id="42", message_id="m1"
    )
    assert env.tenant_id == "default"
    assert env.thread_id is None
    assert env.text == ""
    assert env.attachments == []
    assert env.callback_action is None
    assert env.transport_context == {}


def test_inbound_envelope_callback_payload():
    env = InboundEnvelope(
        surface="telegram",
        user_id="42",
        channel_id="42",
        message_id="cb1",
        callback_token="opaque-token",
        callback_action="approve",
        transport_context={"callback_query_id": "qid-1"},
    )
    assert env.callback_action == "approve"
    assert env.callback_token == "opaque-token"


def test_inbound_envelope_rejects_unknown_callback_action():
    with pytest.raises(ValidationError):
        InboundEnvelope(
            surface="telegram",
            user_id="42",
            channel_id="42",
            message_id="cb1",
            callback_action="maybe",
        )


def test_session_binding_shape():
    binding = SessionBinding(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_key="",
        conversation_id="conv-1",
        profile="wordpress-operator",
    )
    assert binding.active_run_id is None
    assert binding.paused_run_id is None
    assert binding.last_terminal_run_id is None
    assert binding.conversation_id == "conv-1"


def test_approval_binding_states():
    now = datetime.now(UTC)
    binding = ApprovalBinding(
        token_hash="a" * 64,
        surface="telegram",
        user_id="42",
        channel_id="42",
        paused_run_id="run-1",
        state="pending",
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    assert binding.consumed_at is None
    assert binding.model_copy(update={"state": "approved"}).state == "approved"
    assert binding.model_copy(update={"state": "denied"}).state == "denied"
    assert binding.model_copy(update={"state": "expired"}).state == "expired"
    with pytest.raises(ValidationError):
        ApprovalBinding.model_validate(
            binding.model_dump() | {"state": "unknown"}
        )


def test_attachment_local_path_is_workspace_relative_convention():
    """AttachmentRef carries a workspace-relative path by contract; the model
    itself is opaque, the contract is enforced by the Telegram adapter."""
    ref = AttachmentRef(kind="document", local_path="inbox/telegram/abc.csv")
    assert not ref.local_path.startswith("/")
    assert ".." not in ref.local_path.split("/")
