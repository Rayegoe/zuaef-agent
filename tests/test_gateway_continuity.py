"""Normal-turn Gateway multi-turn history — TASKS T010.

Proves real conversational continuity through the public persistence restore:

    session -> previous server-owned terminal run
            -> public StepStore fork_run -> message_history
            -> new run_id, same conversation_id -> Agent.run

Turn 2 must receive Turn 1's model-visible history (the FunctionModel sees the
restored prior user message), and a reset conversation (/new) must NOT leak
prior history across conversations.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness.step_persistence import FileStepStore, continue_run

from zuaef_agent import core as core_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore

models.ALLOW_MODEL_REQUESTS = False


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def _make_service(tmp_path, monkeypatch, surface, fn):
    from importlib.metadata import EntryPoint

    settings = _settings(tmp_path)
    (tmp_path / "config" / "profiles").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "profiles" / "writing.toml").write_text(
        'schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n',
        encoding="utf-8",
    )
    ep = EntryPoint(
        name="fixture-ace-writing",
        value="fixture_plugins.writing:create_plugin",
        group="zuaef.plugins",
    )
    discover = {"fixture-ace-writing": ep}
    versions = {"fixture-ace-writing": "0.2.1"}

    def _vf(e):
        return versions[e.name]

    def builder(settings, *, run_id=None, profile=None, snapshot=None, config_root=None, **_):
        from zuaef_agent.composition import build_profile_agent as real

        return real(
            settings,
            run_id=run_id,
            profile=profile,
            snapshot=snapshot,
            config_root=config_root,
            discover=lambda: discover,
            version_for=_vf,
        )

    monkeypatch.setattr(core_module, "resolve_model", lambda s: FunctionModel(fn))
    monkeypatch.setattr("zuaef_agent.gateway.bridge.build_profile_agent", builder)
    monkeypatch.setattr("zuaef_agent.continuation.build_profile_agent", builder)
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    return GatewayService(
        settings=settings,
        store=store,
        surface=surface,
        default_profile="writing",
        config_root=tmp_path / "config",
    )


class FakeSurface:
    surface_name = "telegram"

    def __init__(self):
        self.texts = []

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id, text):
        self.texts.append((channel_id, text))

    def send_document(self, channel_id, path, *, caption=None):
        self.texts.append((channel_id, f"doc:{path}"))

    def send_approval(self, channel_id, *, text, approve_token, approve_label="Approve", deny_label="Deny"):
        self.texts.append((channel_id, text))

    def send_keyboard(self, channel_id, *, text, buttons):
        self.texts.append((channel_id, text))

    def answer_callback(self, callback_id, text):
        self.texts.append((callback_id, text))


def _final():
    return ModelResponse(
        parts=[
            ToolCallPart(
                "final_result",
                {"status": "completed", "outcome": "done", "artifacts": [], "evidence": []},
            )
        ]
    )


def _envelope(text: str, n: int) -> InboundEnvelope:
    return InboundEnvelope(
        surface="telegram",
        user_id="42",
        channel_id="42",
        message_id=f"m-{n}",
        text=text,
    )


def _session(service: GatewayService):
    return service.store.get_session(
        surface="telegram", tenant_id="default", user_id="42", channel_id="42", thread_id=None
    )


def _user_text(messages) -> str:
    """All user-prompt content the model actually saw, in order."""
    return " || ".join(
        str(part.content)
        for m in messages
        for part in getattr(m, "parts", [])
        if getattr(part, "part_kind", None) == "user-prompt"
    )


def test_turn2_sees_turn1_constraint(tmp_path, monkeypatch):
    """Turn 2's model receives Turn 1's real prompt via public history restore."""
    seen_run_texts: list[str] = []

    def fn(messages, info):
        text = " ".join(
            p.content
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "user-prompt"
        )
        seen_run_texts.append(text)
        return _final()

    surface = FakeSurface()
    service = _make_service(tmp_path, monkeypatch, surface, fn)

    turn1 = "客户觉得上一篇 demo 太模板化。结合他之前给的背景和材料重写一篇。价格先不要写。"
    service.handle(_envelope(turn1, 1))

    session = _session(service)
    assert session.last_terminal_run_id is not None

    turn2 = "开头还是太像 AI。保留刚才客户背景，再改一版；其他要求不变。"
    service.handle(_envelope(turn2, 2))

    # Turn 2's model call must see Turn 1's constraint as prior context.
    turn2_seen = seen_run_texts[-1]
    assert "价格先不要写" in turn2_seen, f"turn 2 lost turn 1 context: {turn2_seen!r}"
    assert "demo 太模板化" in turn2_seen

    # Same conversation bound to two distinct server-owned runs.
    session2 = _session(service)
    assert session2.conversation_id == session.conversation_id
    assert session2.last_terminal_run_id != session.last_terminal_run_id
    receipt = service.receipts.read(session2.last_terminal_run_id)
    assert receipt.conversation_id == session2.conversation_id


def test_reset_conversation_does_not_leak_prior_history(tmp_path, monkeypatch):
    """/new mints a fresh conversation; history must not follow."""
    seen_run_texts: list[str] = []

    def fn(messages, info):
        text = " ".join(
            p.content
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "user-prompt"
        )
        seen_run_texts.append(text)
        return _final()

    surface = FakeSurface()
    service = _make_service(tmp_path, monkeypatch, surface, fn)

    service.handle(_envelope("旧会话约束：价格先不要写", 1))
    old_conversation = _session(service).conversation_id

    # /new resets the conversation.
    service.handle(_envelope("/new", 2))
    session = _session(service)
    assert session.conversation_id != old_conversation

    service.handle(_envelope("新会话：开始新任务", 3))

    # No history restore across the reset boundary.
    new_seen = seen_run_texts[-1]
    assert "价格先不要写" not in new_seen, f"history leaked across /new: {new_seen!r}"


def test_terminal_run_leaves_resumable_snapshot(tmp_path, monkeypatch):
    """T002/T010 diagnostic: a terminal Turn-1 run leaves a ``complete``
    StepPersistence snapshot and ``continue_run`` rebuilds its message history.

    This is the persistence half the Gateway restore relies on — the public
    Harness 0.20.0 API confirmation recorded in
    ``docs/gateway-continuity-trace.md`` §4. Ported from the phase-1
    gateway-history branch (e2bbe57) before the branch was cleaned up.
    """
    seen: list[str] = []

    def fn(messages, info):
        seen.append(_user_text(messages))
        return _final()

    surface = FakeSurface()
    service = _make_service(tmp_path, monkeypatch, surface, fn)
    service.handle(_envelope("Turn one: the product pitch is about a blue umbrella", 1))
    run1 = _session(service).last_terminal_run_id

    store = FileStepStore(service.settings.step_store_dir)
    records = asyncio.run(
        store.list_runs(conversation_id=_session(service).conversation_id)
    )
    assert any(r.run_id == run1 for r in records), "Turn 1 must be recorded under the conversation"

    snapshot = asyncio.run(store.latest_snapshot(run_id=run1))
    assert snapshot is not None, "Turn 1 must leave a resumable snapshot"
    assert snapshot.state == "complete", f"terminal snapshot should be complete, got {snapshot.state!r}"
    snapshot_text = " ".join(
        str(p.content)
        for m in snapshot.messages
        for p in getattr(m, "parts", [])
        if getattr(p, "part_kind", None) == "user-prompt"
    )
    assert "blue umbrella" in snapshot_text, "Turn 1's prompt must be preserved in the snapshot"

    history = asyncio.run(continue_run(store, run_id=run1))
    assert history, "continue_run must rebuild the Turn 1 history for message_history="
    assert "blue umbrella" in _user_text(history)
