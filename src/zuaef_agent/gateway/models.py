"""Gateway domain models — SPEC v0.3 §8.

Gateway models describe surface interaction only: inbound normalization,
session binding and approval routing state. They never carry execution truth
(message history, tool effects, receipts) — that stays owned by the core
runtime (ReceiptStore / StepPersistence / tool-effect ledger).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttachmentRef(BaseModel):
    """One inbound attachment, already downloaded to a workspace-relative path.

    ``local_path`` is workspace-relative (e.g. ``inbox/telegram/<uuid>-x.csv``);
    no absolute path may ever reach a user-visible message.
    """

    kind: Literal["document", "image", "audio", "other"]
    local_path: str
    original_name: str | None = None
    mime_type: str | None = None
    size: int | None = None


class InboundEnvelope(BaseModel):
    """Normalized inbound interaction; upper layers never see Telegram objects."""

    surface: str
    tenant_id: str = "default"

    user_id: str
    channel_id: str
    thread_id: str | None = None

    message_id: str
    text: str = ""

    attachments: list[AttachmentRef] = Field(default_factory=list)

    callback_token: str | None = None
    callback_action: Literal["approve", "deny"] | None = None

    # Surface-specific non-secret transport context (e.g. the Telegram
    # callback_query_id needed to answer a callback). Full platform Updates
    # must not leak through here.
    transport_context: dict[str, str] = Field(default_factory=dict)


class SessionBinding(BaseModel):
    """Gateway routing state for one surface session (SPEC §8.3).

    ``conversation_id`` is a correlation identity only — not automatic model
    chat memory. Pause/resume continuity comes from StepPersistence history;
    terminal runs do not pretend to share model memory.

    ``case_id`` is the deterministically bound business work item (SPEC v1.0
    §5): a supervisor binds a channel/thread to exactly one Case — no model
    identity guessing. Conversation identity and Case identity stay separate;
    ``/new`` rotates the conversation but keeps the Case binding.
    """

    surface: str
    tenant_id: str

    user_id: str
    channel_id: str
    thread_key: str

    conversation_id: str
    profile: str | None
    case_id: str | None = None

    active_run_id: str | None = None
    paused_run_id: str | None = None
    last_terminal_run_id: str | None = None


class ApprovalBinding(BaseModel):
    """One pending interactive approval (SPEC §8.4).

    The store keeps only the SHA-256 of the opaque callback token; the raw
    token exists in the user-visible callback data only.
    """

    token_hash: str

    surface: str
    user_id: str
    channel_id: str

    paused_run_id: str

    state: Literal["pending", "approved", "denied", "expired"]

    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
