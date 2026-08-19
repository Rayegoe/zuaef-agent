"""Surface adapter contract — SPEC v0.3 §13.

Stage A does not build an entry-point registry: surfaces are wired
explicitly. An adapter normalizes inbound platform events into
``InboundEnvelope`` (never leaking platform-specific objects upward) and
renders outbound text, documents and approval buttons. The Gateway Service
and the runtime never see a Telegram ``Update``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .models import InboundEnvelope


class SurfaceAdapter(Protocol):
    surface_name: str

    def poll_once(
        self,
        *,
        timeout_seconds: int,
    ) -> list[InboundEnvelope]:
        """Blocking fetch of the next batch of normalized inbound events."""
        ...

    def send_text(
        self,
        channel_id: str,
        text: str,
    ) -> None:
        ...

    def send_document(
        self,
        channel_id: str,
        path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        ...

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
        approve_label: str = "Approve",
        deny_label: str = "Deny",
    ) -> None:
        ...

    def send_keyboard(
        self,
        channel_id: str,
        *,
        text: str,
        buttons: Sequence[tuple[str, str]],
    ) -> None:
        """Render text with a deterministic control keyboard (one button per
        row). Each button is ``(label, callback_data)``; the callback_data is
        minted by the gateway service, never by the model."""
        ...

    def answer_callback(
        self,
        callback_id: str,
        text: str,
    ) -> None:
        ...

    def pending_cursor(self) -> str | None:
        """Latest processed surface cursor (Telegram ``update_id`` offset), or
        ``None`` when nothing new was processed. The gateway loop persists it
        after handling a batch so a restart never reprocesses old updates."""
        ...
