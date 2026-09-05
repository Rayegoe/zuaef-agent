"""Telegram Bot API outbound transport for the reporting plugin.

Thin, bounded, fail-loud: direct httpx calls to the Bot API ``sendMessage``
(no bot SDK), one payload (``chat_id`` + ``text``), and any failure raises
``TelegramError`` — a send is never reported as success unless Telegram's
response says so.

The transport mirrors the Gateway's constraints (http(s) proxy only, token
redaction) but is self-contained: the plugin is an agent-side communication
tool, never an interaction surface, and must not import Gateway code.

Secrets: the bot token is embedded in the API URL by construction, so every
``TelegramError`` is raised ``from None`` and its message is passed through
``redact_token`` — no chained exception repr carrying the raw URL can leak
the token into a tool error, a receipt or a log.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

SEND_MESSAGE_URL = "https://api.telegram.org/bot{token}/sendMessage"
SEND_DOCUMENT_URL = "https://api.telegram.org/bot{token}/sendDocument"

_BOT_TOKEN_IN_URL = re.compile(r"/bot[0-9A-Za-z:_-]+/")


class TelegramError(RuntimeError):
    """A loud Telegram failure: never rendered as a successful tool result."""


def redact_token(text: str) -> str:
    """Replace ``/bot<TOKEN>/`` occurrences so a token never leaks into text."""
    return _BOT_TOKEN_IN_URL.sub("/bot***/", text)


def _http_proxy() -> str | None:
    """Honor http(s) proxies only; a socks:// ALL_PROXY must not break calls."""
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        value = os.environ.get(name)
        if value and value.startswith(("http://", "https://")):
            return value
    return None


class TelegramClient:
    """Outbound sender for exactly one bot token and one target chat."""

    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._token = bot_token
        self._chat_id = str(chat_id)
        # ``proxy`` and ``transport`` are mutually exclusive in httpx: an
        # injected transport owns the network layer entirely (tests), while
        # production reaches the Bot API through the local http(s) proxy.
        client_kwargs: dict[str, Any] = {"timeout": timeout, "trust_env": False}
        if transport is None:
            client_kwargs["proxy"] = _http_proxy()
        else:
            client_kwargs["transport"] = transport
        self._client = httpx.Client(**client_kwargs)

    def close(self) -> None:
        self._client.close()

    def send_message(self, text: str) -> dict[str, Any]:
        """Send one plain-text message and return a bounded delivery fact."""
        payload = {"chat_id": self._chat_id, "text": text}
        url = SEND_MESSAGE_URL.format(token=self._token)
        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException:
            raise TelegramError("telegram sendMessage timed out") from None
        except httpx.HTTPStatusError as exc:
            raise TelegramError(
                f"telegram sendMessage failed: HTTP {exc.response.status_code}"
            ) from None
        except httpx.HTTPError as exc:
            raise TelegramError(
                redact_token(f"telegram sendMessage failed: {exc}")
            ) from None
        try:
            data = response.json()
        except ValueError:
            raise TelegramError(
                "telegram sendMessage returned non-JSON response"
            ) from None
        if not data.get("ok"):
            raise TelegramError(
                redact_token(f"telegram sendMessage failed: {data}")
            ) from None
        result = data.get("result", {})
        return {
            "ok": True,
            "message_id": result.get("message_id"),
            "date": result.get("date"),
        }

    def send_document(self, path, *, caption: str | None = None) -> dict[str, Any]:
        """Upload one local file as a Telegram document (multipart) and
        return a bounded delivery fact. The caller owns path validation —
        this transport only opens the exact path it was handed."""
        from pathlib import Path

        path = Path(path)
        payload: dict[str, str] = {"chat_id": self._chat_id}
        if caption:
            payload["caption"] = caption
        url = SEND_DOCUMENT_URL.format(token=self._token)
        try:
            with path.open("rb") as handle:
                response = self._client.post(
                    url, data=payload, files={"document": (path.name, handle)}
                )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise TelegramError("telegram sendDocument timed out") from None
        except httpx.HTTPStatusError as exc:
            raise TelegramError(
                f"telegram sendDocument failed: HTTP {exc.response.status_code}"
            ) from None
        except httpx.HTTPError as exc:
            raise TelegramError(
                redact_token(f"telegram sendDocument failed: {exc}")
            ) from None
        try:
            data = response.json()
        except ValueError:
            raise TelegramError(
                "telegram sendDocument returned non-JSON response"
            ) from None
        if not data.get("ok"):
            raise TelegramError(
                redact_token(f"telegram sendDocument failed: {data}")
            ) from None
        result = data.get("result", {})
        return {
            "ok": True,
            "message_id": result.get("message_id"),
            "date": result.get("date"),
            "file": path.name,
        }
