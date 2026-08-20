"""WordPress plugin tests — SPEC v0.3 §79. WordPress REST is mocked via httpx."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic_ai import RunContext, RunUsage, models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_wordpress import create_plugin
from zuaef_wordpress.client import WordPressClient, WordPressError
from zuaef_wordpress.toolset import make_toolset

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv
from zuaef_agent.runtime import PausedRun, TerminalRun, execute_run

models.ALLOW_MODEL_REQUESTS = False


# ── helpers ─────────────────────────────────────────────────────────────────


class FakeWordPress:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.posts: dict[int, dict] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        method, path = request.method, request.url.path
        if path.endswith("/posts") and method == "POST":
            body = json.loads(request.content)
            post_id = max(self.posts, default=0) + 1
            post = {
                "id": post_id,
                "status": body.get("status", "draft"),
                "slug": f"post-{post_id}",
                "link": f"https://wp.example/?p={post_id}",
                "title": {"rendered": body.get("title", "")},
                "modified": "2026-01-01T00:00:00",
            }
            self.posts[post_id] = post
            return httpx.Response(200, json=post)
        if path.endswith("/posts") and method == "GET":
            return httpx.Response(200, json=list(self.posts.values()))
        if "/posts/" in path:
            post_id = int(path.rsplit("/", 1)[-1])
            post = self.posts.get(post_id)
            if post is None:
                return httpx.Response(
                    404,
                    json={"code": "rest_post_invalid_id", "message": "Invalid post ID."},
                )
            if method == "POST":
                body = json.loads(request.content)
                if "status" in body:
                    post["status"] = body["status"]
                post["modified"] = "2026-01-02T00:00:00"
                return httpx.Response(200, json=post)
            return httpx.Response(200, json=post)
        return httpx.Response(500, json={"message": "boom"})


def _client(fake: FakeWordPress) -> WordPressClient:
    return WordPressClient(
        site_url="https://wp.example",
        username="operator",
        app_password="app-pass",
        transport=httpx.MockTransport(fake.handler),
    )


def _env(monkeypatch):
    monkeypatch.setenv("ZUAEF_WORDPRESS_USERNAME", "operator")
    monkeypatch.setenv("ZUAEF_WORDPRESS_APP_PASSWORD", "app-pass")


def _plugin_env(tmp_path: Path) -> PluginEnv:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return PluginEnv(
        plugin_id="wordpress",
        plugin_version="0.1.0",
        workspace_root=workspace,
        state_root=tmp_path / ".zuaef-state",
    )


def _tool_names(bundle) -> set[str]:
    import asyncio

    ctx = RunContext(
        deps=CoreDeps(workspace_root=Path("/tmp"), run_id=""),
        usage=RunUsage(),
        prompt="",
        model=None,
    )
    names: set[str] = set()
    for toolset in bundle.toolsets:
        names |= set(asyncio.run(toolset.get_tools(ctx)))
    return names


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


def _final():
    return ModelResponse(parts=[TextPart(content="done")])


def _has_tool_return(messages) -> bool:
    return any(
        getattr(part, "part_kind", None) == "tool-return"
        for message in messages
        for part in getattr(message, "parts", [])
    )


def _run_with(fake: FakeWordPress, tmp_path: Path, tool: str, args: dict):
    settings = _settings(tmp_path)
    agent = build_agent(
        settings, run_id="wprun", extra_toolsets=[make_toolset(_client(fake))]
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id="wprun")

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(parts=[ToolCallPart(tool, args)])
        return _final()

    with agent.override(model=FunctionModel(fn)):
        return execute_run(
            agent, deps, prompt="go", settings=settings, run_id="wprun"
        )


# ── factory ─────────────────────────────────────────────────────────────────


def test_factory_returns_bundle_with_exact_tool_names(tmp_path: Path, monkeypatch):
    _env(monkeypatch)
    bundle = create_plugin(
        _plugin_env(tmp_path), {"site_url": "https://wp.example", "site_label": "prod"}
    )
    assert _tool_names(bundle) == {
        "wordpress_get_post",
        "wordpress_create_draft",
        "wordpress_update_post",
        "wordpress_publish_post",
    }


def test_factory_fails_loud_without_credentials(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ZUAEF_WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("ZUAEF_WORDPRESS_APP_PASSWORD", raising=False)
    with pytest.raises(CompositionError, match="credentials missing"):
        create_plugin(_plugin_env(tmp_path), {"site_url": "https://wp.example"})


def test_factory_fails_loud_without_site_url(tmp_path: Path, monkeypatch):
    _env(monkeypatch)
    with pytest.raises(CompositionError, match="site_url"):
        create_plugin(_plugin_env(tmp_path), {})


# ── client behavior ─────────────────────────────────────────────────────────


def test_get_post_returns_bounded_read_fields():
    fake = FakeWordPress()
    fake.posts[123] = {
        "id": 123,
        "status": "draft",
        "slug": "hello",
        "link": "https://wp.example/?p=123",
        "title": {"rendered": "Hello"},
        "modified": "2026-01-01T00:00:00",
        "content": {"rendered": "<p>FULL HTML</p>"},
        "_embedded": {"author": [{"name": "x"}]},
    }
    result = _client(fake).get_post(123)
    assert result == {
        "id": 123,
        "status": "draft",
        "slug": "hello",
        "link": "https://wp.example/?p=123",
        "title": "Hello",
        "modified": "2026-01-01T00:00:00",
    }
    assert "content" not in result and "_embedded" not in result


def test_create_draft_posts_draft_and_bounds_response():
    fake = FakeWordPress()
    result = _client(fake).create_draft(title="T", content="body")
    sent = json.loads(fake.requests[0].content)
    assert sent["status"] == "draft"
    assert set(result) == {"id", "status", "link", "modified"}
    assert result["status"] == "draft"


def test_publish_post_sends_status_publish():
    fake = FakeWordPress()
    fake.posts[7] = {"id": 7, "status": "draft", "link": "https://wp.example/?p=7"}
    result = _client(fake).publish_post(7)
    sent = json.loads(fake.requests[0].content)
    assert sent == {"status": "publish"}
    assert result["status"] == "publish"


def test_update_post_sends_only_provided_fields():
    fake = FakeWordPress()
    fake.posts[7] = {"id": 7, "status": "draft", "link": "https://wp.example/?p=7"}
    _client(fake).update_post(7, title="New")
    sent = json.loads(fake.requests[0].content)
    assert sent == {"title": "New"}


def test_update_post_without_fields_fails_loud():
    fake = FakeWordPress()
    with pytest.raises(WordPressError, match="at least one field"):
        _client(fake).update_post(7)


def test_http_404_fails_loud():
    fake = FakeWordPress()
    with pytest.raises(WordPressError, match="404"):
        _client(fake).get_post(999)


def test_http_500_fails_loud():
    def boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    client = WordPressClient(
        site_url="https://wp.example",
        username="u",
        app_password="p",
        transport=httpx.MockTransport(boom),
    )
    with pytest.raises(WordPressError, match="500"):
        client.get_post(1)


def test_timeout_fails_loud(tmp_path: Path):
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = WordPressClient(
        site_url="https://wp.example",
        username="u",
        app_password="p",
        transport=httpx.MockTransport(slow),
    )
    with pytest.raises(WordPressError, match="timed out"):
        client.get_post(1)


def test_network_error_fails_loud(tmp_path: Path):
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = WordPressClient(
        site_url="https://wp.example",
        username="u",
        app_password="p",
        transport=httpx.MockTransport(broken),
    )
    with pytest.raises(WordPressError, match="request failed"):
        client.get_post(1)


def test_secrets_never_returned(tmp_path: Path):
    fake = FakeWordPress()
    fake.posts[1] = {
        "id": 1,
        "status": "publish",
        "link": "https://wp.example/?p=1",
        "password": "hunter2",
        "author": {"token": "secret-token"},
    }
    result = json.dumps(_client(fake).get_post(1))
    assert "hunter2" not in result
    assert "secret-token" not in result


# ── native approval behavior ────────────────────────────────────────────────


def test_get_post_is_observation_and_does_not_pause(tmp_path: Path):
    fake = FakeWordPress()
    fake.posts[123] = {"id": 123, "status": "draft", "link": "https://wp.example/?p=123"}
    outcome = _run_with(fake, tmp_path, "wordpress_get_post", {"post_id": 123})
    assert isinstance(outcome, TerminalRun)
    assert len(fake.requests) == 1
    assert fake.requests[0].method == "GET"


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("wordpress_create_draft", {"title": "T", "content": "C"}),
        ("wordpress_update_post", {"post_id": 5, "title": "T"}),
        ("wordpress_publish_post", {"post_id": 5}),
    ],
)
def test_write_tools_pause_for_native_approval_before_execution(
    tmp_path: Path, tool: str, args: dict
):
    fake = FakeWordPress()
    fake.posts[5] = {"id": 5, "status": "draft", "link": "https://wp.example/?p=5"}
    outcome = _run_with(fake, tmp_path, tool, args)
    assert isinstance(outcome, PausedRun)
    assert outcome.pause_receipt.pending_approvals[0]["tool_name"] == tool
    assert fake.requests == [], "external write must not execute before approval"


def test_publish_after_approval_executes_and_settles(tmp_path: Path, monkeypatch):
    """Full native-approval proof through the REAL installed entry point:
    profile → build_profile_agent → pause → shared resume → WordPress write.
    The factory is patched to inject the mocked transport while the real
    `zuaef.plugins` entry point, composition and frozen snapshot stay."""
    import zuaef_wordpress

    from zuaef_agent.composition import build_profile_agent
    from zuaef_agent.continuation import resume_paused_run

    fake = FakeWordPress()
    fake.posts[5] = {"id": 5, "status": "draft", "link": "https://wp.example/?p=5"}
    client = _client(fake)

    def fixture_factory(env, config):
        return PluginBundle(toolsets=[make_toolset(client)])

    monkeypatch.setattr(zuaef_wordpress, "create_plugin", fixture_factory)

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "wordpress-operator.toml").write_text(
        'schema = 1\nname = "wordpress-operator"\n\n[[plugins]]\nid = "wordpress"\n\n[plugins.config]\nsite_url = "https://wp.example"\n',
        encoding="utf-8",
    )

    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="wordpress-operator",
        config_root=config_root,
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(
                parts=[ToolCallPart("wordpress_publish_post", {"post_id": 5})]
            )
        return _final()

    with agent.override(model=FunctionModel(fn)):
        paused = execute_run(
            agent,
            deps,
            prompt="publish 5",
            settings=settings,
            run_id=run_id,
            composition=snapshot,
        )
    assert isinstance(paused, PausedRun)
    assert fake.requests == [], "external write must not execute before approval"

    terminal = resume_paused_run(settings, run_id, decision="approve")
    assert isinstance(terminal, TerminalRun)
    assert len(fake.requests) == 1
    assert json.loads(fake.requests[0].content) == {"status": "publish"}
    settled = [
        e for e in terminal.receipt.tool_effect_facts
        if e.tool_name == "wordpress_publish_post"
    ]
    assert settled and settled[0].status == "completed"
