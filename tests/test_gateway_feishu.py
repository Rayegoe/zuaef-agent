"""Feishu transport tests — Feishu Surface v0.1 (spec pack 07 C/D gates).

All SDK interaction goes through a ``FakeChannel`` standing in for
``lark_channel.FeishuChannel``: event registration, coroutine scheduling and
outbound sends are recorded, never networked. Normalization, surface
admission (allowlists, mention policy, bot filtering) and outbound card
framing are exercised against the real adapter.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from zuaef_agent.gateway.feishu import FeishuAdapter


class FakeChannel:
    """Stateful stand-in for the SDK channel object the adapter uses."""

    def __init__(self):
        self.handlers: dict[str, Any] = {}
        self.sent: list[tuple[str, dict, dict | None]] = []
        self.fail_next_send = False
        self.connected = False
        self.stopped = False
        # When set, connect_until_ready hangs past any probe deadline.
        self.connect_hangs = False

    def on(self, name: str, handler) -> None:
        self.handlers[name] = handler

    async def send(self, to, message, opts=None):
        self.sent.append((to, message, opts))
        if self.fail_next_send:
            self.fail_next_send = False
            raise RuntimeError("feishu transport down")
        return SimpleNamespace(success=True, message_id="om_card_1", error=None)

    async def connect_until_ready(self, *, timeout=None):
        # Mirrors the real semantic: returns once the WS connection exists.
        if self.connect_hangs:
            await asyncio.sleep(30)
        self.connected = True

    def schedule(self, coro):
        future: concurrent.futures.Future = concurrent.futures.Future()
        try:
            future.set_result(asyncio.run(coro))
        except Exception as exc:  # noqa: BLE001 — fake mirrors the SDK: send
            # errors surface through the future, exactly like the real one.
            future.set_exception(exc)
        return future

    def start(self) -> None:
        self.connected = True

    def stop(self) -> None:
        self.stopped = True


def _message(**overrides) -> SimpleNamespace:
    base = SimpleNamespace(
        message_id="om_100",
        chat_id="oc_group_1",
        chat_type="group",
        sender_id="ou_1",
        sender_type="user",
        sender_is_bot=False,
        mentioned_bot=True,
        body_text="check the post",
        content=SimpleNamespace(kind="text"),
        conversation=SimpleNamespace(thread_id=None),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _card_action(**overrides) -> SimpleNamespace:
    base = SimpleNamespace(
        message_id="om_card_1",
        chat_id="oc_group_1",
        operator=SimpleNamespace(open_id="ou_1", user_id=None, name=None),
        action=SimpleNamespace(value={"callback_data": "zg:opaque:a"}, tag="button"),
        raw={},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _adapter(channel: FakeChannel, **overrides) -> FeishuAdapter:
    kwargs: dict[str, Any] = {
        "app_id": "cli_x",
        "app_secret": "sec",
        "allowed_user_ids": {"ou_1"},
        "allowed_chat_ids": {"oc_group_1"},
        "workspace_root": Path("/tmp/ws"),
        "channel": channel,
    }
    kwargs.update(overrides)
    return FeishuAdapter(**kwargs)


def _poll_all(adapter: FeishuAdapter) -> list:
    events = adapter.poll_once(timeout_seconds=0)
    events.extend(adapter.poll_once(timeout_seconds=0))
    return events


def test_constructor_fails_closed_without_user_allowlist():
    with pytest.raises(ValueError, match="at least one allowed user"):
        FeishuAdapter(
            app_id="cli_x",
            app_secret="sec",
            allowed_user_ids=set(),
            workspace_root=Path("/tmp/ws"),
        )


def test_group_message_with_mention_normalizes():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message())

    events = _poll_all(adapter)

    assert len(events) == 1
    env = events[0]
    assert env.surface == "feishu"
    assert env.user_id == "ou_1"
    assert env.channel_id == "oc_group_1"
    assert env.chat_type == "group"
    assert env.message_id == "om_100"
    assert env.text == "check the post"
    assert env.thread_id is None
    assert env.actor_role == "supervisor"
    assert env.callback_action is None


def test_body_text_is_forwarded_verbatim_for_commands():
    """``body_text`` is the SDK-normalized text minus the bot's own @mention
    (SDK semantics); the adapter forwards it untouched as the command basis
    (spec pack 02 §5)."""
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(body_text="今天盯什么？"))
    events = _poll_all(adapter)
    assert events[0].text == "今天盯什么？"


def test_group_message_without_mention_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(mentioned_bot=False))
    assert _poll_all(adapter) == []


def test_group_message_without_mention_delivered_when_mention_not_required():
    channel = FakeChannel()
    adapter = _adapter(channel, require_mention=False)
    channel.handlers["message"](_message(mentioned_bot=False))
    events = _poll_all(adapter)
    assert len(events) == 1


def test_group_not_in_allowlist_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(chat_id="oc_other"))
    assert _poll_all(adapter) == []


def test_group_with_empty_allowlist_is_dropped_fail_closed():
    channel = FakeChannel()
    adapter = _adapter(channel, allowed_chat_ids=set())
    channel.handlers["message"](_message())
    assert _poll_all(adapter) == []


def test_bot_sender_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(sender_is_bot=True, sender_type="bot"))
    assert _poll_all(adapter) == []


def test_unauthorized_user_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(sender_id="ou_999"))
    assert _poll_all(adapter) == []


def test_p2p_message_is_delivered_without_mention():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](
        _message(
            chat_id="oc_dm_1",
            chat_type="p2p",
            mentioned_bot=False,
            body_text="hello",
        )
    )
    events = _poll_all(adapter)
    assert len(events) == 1
    assert events[0].chat_type == "p2p"
    assert events[0].text == "hello"


def test_unknown_chat_type_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](_message(chat_type="topic"))
    assert _poll_all(adapter) == []


def test_non_text_message_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](
        _message(body_text="", content=SimpleNamespace(kind="image"))
    )
    assert _poll_all(adapter) == []


def test_thread_id_normalized_from_conversation():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["message"](
        _message(conversation=SimpleNamespace(thread_id="th_1"))
    )
    events = _poll_all(adapter)
    assert events[0].thread_id == "th_1"


def test_card_action_approve_normalization():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["cardAction"](_card_action())
    events = _poll_all(adapter)
    assert len(events) == 1
    env = events[0]
    assert env.callback_action == "approve"
    assert env.callback_token == "opaque"
    assert env.transport_context["callback_query_id"] == "om_card_1"
    assert env.channel_id == "oc_group_1"


def test_card_action_deny_normalization():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["cardAction"](
        _card_action(action=SimpleNamespace(value={"callback_data": "zg:t:d"}))
    )
    events = _poll_all(adapter)
    assert events[0].callback_action == "deny"


def test_card_action_control_bind_normalization():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["cardAction"](
        _card_action(action=SimpleNamespace(value={"callback_data": "zc:bind:c1"}))
    )
    events = _poll_all(adapter)
    env = events[0]
    assert env.callback_action == "bind"
    assert env.callback_payload == "c1"
    assert env.callback_token is None


def test_card_action_unknown_value_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["cardAction"](
        _card_action(action=SimpleNamespace(value={"unrelated": True}))
    )
    assert _poll_all(adapter) == []


def test_card_action_from_unauthorized_operator_is_dropped():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["cardAction"](
        _card_action(operator=SimpleNamespace(open_id="ou_999"))
    )
    assert _poll_all(adapter) == []


def test_poll_once_times_out_empty_without_events():
    adapter = _adapter(FakeChannel())
    assert adapter.poll_once(timeout_seconds=0) == []


def test_pending_cursor_is_none():
    assert _adapter(FakeChannel()).pending_cursor() is None


def test_transport_thread_death_raises_from_poll():
    adapter = _adapter(FakeChannel())
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()
    adapter._thread = dead
    with pytest.raises(RuntimeError, match="not running"):
        adapter.poll_once(timeout_seconds=0)


def test_policy_rejection_is_logged_and_never_enqueued():
    """SDK policy rejections (unallowed sender/chat, missing mention) must
    surface in the operator log with the raw ids (T073) and never reach the
    dispatch queue."""
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.handlers["reject"](
        SimpleNamespace(
            message_id="om_1",
            chat_id="oc_group_1",
            sender_id="ou_999",
            reason="sender_not_allowed",
        )
    )
    assert adapter.poll_once(timeout_seconds=0) == []


def test_send_text_uses_sdk_send():
    channel = FakeChannel()
    adapter = _adapter(channel)
    adapter.send_text("oc_group_1", "hello there")
    assert channel.sent == [("oc_group_1", {"text": "hello there"}, None)]


def test_send_document_sends_caption_then_file(tmp_path: Path):
    channel = FakeChannel()
    adapter = _adapter(channel)
    target = tmp_path / "report.md"
    target.write_text("# report", encoding="utf-8")
    adapter.send_document("oc_group_1", target, caption="here you go")
    assert [message for _, message, _ in channel.sent] == [
        {"text": "here you go"},
        {"file": {"source": str(target), "fileName": "report.md"}},
    ]


def test_send_approval_card_has_framed_buttons():
    channel = FakeChannel()
    adapter = _adapter(channel)
    adapter.send_approval("oc_group_1", text="⚠️ Approval required", approve_token="tok-1")
    (_, message, _) = channel.sent[0]
    actions = [e for e in message["card"]["elements"] if e.get("tag") == "action"]
    buttons = actions[0]["actions"]
    assert buttons[0]["value"] == {"callback_data": "zg:tok-1:a"}
    assert buttons[1]["value"] == {"callback_data": "zg:tok-1:d"}
    assert buttons[0]["text"]["content"] == "Approve"
    assert buttons[1]["text"]["content"] == "Deny"


def test_send_keyboard_one_button_per_row():
    channel = FakeChannel()
    adapter = _adapter(channel)
    adapter.send_keyboard(
        "oc_group_1",
        text="Case binding",
        buttons=[("Bind alpha", "zc:bind:alpha"), ("Cases", "zc:cases:")],
    )
    (_, message, _) = channel.sent[0]
    rows = [e for e in message["card"]["elements"] if e.get("tag") == "action"]
    assert len(rows) == 2
    assert rows[0]["actions"][0]["value"] == {"callback_data": "zc:bind:alpha"}
    assert rows[1]["actions"][0]["value"] == {"callback_data": "zc:cases:"}


def test_send_failure_is_logged_not_raised():
    channel = FakeChannel()
    adapter = _adapter(channel)
    channel.fail_next_send = True
    adapter.send_text("oc_group_1", "will fail")  # must not raise


def test_probe_raises_when_channel_never_connects():
    channel = FakeChannel()
    channel.connect_hangs = True
    adapter = _adapter(channel, connect_timeout=0.2)
    with pytest.raises(RuntimeError, match="not ready"):
        adapter.probe()


def test_probe_starts_transport_and_reports_ready():
    channel = FakeChannel()
    adapter = _adapter(channel)
    assert adapter.probe() == {"ready": True}
    assert channel.connected
    adapter.close()
    assert channel.stopped


def test_real_channel_construction_wires_policy_and_security():
    """No injected channel: the adapter must build a real offline
    ``FeishuChannel`` (constructor does no network) with the admission
    policy and security mode actually applied. Regression: __init__ once
    failed to store security_mode/domain, which only the real construction
    path touched — the injected-channel tests never saw it."""
    from lark_channel import FeishuChannel

    adapter = _adapter(None)  # type: ignore[arg-type]

    assert isinstance(adapter._channel, FeishuChannel)
    policy = adapter._channel.get_policy()
    assert policy.dm_policy == "allowlist"
    assert policy.group_policy == "allowlist"
    assert policy.allow_from == ["ou_1"]
    assert policy.group_allowlist == ["oc_group_1"]
    assert policy.require_mention is True
