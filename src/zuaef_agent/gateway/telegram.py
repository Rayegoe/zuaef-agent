"""Telegram surface adapter — SPEC v0.3 §15–§19.

Direct Telegram Bot HTTP API over ``httpx`` (no bot SDK). Stage A scope:
private chats only, text + document inbound, text + document + approval
keyboard outbound, callback queries for Approve/Deny, a mandatory user-id
allowlist, bot-token redaction and workspace-relative document downloads.

The adapter is pure transport: it never touches the runtime, business
policy or approval semantics.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from .models import AttachmentRef, InboundEnvelope

logger = logging.getLogger(__name__)

CALLBACK_PREFIX = "zg"
GROUP_CHAT_REFUSAL = "Group chats are not enabled in this gateway build."

_BOT_TOKEN_IN_URL = re.compile(r"/bot[0-9A-Za-z:_-]+/")
_SANITIZE_KEEP = re.compile(r"[^A-Za-z0-9._-]")


def redact_token(text: str) -> str:
    """Replace ``/bot<TOKEN>/`` occurrences; used on every error render."""
    return _BOT_TOKEN_IN_URL.sub("/bot***/", text)


def _http_proxy() -> str | None:
    """Mirror providers.py: honor http(s) proxies only; a socks:// ALL_PROXY
    (TUN/transparent local setups) must not break Telegram API calls."""
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name)
        if value and value.startswith(("http://", "https://")):
            return value
    return None


class TelegramAdapter:
    """Blocking long-poll adapter for one bot token and one allowlist.

    Fail-closed rule lives at startup (empty allowlist aborts before polling);
    at runtime every inbound update from a non-allowlisted user id is dropped.
    """

    surface_name = "telegram"

    def __init__(
        self,
        *,
        token: str,
        allowed_user_ids: set[str],
        workspace_root: Path,
        poll_timeout: int = 30,
        max_upload_bytes: int = 20 * 1024 * 1024,
        http_client: httpx.Client | None = None,
    ):
        self.token = token
        self.allowed_user_ids = allowed_user_ids
        self.workspace_root = workspace_root
        self.poll_timeout = poll_timeout
        self.max_upload_bytes = max_upload_bytes
        self._client = http_client or httpx.Client(
            timeout=60.0, trust_env=False, proxy=_http_proxy()
        )
        self._offset: int | None = None

    # ── HTTP plumbing ───────────────────────────────────────────────────────

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.token}/{method}"

    def _file_url(self, file_path: str) -> str:
        return f"https://api.telegram.org/file/bot{self.token}/{file_path}"

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(self._api_url(method), json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise httpx.HTTPError(redact_token(str(exc))) from exc
        data = response.json()
        if not data.get("ok"):
            raise httpx.HTTPError(redact_token(f"telegram {method} failed: {data}"))
        return data

    def _download_bytes(self, url: str) -> bytes:
        response = self._client.get(url)
        response.raise_for_status()
        return response.content

    def probe(self) -> dict[str, Any]:
        """Startup getMe probe; raises on failure so the gateway fails closed."""
        return self._post("getMe", {}).get("result", {})

    def set_offset(self, offset: int | None) -> None:
        """Seed the update_id offset from the persisted surface cursor."""
        self._offset = offset

    # ── polling ─────────────────────────────────────────────────────────────

    def poll_once(self, *, timeout_seconds: int) -> list[InboundEnvelope]:
        payload: dict[str, Any] = {
            "timeout": timeout_seconds if timeout_seconds > 0 else self.poll_timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if self._offset is not None:
            payload["offset"] = self._offset
        data = self._post("getUpdates", payload)
        updates = data.get("result", [])
        events: list[InboundEnvelope] = []
        for update in updates:
            self._offset = int(update["update_id"]) + 1
            event = self._normalize_update(update)
            if event is not None:
                events.append(event)
        return events

    def pending_cursor(self) -> str | None:
        return str(self._offset) if self._offset is not None else None

    def _normalize_update(self, update: dict[str, Any]) -> InboundEnvelope | None:
        message = update.get("message")
        if message is not None:
            return self._normalize_message(message)
        callback = update.get("callback_query")
        if callback is not None:
            return self._normalize_callback(callback)
        return None

    # ── inbound normalization ───────────────────────────────────────────────

    def _authorized(self, user_id: str) -> bool:
        return user_id in self.allowed_user_ids

    def _normalize_message(self, message: dict[str, Any]) -> InboundEnvelope | None:
        user_id = str(message.get("from", {}).get("id", ""))
        if not self._authorized(user_id):
            logger.info("ignored inbound from unauthorized telegram user %s", user_id)
            return None
        chat = message.get("chat", {})
        chat_type = chat.get("type")
        if chat_type not in ("private",):
            self.send_text(str(chat.get("id", "")), GROUP_CHAT_REFUSAL)
            return None
        channel_id = str(chat.get("id", ""))
        attachments = self._download_documents(message, channel_id=channel_id)
        return InboundEnvelope(
            surface=self.surface_name,
            user_id=user_id,
            channel_id=channel_id,
            thread_id=None,
            message_id=str(message.get("message_id", "")),
            text=message.get("text") or message.get("caption") or "",
            attachments=attachments,
        )

    def _download_documents(
        self, message: dict[str, Any], *, channel_id: str
    ) -> list[AttachmentRef]:
        document = message.get("document")
        attachments: list[AttachmentRef] = []
        if document is None:
            return attachments
        size = document.get("file_size")
        if isinstance(size, int) and size > self.max_upload_bytes:
            self.send_text(
                channel_id,
                f"Attachment rejected: exceeds {self.max_upload_bytes} bytes.",
            )
            return attachments
        file_id = document.get("file_id")
        if not file_id:
            return attachments
        get_file = self._post("getFile", {"file_id": file_id})
        file_path = get_file.get("result", {}).get("file_path")
        if not file_path:
            return attachments
        content = self._download_bytes(self._file_url(file_path))
        if len(content) > self.max_upload_bytes:
            self.send_text(
                channel_id,
                f"Attachment rejected: exceeds {self.max_upload_bytes} bytes.",
            )
            return attachments
        original_name = document.get("file_name") or Path(file_path).name
        safe_name = Path(original_name).name
        safe_name = _SANITIZE_KEEP.sub("_", safe_name) or "upload"
        target = (
            self.workspace_root
            / "inbox"
            / "telegram"
            / f"{uuid4().hex}-{safe_name}"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        attachments.append(
            AttachmentRef(
                kind="document",
                local_path=str(
                    target.relative_to(self.workspace_root.resolve())
                ).replace("\\", "/"),
                original_name=original_name,
                mime_type=document.get("mime_type"),
                size=len(content),
            )
        )
        return attachments

    def _normalize_callback(
        self, callback: dict[str, Any]
    ) -> InboundEnvelope | None:
        user_id = str(callback.get("from", {}).get("id", ""))
        if not self._authorized(user_id):
            logger.info("ignored callback from unauthorized telegram user %s", user_id)
            return None
        data = callback.get("data") or ""
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
            self.answer_callback(str(callback.get("id", "")), "Unknown action.")
            return None
        token, action = parts[1], parts[2]
        if action not in ("a", "d"):
            self.answer_callback(str(callback.get("id", "")), "Unknown action.")
            return None
        message = callback.get("message", {})
        chat = message.get("chat", {})
        channel_id = str(chat.get("id", ""))
        return InboundEnvelope(
            surface=self.surface_name,
            user_id=user_id,
            channel_id=channel_id,
            thread_id=None,
            message_id=str(callback.get("id", "")),
            text="",
            callback_token=token,
            callback_action="approve" if action == "a" else "deny",
            transport_context={"callback_query_id": str(callback.get("id", ""))},
        )

    # ── outbound rendering ──────────────────────────────────────────────────

    def send_text(self, channel_id: str, text: str) -> None:
        self._post(
            "sendMessage",
            {"chat_id": channel_id, "text": text, "disable_web_page_preview": True},
        )

    def send_document(
        self,
        channel_id: str,
        path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"chat_id": channel_id}
        if caption:
            payload["caption"] = caption
        with path.open("rb") as handle:
            response = self._client.post(
                self._api_url("sendDocument"),
                data=payload,
                files={"document": (path.name, handle)},
            )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise httpx.HTTPError(redact_token(str(exc))) from exc
        data = response.json()
        if not data.get("ok"):
            raise httpx.HTTPError(redact_token(f"telegram sendDocument failed: {data}"))

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
        approve_label: str = "Approve",
        deny_label: str = "Deny",
    ) -> None:
        keyboard = [
            [
                {
                    "text": approve_label,
                    "callback_data": f"{CALLBACK_PREFIX}:{approve_token}:a",
                },
                {
                    "text": deny_label,
                    "callback_data": f"{CALLBACK_PREFIX}:{approve_token}:d",
                },
            ]
        ]
        self._post(
            "sendMessage",
            {
                "chat_id": channel_id,
                "text": text,
                "reply_markup": {"inline_keyboard": keyboard},
            },
        )

    def answer_callback(self, callback_id: str, text: str) -> None:
        self._post(
            "answerCallbackQuery",
            {"callback_query_id": callback_id, "text": text},
        )

    def close(self) -> None:
        self._client.close()
