"""Stage 8 local end-to-end proof — SPEC v0.3 §Stage 8.

The complete vertical slice with mocked Telegram and mocked WordPress, but
the REAL runtime, profile composition, PydanticAI native approval,
PauseReceipt, shared resume and RunReceipt:

Telegram InboundEnvelope → GatewayService → wordpress-operator profile →
build_profile_agent → execute_run → wordpress_publish_post → PausedRun →
opaque approval token → Approve callback → resume_paused_run → WordPress
REST write → verified tool effect → RunReceipt.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import zuaef_wordpress
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_wordpress.client import WordPressClient
from zuaef_wordpress.toolset import make_toolset

from zuaef_agent import core as core_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore
from zuaef_agent.plugin_api import PluginBundle

models.ALLOW_MODEL_REQUESTS = False


class FakeWordPress:
    """Minimal mock WordPress REST for the E2E slice."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.posts: dict[int, dict] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if "/posts/" in request.url.path and request.method == "POST":
            post_id = int(request.url.path.rsplit("/", 1)[-1])
            body = json.loads(request.content)
            post = dict(self.posts.get(post_id, {"id": post_id}))
            post.update({"id": post_id, "status": body.get("status"), "link": f"https://wp.example/?p={post_id}", "modified": "2026-01-02T00:00:00"})
            self.posts[post_id] = post
            return httpx.Response(200, json=post)
        return httpx.Response(404, json={"message": "not found"})


class FakeSurface:
    surface_name = "telegram"

    def __init__(self):
        self.texts: list[str] = []
        self.approvals: list[dict] = []
        self.callback_answers: list[tuple[str, str]] = []

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id: str, text: str) -> None:
        self.texts.append(text)

    def send_document(self, channel_id, path, *, caption=None) -> None:
        pass

    def send_approval(
        self, channel_id, *, text, approve_token, approve_label="Approve", deny_label="Deny"
    ) -> None:
        self.approvals.append({"text": text, "token": approve_token})

    def send_keyboard(self, channel_id, *, text, buttons) -> None:
        self.texts.append(text)

    def answer_callback(self, callback_id: str, text: str) -> None:
        self.callback_answers.append((callback_id, text))

    def last_text(self) -> str:
        return "".join(self.texts)


PROFILE = 'schema = 1\nname = "wordpress-operator"\n\n[[plugins]]\nid = "wordpress"\n\n[plugins.config]\nsite_url = "https://wp.example"\n'


@pytest.fixture
def world(tmp_path: Path, monkeypatch):
    fake_wp = FakeWordPress()
    fake_wp.posts[5] = {"id": 5, "status": "draft", "link": "https://wp.example/?p=5"}
    client = WordPressClient(
        site_url="https://wp.example",
        username="operator",
        app_password="app-pass",
        transport=httpx.MockTransport(fake_wp.handler),
    )

    monkeypatch.setattr(
        zuaef_wordpress,
        "create_plugin",
        lambda env, config: PluginBundle(toolsets=[make_toolset(client)]),
    )

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "wordpress-operator.toml").write_text(
        PROFILE, encoding="utf-8"
    )

    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    surface = FakeSurface()

    def model_fn(messages, info):
        has_return = any(
            getattr(part, "part_kind", None) == "tool-return"
            for message in messages
            for part in getattr(message, "parts", [])
        )
        if not has_return:
            return ModelResponse(
                parts=[ToolCallPart("wordpress_publish_post", {"post_id": 5})]
            )
        return ModelResponse(parts=[TextPart(content="WordPress post published.")])

    monkeypatch.setattr(
        core_module, "resolve_model", lambda s: FunctionModel(model_fn)
    )
    service = GatewayService(
        settings=settings,
        store=store,
        surface=surface,
        default_profile="wordpress-operator",
        config_root=config_root,
    )
    return {
        "settings": settings,
        "store": store,
        "surface": surface,
        "service": service,
        "fake_wp": fake_wp,
    }


def _envelope(text: str, n: int = 1, **overrides) -> InboundEnvelope:
    base = {
        "surface": "telegram",
        "user_id": "42",
        "channel_id": "42",
        "message_id": f"m-{n}",
        "text": text,
    }
    base.update(overrides)
    return InboundEnvelope(**base)


def test_full_publish_slice_through_gateway(world):
    service: GatewayService = world["service"]
    store: GatewayStore = world["store"]
    surface: FakeSurface = world["surface"]
    fake_wp: FakeWordPress = world["fake_wp"]

    # 1. Telegram task arrives.
    service.handle(_envelope("Publish WordPress draft 5.", n=1))

    session = store.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )
    assert session.paused_run_id, "external write must pause"
    paused_run_id = session.paused_run_id
    assert session.profile == "wordpress-operator"
    assert len(surface.approvals) == 1
    assert "wordpress_publish_post" in surface.approvals[0]["text"]
    assert fake_wp.requests == [], "no WordPress call before approval"

    pause_receipt = service.receipts.read(paused_run_id)
    assert pause_receipt.state == "paused"
    assert pause_receipt.composition.profile == "wordpress-operator"
    assert pause_receipt.pending_approvals[0]["tool_name"] == "wordpress_publish_post"
    composition_id = pause_receipt.composition.composition_id
    conversation_id = session.conversation_id

    # 2. Human taps Approve; the opaque token authorizes the resume.
    token = surface.approvals[0]["token"]
    service.handle(
        _envelope(
            "",
            n=2,
            callback_token=token,
            callback_action="approve",
            transport_context={"callback_query_id": "cb-1"},
        )
    )

    # 3. WordPress REST write executed exactly once, then verified.
    assert len(fake_wp.requests) == 1
    assert json.loads(fake_wp.requests[0].content) == {"status": "publish"}

    session = store.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )
    assert session.paused_run_id is None
    assert session.last_terminal_run_id

    receipt = service.receipts.read(session.last_terminal_run_id)
    assert receipt.state == "terminal"
    assert receipt.continued_from_run_id == paused_run_id
    assert receipt.conversation_id == conversation_id
    assert receipt.composition.composition_id == composition_id
    assert receipt.status == "completed"
    effects = [e for e in receipt.verified_tool_effects if e.tool_name == "wordpress_publish_post"]
    assert len(effects) == 1 and effects[0].status == "completed"
    assert "✅ Completed" in surface.last_text()
    assert surface.callback_answers == [("cb-1", "Approved. Resuming…")]


def test_deny_never_touches_wordpress(world):
    service: GatewayService = world["service"]
    store: GatewayStore = world["store"]
    surface: FakeSurface = world["surface"]
    fake_wp: FakeWordPress = world["fake_wp"]

    service.handle(_envelope("Publish WordPress draft 5.", n=1))
    token = surface.approvals[0]["token"]
    service.handle(
        _envelope("", n=2, callback_token=token, callback_action="deny")
    )

    assert fake_wp.requests == [], "denied write must never execute"
    session = store.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )
    receipt = service.receipts.read(session.last_terminal_run_id)
    assert not [
        e for e in receipt.verified_tool_effects if e.status == "completed"
    ]
