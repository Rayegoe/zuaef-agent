"""Feishu surface adapter — Feishu Surface v0.1 (spec pack 02).

Thin transport over the standalone ``lark-channel-sdk`` (pinned 1.4.0):
WebSocket long connection, no public webhook. The SDK owns transport,
normalization, two-layer dedup, outbound chunking/retry and card helpers;
this adapter only normalizes SDK events into the generic ``InboundEnvelope``,
applies surface admission (user allowlist, group allowlist, mention policy,
bot-sender drop) and renders outbound text/documents/cards.

Pure transport like ``telegram.py``: it never touches the runtime, business
policy or approval semantics, and it never names a business profile. Profile
aliases and per-profile access policy live in the gateway routing policy
(``routing.py``), enforced by the service before any run.

Threading model: the SDK runs its own background loop on a daemon thread.
``probe()`` starts a dedicated thread that awaits the SDK's public
``connect_until_ready()`` (whose readiness includes the WebSocket connection
being established — the raw ``is_ready`` flag only flips AFTER the blocking
``start()`` returns, i.e. never while the transport runs) and then keeps
that loop alive for the process lifetime; SDK event handlers push normalized
envelopes into a thread-safe queue and the gateway runner's sync serial loop
drains it via ``poll_once`` (blocking wait, no API polling). Outbound
helpers submit SDK coroutines through the public ``channel.schedule`` and
wait bounded — they log failures instead of raising so a transport error
cannot kill the gateway dispatch loop.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from lark_channel import FeishuChannel, PolicyConfig, SecurityConfig

from .models import (
    CONTROL_CALLBACK_ACTIONS,
    CONTROL_PREFIX,
    InboundEnvelope,
)

logger = logging.getLogger(__name__)

# Card value framing shared with the Telegram transport: the gateway service
# mints ``zg:<token>:a|d`` approval values and ``zc:<action>:<payload>``
# supervisor-control values; the adapter only parses the frame.
CALLBACK_PREFIX = "zg"
_CALLBACK_FRAME_PARTS = 3

# One poll drains at most this many queued events after the first one —
# bounded batching, mirroring a long-poll batch.
_POLL_BATCH_MAX = 10

_SEND_TIMEOUT_SECONDS = 30.0
_CONNECT_POLL_INTERVAL = 0.1


class FeishuAdapter:
    """WebSocket adapter for one Feishu app and one allowlist.

    Fail-closed rules live at startup: an empty user allowlist aborts in the
    constructor, connection failure aborts ``probe()``; at runtime every
    inbound event from a non-allowlisted user, a bot sender, a non-allowlisted
    group or (in groups) without the bot mention is dropped before the
    gateway service ever sees it.
    """

    surface_name = "feishu"

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        allowed_user_ids: set[str],
        workspace_root: Path,
        allowed_chat_ids: set[str] | None = None,
        require_mention: bool = True,
        security_mode: str = "audit",
        domain: str | None = None,
        connect_timeout: float = 30.0,
        channel: Any | None = None,
    ):
        if not allowed_user_ids:
            raise ValueError(
                "FeishuAdapter requires at least one allowed user id "
                "(fail closed; there is no allow-all default)"
            )
        self.app_id = app_id
        self.app_secret = app_secret
        self.allowed_user_ids = set(allowed_user_ids)
        self.allowed_chat_ids = set(allowed_chat_ids or ())
        self.require_mention = require_mention
        self.security_mode = security_mode
        self.domain = domain
        self.workspace_root = workspace_root
        self.connect_timeout = connect_timeout
        self._events: queue.Queue[InboundEnvelope] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._thread_error: BaseException | None = None
        self._ready = threading.Event()
        if channel is not None:
            self._channel = channel
        else:
            self._channel = self._build_channel()
        self._channel.on("message", self._on_message)
        self._channel.on("cardAction", self._on_card_action)
        self._channel.on("error", self._on_error)

    # ── transport lifecycle ─────────────────────────────────────────────────

    def _build_channel(self) -> FeishuChannel:
        policy = PolicyConfig(
            dm_policy="allowlist",
            group_policy="allowlist",
            require_mention=self.require_mention,
            respond_to_mention_all=False,
            allow_from=sorted(self.allowed_user_ids),
            group_allowlist=sorted(self.allowed_chat_ids) or None,
        )
        security = SecurityConfig(mode=self.security_mode)
        kwargs: dict[str, Any] = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
            "transport": "ws",
            "policy": policy,
            "security": security,
        }
        if self.domain:
            kwargs["domain"] = self.domain
        return FeishuChannel(**kwargs)

    def probe(self) -> dict[str, Any]:
        """Start the WebSocket transport and wait until the connection is
        established; raise (fail closed) when it does not come up in time.
        A failed handshake raises inside the transport thread and surfaces
        here immediately; a hung one hits the connect timeout."""
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._run_channel, name="zuaef-feishu-channel", daemon=True
            )
            self._thread.start()
        deadline = time.monotonic() + self.connect_timeout
        while time.monotonic() < deadline:
            if self._thread_error is not None:
                raise RuntimeError(
                    f"feishu transport failed to start: {self._thread_error}"
                ) from self._thread_error
            if self._ready.is_set():
                return {"ready": True}
            time.sleep(_CONNECT_POLL_INTERVAL)
        raise RuntimeError(
            f"feishu transport not ready within {self.connect_timeout:.0f}s"
        )

    def _run_channel(self) -> None:
        try:
            asyncio.run(self._channel_session())
        except BaseException as exc:  # noqa: BLE001 — thread boundary: record
            # any death (including KeyboardInterrupt) for probe()/poll_once().
            self._thread_error = exc
            logger.error("feishu channel thread died: %s", exc)

    async def _channel_session(self) -> None:
        # connect_until_ready returns as soon as the WebSocket connection
        # exists (its readiness includes the live connection, unlike the
        # raw is_ready flag). Afterwards keep this loop alive forever — the
        # SDK's blocking start() runs on this loop's executor thread and the
        # SDK's own auto-reconnect owns the connection from here on.
        try:
            await self._channel.connect_until_ready(timeout=self.connect_timeout)
        except TimeoutError as exc:
            raise RuntimeError(
                f"feishu transport not ready within {self.connect_timeout:.0f}s"
            ) from exc
        self._ready.set()
        logger.info("feishu transport ready; connection owned by the SDK")
        await asyncio.Event().wait()

    def _assert_transport_alive(self) -> None:
        if self._thread is not None and (
            not self._thread.is_alive() or self._thread_error is not None
        ):
            raise RuntimeError(
                "feishu transport thread is not running; restarting the "
                "gateway process is required"
            )

    def close(self) -> None:
        try:
            # Idempotent and safe from any thread (SDK contract). The SDK
            # raises several unrelated exception types — a shutdown failure
            # must never mask the gateway's own shutdown.
            self._channel.stop()
        except Exception as exc:  # noqa: BLE001 — transport shutdown, logged
            logger.warning("feishu channel stop failed: %s", exc)
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    # ── inbound ─────────────────────────────────────────────────────────────

    def poll_once(self, *, timeout_seconds: int) -> list[InboundEnvelope]:
        """Blocking drain of the normalized inbound queue — one SDK event
        delivery becomes exactly one envelope; duplicates never reach this
        layer because the SDK's two-layer dedup runs before dispatch."""
        self._assert_transport_alive()
        try:
            first = self._events.get(timeout=max(float(timeout_seconds), 0.0))
        except queue.Empty:
            return []
        events = [first]
        while len(events) < _POLL_BATCH_MAX:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events

    def pending_cursor(self) -> str | None:
        """WebSocket transport has no offset cursor: the SDK dedup covers
        reconnect backfill, so there is nothing to persist per batch."""
        return None

    def _on_message(self, msg: Any) -> None:
        try:
            envelope = self._normalize_message(msg)
        except Exception:
            logger.exception("feishu inbound normalization failed")
            return
        if envelope is not None:
            self._events.put(envelope)

    def _normalize_message(self, msg: Any) -> InboundEnvelope | None:
        user_id = getattr(msg, "sender_id", "") or ""
        if msg.sender_is_bot or (msg.sender_type or "") in {
            "bot",
            "app",
            "system",
            "anonymous",
        }:
            logger.info("ignored feishu bot/app sender %s", user_id or "?")
            return None
        if user_id not in self.allowed_user_ids:
            logger.info("ignored inbound from unauthorized feishu user %s", user_id)
            return None
        chat_type = getattr(msg, "chat_type", None) or "unknown"
        channel_id = getattr(msg, "chat_id", "") or ""
        if chat_type == "group":
            # Spec pack 03 §7: groups are allowlist-only — an empty group
            # allowlist refuses every group (fail closed), leaving DMs.
            if channel_id not in self.allowed_chat_ids:
                logger.info(
                    "ignored feishu group %s: not in the surface allowlist",
                    channel_id,
                )
                return None
            if self.require_mention and not msg.mentioned_bot:
                return None  # group chatter without @bot is not addressed to us
        elif chat_type != "p2p":
            logger.info("ignored feishu chat type %s in %s", chat_type, channel_id)
            return None
        # body_text is content_text minus this bot's own @mention (SDK
        # semantics) — the right basis for command routing.
        body = (getattr(msg, "body_text", "") or "").strip()
        if not body:
            kind = getattr(getattr(msg, "content", None), "kind", "unknown")
            logger.info(
                "ignored feishu non-text message kind=%s (v0.1 handles text/post only)",
                kind,
            )
            return None
        thread_id = getattr(getattr(msg, "conversation", None), "thread_id", None)
        return InboundEnvelope(
            surface=self.surface_name,
            user_id=user_id,
            channel_id=channel_id,
            thread_id=thread_id or None,
            chat_type=chat_type,
            message_id=getattr(msg, "message_id", "") or "",
            text=body,
            # Authorized Feishu operators speak as the supervisor, mirroring
            # the Telegram console allowlist semantics.
            actor_role="supervisor",
        )

    def _on_card_action(self, event: Any) -> None:
        try:
            envelope = self._normalize_card_action(event)
        except Exception:
            logger.exception("feishu card action normalization failed")
            return
        if envelope is not None:
            self._events.put(envelope)

    def _normalize_card_action(self, event: Any) -> InboundEnvelope | None:
        user_id = getattr(getattr(event, "operator", None), "open_id", "") or ""
        if user_id not in self.allowed_user_ids:
            logger.info("ignored feishu card action from unauthorized user %s", user_id)
            return None
        value = getattr(getattr(event, "action", None), "value", None)
        data = value.get("callback_data") if isinstance(value, dict) else None
        parts = data.split(":") if isinstance(data, str) else []
        if (
            len(parts) != _CALLBACK_FRAME_PARTS
            or parts[0] not in (CALLBACK_PREFIX, CONTROL_PREFIX)
        ):
            logger.info("ignored unknown feishu card action value: %r", value)
            return None
        kwargs: dict[str, Any] = {
            "surface": self.surface_name,
            "user_id": user_id,
            "channel_id": getattr(event, "chat_id", "") or "",
            "message_id": getattr(event, "message_id", "") or "",
            "text": "",
            "actor_role": "supervisor",
            # The card message doubles as the callback id; Feishu has no
            # toast API — outcomes are delivered as chat messages.
            "transport_context": {
                "callback_query_id": getattr(event, "message_id", "") or ""
            },
        }
        if parts[0] == CONTROL_PREFIX:
            action, payload = parts[1], parts[2]
            if action not in CONTROL_CALLBACK_ACTIONS:
                logger.info("ignored unknown feishu control action %r", action)
                return None
            kwargs["callback_action"] = action
            kwargs["callback_payload"] = payload or None
        else:
            token, action = parts[1], parts[2]
            if action not in ("a", "d"):
                logger.info("ignored unknown feishu approval action %r", action)
                return None
            kwargs["callback_token"] = token
            kwargs["callback_action"] = "approve" if action == "a" else "deny"
        return InboundEnvelope(**kwargs)

    def _on_error(self, error: Any) -> None:
        logger.error("feishu transport error: %s", error)

    # ── outbound ────────────────────────────────────────────────────────────

    def send_text(self, channel_id: str, text: str) -> None:
        self._submit(self._channel.send(channel_id, {"text": text}))

    def send_document(
        self,
        channel_id: str,
        path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        # Feishu file messages carry no caption — send it as its own text.
        if caption:
            self.send_text(channel_id, caption)
        self._submit(
            self._channel.send(
                channel_id,
                {"file": {"source": str(path), "fileName": path.name}},
            )
        )

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
        approve_label: str = "Approve",
        deny_label: str = "Deny",
    ) -> None:
        card = self._card(
            text,
            [
                [
                    self._button(
                        approve_label, f"{CALLBACK_PREFIX}:{approve_token}:a"
                    ),
                    self._button(deny_label, f"{CALLBACK_PREFIX}:{approve_token}:d"),
                ]
            ],
        )
        self._submit(self._channel.send(channel_id, {"card": card}))

    def send_keyboard(
        self,
        channel_id: str,
        *,
        text: str,
        buttons: Sequence[tuple[str, str]],
    ) -> None:
        # One button per row, mirroring the Telegram control keyboard.
        card = self._card(
            text, [[self._button(label, data)] for label, data in buttons]
        )
        self._submit(self._channel.send(channel_id, {"card": card}))

    def answer_callback(self, callback_id: str, text: str) -> None:
        # Feishu card actions are acknowledged by the SDK itself and there is
        # no toast API; the decision outcome arrives as the next chat message
        # (same content the Telegram toast would show).
        logger.debug("feishu callback %s: %s", callback_id, text)

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _card(text: str, rows: list[list[dict[str, Any]]]) -> dict[str, Any]:
        return {
            "config": {"wide_screen_mode": True},
            "elements": [
                {"tag": "markdown", "content": text},
                {"tag": "hr"},
                *({"tag": "action", "actions": row} for row in rows),
            ],
        }

    @staticmethod
    def _button(label: str, value: str) -> dict[str, Any]:
        return {
            "tag": "button",
            "text": {"tag": "plain_text", "content": label},
            "type": "primary",
            "value": {"callback_data": value},
        }

    def _submit(self, coro: Any) -> Any:
        """Run an SDK coroutine on its background loop and wait bounded.

        Never raises: an outbound failure is logged for the operator instead
        of killing the gateway dispatch loop (the Telegram adapter raises
        ``httpx`` errors the runner already tolerates; this adapter keeps its
        failures non-fatal by contract).
        """
        try:
            future = self._channel.schedule(coro)
        except Exception as exc:  # noqa: BLE001 — outbound is non-fatal by
            # contract (see module docstring); every failure is logged.
            logger.error("feishu outbound submit failed: %s", exc)
            return None
        try:
            return future.result(timeout=_SEND_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 — outbound is non-fatal
            logger.error("feishu outbound send failed: %s", exc)
            return None
