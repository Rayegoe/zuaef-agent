"""Telegram transport tests — SPEC v0.3 §75. All network is mocked via httpx."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from zuaef_agent.gateway.telegram import TelegramAdapter, redact_token


class FakeBot:
    """Stateful mock of the Telegram Bot HTTP API over httpx.MockTransport."""

    def __init__(self, updates: list[dict], file_contents: dict[str, bytes] | None = None):
        self.updates = updates
        self.file_contents = file_contents or {}
        self.calls: list[tuple[str, dict]] = []  # (method, payload)
        self.get_updates_payloads: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/file/bot" in url:
            match = re.search(r"/file/bot[^/]+/(.*)", url)
            path = match.group(1) if match else ""
            if path in self.file_contents:
                return httpx.Response(200, content=self.file_contents[path])
            return httpx.Response(404, json={"ok": False, "description": "missing"})
        method = url.rsplit("/", 1)[-1]
        payload: dict = dict(request.url.params)
        if request.content:
            try:
                payload.update(json.loads(request.content.decode()))
            except ValueError:
                pass
        if method == "getUpdates":
            self.get_updates_payloads.append(payload)
            return httpx.Response(200, json={"ok": True, "result": self.updates})
        if method == "getMe":
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 1, "username": "zuaef_bot"}},
            )
        if method == "getFile":
            file_id = payload.get("file_id", "")
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": f"docs/{file_id}.bin"}}
            )
        if method == "sendMessage":
            self.calls.append(("sendMessage", payload))
            return httpx.Response(200, json={"ok": True, "result": {}})
        if method == "sendDocument":
            self.calls.append(("sendDocument", {"raw": request.content}))
            return httpx.Response(200, json={"ok": True, "result": {}})
        if method == "answerCallbackQuery":
            self.calls.append(("answerCallbackQuery", payload))
            return httpx.Response(200, json={"ok": True, "result": {}})
        return httpx.Response(200, json={"ok": True, "result": {}})


def _adapter(tmp_path: Path, bot: FakeBot) -> TelegramAdapter:
    client = httpx.Client(transport=httpx.MockTransport(bot.handler))
    return TelegramAdapter(
        token="123456:TEST-TOKEN",
        allowed_user_ids={"42"},
        workspace_root=tmp_path,
        http_client=client,
    )


def _text_update(update_id: int, text: str, user_id: str = "42") -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": 100 + update_id,
            "from": {"id": int(user_id)},
            "chat": {"id": int(user_id), "type": "private"},
            "text": text,
        },
    }


def test_get_updates_text_message_normalization(tmp_path: Path):
    bot = FakeBot([_text_update(7, "check post 123")])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert len(events) == 1
    env = events[0]
    assert env.surface == "telegram"
    assert env.user_id == "42"
    assert env.channel_id == "42"
    assert env.message_id == "107"
    assert env.text == "check post 123"
    assert env.attachments == []


def test_document_download_to_workspace_inbox(tmp_path: Path):
    update = {
        "update_id": 3,
        "message": {
            "message_id": 55,
            "from": {"id": 42},
            "chat": {"id": 42, "type": "private"},
            "caption": "analyze this budget",
            "document": {
                "file_id": "doc-1",
                "file_name": "budget.csv",
                "mime_type": "text/csv",
                "file_size": 12,
            },
        },
    }
    bot = FakeBot([update], {"docs/doc-1.bin": b"a,b,c\n1,2,3\n"})
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert len(events) == 1
    env = events[0]
    assert env.text == "analyze this budget"
    assert len(env.attachments) == 1
    ref = env.attachments[0]
    assert ref.kind == "document"
    assert ref.original_name == "budget.csv"
    assert ref.local_path.startswith("inbox/telegram/")
    assert not ref.local_path.startswith("/")
    assert ref.size == 12
    stored = tmp_path / ref.local_path
    assert stored.read_bytes() == b"a,b,c\n1,2,3\n"


def test_document_path_traversal_name_is_sanitized(tmp_path: Path):
    update = {
        "update_id": 3,
        "message": {
            "message_id": 55,
            "from": {"id": 42},
            "chat": {"id": 42, "type": "private"},
            "document": {
                "file_id": "doc-1",
                "file_name": "../../evil.sh",
                "file_size": 3,
            },
        },
    }
    bot = FakeBot([update], {"docs/doc-1.bin": b"x"})
    adapter = _adapter(tmp_path, bot)
    events = adapter.poll_once(timeout_seconds=0)
    ref = events[0].attachments[0]
    assert ".." not in ref.local_path
    assert ref.local_path.endswith("-evil.sh")
    assert (tmp_path / ref.local_path).is_file()


def test_oversized_document_rejected_before_download(tmp_path: Path):
    update = {
        "update_id": 3,
        "message": {
            "message_id": 55,
            "from": {"id": 42},
            "chat": {"id": 42, "type": "private"},
            "document": {"file_id": "doc-1", "file_name": "big.bin", "file_size": 10**9},
        },
    }
    bot = FakeBot([update])
    adapter = _adapter(tmp_path, bot)
    adapter.max_upload_bytes = 1024

    events = adapter.poll_once(timeout_seconds=0)

    assert events[0].attachments == []
    assert any(
        call[0] == "sendMessage" and "Attachment rejected" in call[1]["text"]
        for call in bot.calls
    )


def test_callback_query_normalization(tmp_path: Path):
    update = {
        "update_id": 9,
        "callback_query": {
            "id": "cb-9",
            "from": {"id": 42},
            "message": {"chat": {"id": 42, "type": "private"}},
            "data": "zg:opaque-token:a",
        },
    }
    bot = FakeBot([update])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert len(events) == 1
    env = events[0]
    assert env.callback_token == "opaque-token"
    assert env.callback_action == "approve"
    assert env.transport_context["callback_query_id"] == "cb-9"


def test_callback_deny_action(tmp_path: Path):
    update = {
        "update_id": 9,
        "callback_query": {
            "id": "cb-9",
            "from": {"id": 42},
            "message": {"chat": {"id": 42, "type": "private"}},
            "data": "zg:tok:d",
        },
    }
    bot = FakeBot([update])
    adapter = _adapter(tmp_path, bot)
    events = adapter.poll_once(timeout_seconds=0)
    assert events[0].callback_action == "deny"


def _control_update(data: str) -> dict:
    return {
        "update_id": 11,
        "callback_query": {
            "id": "cb-11",
            "from": {"id": 42},
            "message": {"chat": {"id": 42, "type": "private"}},
            "data": data,
        },
    }


def test_control_callback_bind_normalization(tmp_path: Path):
    bot = FakeBot([_control_update("zc:bind:stillevo-beauty")])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert len(events) == 1
    env = events[0]
    assert env.callback_action == "bind"
    assert env.callback_payload == "stillevo-beauty"
    assert env.callback_token is None
    assert env.transport_context["callback_query_id"] == "cb-11"


def test_control_callback_bare_actions_normalize(tmp_path: Path):
    bot = FakeBot([_control_update(f"zc:{action}:") for action in ("unbind", "cases", "new")])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert [e.callback_action for e in events] == ["unbind", "cases", "new"]
    assert all(e.callback_payload is None for e in events)


def test_control_callback_unknown_action_answered_and_dropped(tmp_path: Path):
    bot = FakeBot([_control_update("zc:explode:x"), _control_update("zz:bind:a")])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert events == []
    answered = [call for call in bot.calls if call[0] == "answerCallbackQuery"]
    assert len(answered) == 2
    assert all(call[1]["text"] == "Unknown action." for call in answered)


def test_control_callback_unauthorized_user_dropped(tmp_path: Path):
    update = _control_update("zc:bind:stillevo-beauty")
    update["callback_query"]["from"]["id"] = 999
    bot = FakeBot([update])
    adapter = _adapter(tmp_path, bot)

    events = adapter.poll_once(timeout_seconds=0)

    assert events == []


def test_send_keyboard_posts_one_button_per_row(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    adapter.send_keyboard(
        "42",
        text="Case binding",
        buttons=[("Bind alpha", "zc:bind:alpha"), ("Cases", "zc:cases:")],
    )
    sent = next(call for call in bot.calls if call[0] == "sendMessage")
    keyboard = sent[1]["reply_markup"]["inline_keyboard"]
    assert keyboard == [
        [{"text": "Bind alpha", "callback_data": "zc:bind:alpha"}],
        [{"text": "Cases", "callback_data": "zc:cases:"}],
    ]
    assert sent[1]["text"] == "Case binding"


def test_cursor_advances_across_batch(tmp_path: Path):
    bot = FakeBot([_text_update(7, "first"), _text_update(8, "second")])
    adapter = _adapter(tmp_path, bot)

    first = adapter.poll_once(timeout_seconds=0)
    assert [e.text for e in first] == ["first", "second"]
    assert adapter.pending_cursor() == "9"


def test_second_poll_sends_offset(tmp_path: Path):
    bot = FakeBot([_text_update(4, "hello")])
    adapter = _adapter(tmp_path, bot)
    adapter.poll_once(timeout_seconds=0)
    assert bot.get_updates_payloads[0].get("offset") is None

    bot.updates = []
    adapter.poll_once(timeout_seconds=0)
    assert bot.get_updates_payloads[1]["offset"] == 5


def test_unauthorized_user_ignored(tmp_path: Path):
    bot = FakeBot([_text_update(1, "hack", user_id="999")])
    adapter = _adapter(tmp_path, bot)
    events = adapter.poll_once(timeout_seconds=0)
    assert events == []


def test_group_chat_refused_no_envelope(tmp_path: Path):
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "from": {"id": 42},
            "chat": {"id": -100123, "type": "supergroup"},
            "text": "hi",
        },
    }
    bot = FakeBot([update])
    adapter = _adapter(tmp_path, bot)
    events = adapter.poll_once(timeout_seconds=0)
    assert events == []
    assert any(
        call[0] == "sendMessage" and "Group chats" in call[1]["text"]
        for call in bot.calls
    )


def test_send_text(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    adapter.send_text("42", "hello")
    assert any(
        call[0] == "sendMessage" and call[1]["chat_id"] == "42" for call in bot.calls
    )


def test_send_document(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    target = tmp_path / "report.md"
    target.write_text("# report", encoding="utf-8")
    adapter.send_document("42", target, caption="here you go")
    sent = next(call for call in bot.calls if call[0] == "sendDocument")
    body = sent[1]["raw"].decode()
    assert 'name="chat_id"' in body and "42" in body
    assert 'name="caption"' in body and "here you go" in body
    assert "report.md" in body


def test_send_approval_keyboard(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    adapter.send_approval("42", text="⚠️ Approval required", approve_token="tok-1")
    sent = next(call for call in bot.calls if call[0] == "sendMessage")
    keyboard = sent[1]["reply_markup"]["inline_keyboard"]
    assert keyboard[0][0]["callback_data"] == "zg:tok-1:a"
    assert keyboard[0][1]["callback_data"] == "zg:tok-1:d"


def test_answer_callback(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    adapter.answer_callback("cb-1", "Approved.")
    assert any(
        call[0] == "answerCallbackQuery"
        and call[1]["callback_query_id"] == "cb-1"
        for call in bot.calls
    )


def test_error_rendering_redacts_bot_token(tmp_path: Path):
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "ok": False,
                "description": "https://api.telegram.org/bot123456:TEST-TOKEN/getUpdates failed",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(failing))
    adapter = TelegramAdapter(
        token="123456:TEST-TOKEN",
        allowed_user_ids={"42"},
        workspace_root=tmp_path,
        http_client=client,
    )
    with pytest.raises(httpx.HTTPError) as exc:
        adapter.poll_once(timeout_seconds=0)
    assert "123456:TEST-TOKEN" not in str(exc.value)
    assert "/bot***/" in str(exc.value)


def test_redact_token_helper():
    assert redact_token("x/bot123:ABC/y") == "x/bot***/y"
    assert redact_token("no token here") == "no token here"


def test_get_me_probe(tmp_path: Path):
    bot = FakeBot([])
    adapter = _adapter(tmp_path, bot)
    result = adapter.probe()
    assert result["username"] == "zuaef_bot"
