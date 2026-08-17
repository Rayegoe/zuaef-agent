"""GatewayStore tests — SPEC v0.3 §74."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from zuaef_agent.gateway.store import ApprovalTokenError, GatewayStore


@pytest.fixture
def store(tmp_path: Path) -> GatewayStore:
    return GatewayStore(tmp_path / "gateway.sqlite3")


def _key(**overrides):
    base = {
        "surface": "telegram",
        "tenant_id": "default",
        "user_id": "42",
        "channel_id": "42",
        "thread_id": None,
        "default_profile": "wordpress-operator",
    }
    base.update(overrides)
    return base


def _get_key(**overrides):
    key = _key(**overrides)
    key.pop("default_profile", None)
    return key


def test_create_and_get_session(store: GatewayStore):
    binding = store.get_or_create_session(**_key())
    assert binding.conversation_id
    assert binding.profile == "wordpress-operator"
    assert binding.thread_key == ""

    again = store.get_or_create_session(**_key())
    assert again.conversation_id == binding.conversation_id
    assert again == binding


def test_same_chat_same_conversation_different_chat_different(store: GatewayStore):
    a = store.get_or_create_session(**_key())
    b = store.get_or_create_session(**_key(channel_id="43"))
    assert a.conversation_id != b.conversation_id
    c = store.get_or_create_session(**_key(thread_id="thread-7"))
    assert c.thread_key == "thread-7"
    assert c.conversation_id != a.conversation_id


def test_reset_session_new_conversation_id_clears_runs(store: GatewayStore):
    binding = store.get_or_create_session(**_key())
    paused = binding.model_copy(update={"paused_run_id": "run-1", "active_run_id": None})
    store.save_session(paused)

    reset = store.reset_session(paused)
    assert reset.conversation_id != paused.conversation_id
    assert reset.paused_run_id is None
    assert reset.last_terminal_run_id is None
    assert reset.profile == paused.profile

    reloaded = store.get_session(**_get_key())
    assert reloaded == reset


def test_profile_persists(store: GatewayStore):
    binding = store.get_or_create_session(**_key(default_profile=None))
    assert binding.profile is None
    binding = binding.model_copy(update={"profile": "ace-writing"})
    store.save_session(binding)
    reloaded = store.get_session(**_get_key())
    assert reloaded.profile == "ace-writing"


def test_cursor_persists(store: GatewayStore):
    assert store.get_cursor("telegram") is None
    store.set_cursor("telegram", "100")
    assert store.get_cursor("telegram") == "100"
    store.set_cursor("telegram", "105")
    assert store.get_cursor("telegram") == "105"
    assert store.get_cursor("feishu") is None


def test_approval_token_raw_value_not_stored(store: GatewayStore, tmp_path: Path):
    session = store.get_or_create_session(**_key())
    raw = store.create_approval(session=session, paused_run_id="run-1", ttl_seconds=60)
    assert raw
    db_text = (tmp_path / "gateway.sqlite3").read_text(errors="replace")
    assert raw not in db_text
    binding = store.resolve_approval(raw)
    assert binding is not None
    assert binding.state == "pending"
    assert binding.paused_run_id == "run-1"
    assert binding.token_hash != raw


def test_approval_resolve_unknown_token(store: GatewayStore):
    assert store.resolve_approval("not-a-real-token") is None


def test_approval_consume_transitions_once(store: GatewayStore):
    session = store.get_or_create_session(**_key())
    raw = store.create_approval(session=session, paused_run_id="run-1", ttl_seconds=60)
    consumed = store.consume_approval(raw, decision="approved")
    assert consumed.state == "approved"
    assert consumed.consumed_at is not None
    with pytest.raises(ApprovalTokenError, match="already approved"):
        store.consume_approval(raw, decision="approved")


def test_expired_token_rejected(store: GatewayStore):
    session = store.get_or_create_session(**_key())
    raw = store.create_approval(session=session, paused_run_id="run-1", ttl_seconds=-1)
    binding = store.resolve_approval(raw)
    assert binding is not None
    assert binding.state == "expired"
    with pytest.raises(ApprovalTokenError, match="expired"):
        store.consume_approval(raw, decision="approved")


def test_different_user_cannot_use_token(store: GatewayStore):
    session = store.get_or_create_session(**_key())
    raw = store.create_approval(session=session, paused_run_id="run-1", ttl_seconds=60)
    with pytest.raises(ApprovalTokenError, match="another user"):
        store.consume_approval(raw, decision="approved", user_id="99")
    with pytest.raises(ApprovalTokenError, match="another channel"):
        store.consume_approval(raw, decision="approved", channel_id="99")
    # token is still pending and consumable by the right user/channel
    ok = store.consume_approval(
        raw, decision="denied", user_id="42", channel_id="42"
    )
    assert ok.state == "denied"


def test_reset_expires_pending_tokens_for_paused_run(store: GatewayStore):
    session = store.get_or_create_session(**_key())
    raw = store.create_approval(session=session, paused_run_id="run-1", ttl_seconds=60)
    paused = session.model_copy(update={"paused_run_id": "run-1"})
    store.reset_session(paused)
    binding = store.resolve_approval(raw)
    assert binding is not None
    assert binding.state == "expired"
    with pytest.raises(ApprovalTokenError, match="expired"):
        store.consume_approval(raw, decision="approved")


def test_schema_user_version(store: GatewayStore, tmp_path: Path):
    conn = sqlite3.connect(str(tmp_path / "gateway.sqlite3"))
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert version == 1


def test_list_sessions_and_missing_session(store: GatewayStore):
    assert store.list_sessions() == []
    store.get_or_create_session(**_key())
    store.get_or_create_session(**_key(channel_id="43"))
    assert len(store.list_sessions()) == 2
    assert store.get_session(**_get_key(channel_id="44")) is None


def test_thread_id_none_normalizes_to_empty_key(store: GatewayStore):
    a = store.get_or_create_session(**_key(thread_id=None))
    b = store.get_or_create_session(**_key(thread_id=""))
    assert a.conversation_id == b.conversation_id
