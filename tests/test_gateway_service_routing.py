"""GatewayService routing-policy tests — Feishu Surface v0.1 (spec pack 07 B
gates): alias commands, profile access policy and binding precedence, driven
through the real service dispatch with the fixture plugin composition."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai.models.function import FunctionModel
from test_gateway_service import (
    PROFILE,
    FakeSurface,
    _final,
    _fixture_builder,
    _fixture_validate,
    _settings,
    _write_profile,
)

from zuaef_agent import core as core_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.routing import ProfileAccessRule, RoutingPolicy
from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore


def _recording_fn(seen: dict):
    def fn(messages, info):
        seen["model_calls"] = seen.get("model_calls", 0) + 1
        last = messages[-1]
        seen.setdefault("last_prompt", str(getattr(last, "content", last)))
        return _final(outcome="ran under profile")

    return fn


def _recording_builder(seen: dict):
    def builder(settings, **kwargs):
        seen.setdefault("profiles", []).append(kwargs.get("profile"))
        return _fixture_builder(settings, **kwargs)

    return builder


def _write_second_profile(tmp_path: Path, name: str = "research") -> None:
    text = PROFILE.replace('name = "writing"', f'name = "{name}"')
    (tmp_path / "config" / "profiles" / f"{name}.toml").write_text(
        text, encoding="utf-8"
    )


def _service(
    tmp_path: Path,
    monkeypatch,
    surface: FakeSurface,
    fn,
    routing: RoutingPolicy | None = None,
    default_profile: str | None = None,
    seen: dict | None = None,
) -> GatewayService:
    settings: AgentSettings = _settings(tmp_path)
    _write_profile(tmp_path)
    _write_second_profile(tmp_path)
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    monkeypatch.setattr(core_module, "resolve_model", lambda s: FunctionModel(fn))
    builder = _recording_builder(seen) if seen is not None else _fixture_builder
    monkeypatch.setattr("zuaef_agent.gateway.bridge.build_profile_agent", builder)
    monkeypatch.setattr(
        "zuaef_agent.continuation.build_profile_agent", _fixture_builder
    )
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.validate_profile", _fixture_validate
    )
    return GatewayService(
        settings=settings,
        store=store,
        surface=surface,
        default_profile=default_profile,
        config_root=tmp_path / "config",
        routing_policy=routing,
    )


def _envelope(text: str, n: int = 1, **overrides) -> InboundEnvelope:
    base = {
        "surface": "feishu",
        "user_id": "ou_1",
        "channel_id": "oc_group_1",
        "chat_type": "group",
        "message_id": f"om-{n}",
        "text": text,
    }
    base.update(overrides)
    return InboundEnvelope(**base)


def _session(service: GatewayService, **overrides):
    base = {
        "surface": "feishu",
        "tenant_id": "default",
        "user_id": "ou_1",
        "channel_id": "oc_group_1",
        "thread_id": None,
    }
    base.update(overrides)
    session = service.store.get_session(**base)
    assert session is not None
    return session


# ── alias commands (spec pack 07 B3) ───────────────────────────────────────


def test_alias_switches_profile_and_runs_remaining_prompt(
    tmp_path: Path, monkeypatch
):
    seen: dict = {}
    surface = FakeSurface()
    routing = RoutingPolicy(profile_aliases={"expert": "research"})
    service = _service(tmp_path, monkeypatch, surface, _recording_fn(seen), routing)

    service.handle(_envelope("/expert summarize this", n=1))

    assert _session(service).profile == "research"
    assert seen["model_calls"] == 1
    assert "summarize this" in seen["last_prompt"]
    assert "✅ Completed" in surface.last_text()


def test_alias_without_argument_only_switches_profile(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    routing = RoutingPolicy(profile_aliases={"expert": "research"})
    service = _service(tmp_path, monkeypatch, surface, _recording_fn(seen), routing)

    service.handle(_envelope("/expert", n=1))

    assert _session(service).profile == "research"
    assert seen.get("model_calls", 0) == 0
    assert "Current profile: research" in surface.last_text()


def test_unknown_command_still_errors(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _recording_fn(seen))

    service.handle(_envelope("/nosuchcmd", n=1))

    assert seen.get("model_calls", 0) == 0
    assert "unknown command" in surface.last_text()


# ── profile admission (spec pack 07 B4/B5) ─────────────────────────────────


def _group_only_routing() -> RoutingPolicy:
    return RoutingPolicy(
        profile_aliases={"expert": "research"},
        profile_access={"research": ProfileAccessRule(allowed_chat_types=("group",))},
    )


def test_alias_denied_in_dm_before_any_run(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), _group_only_routing()
    )

    service.handle(_envelope("/expert", n=1, chat_type="p2p", channel_id="oc_dm_1"))

    assert seen.get("model_calls", 0) == 0, "DM attempt must not run"
    assert "enabled only for group chats" in surface.last_text()
    assert _session(service, channel_id="oc_dm_1").profile is None, (
        "a denied profile must never be bound to the session"
    )


def test_alias_denied_in_disallowed_group(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    routing = RoutingPolicy(
        profile_aliases={"expert": "research"},
        profile_access={
            "research": ProfileAccessRule(
                allowed_chat_types=("group",), allowed_channel_ids=("oc_lab",)
            )
        },
    )
    service = _service(tmp_path, monkeypatch, surface, _recording_fn(seen), routing)

    service.handle(_envelope("/expert", n=1, channel_id="oc_other_group"))

    assert seen.get("model_calls", 0) == 0
    assert "enabled only in approved channels" in surface.last_text()


def test_group_only_profile_allowed_in_approved_group(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), _group_only_routing()
    )

    service.handle(_envelope("/expert summarize this", n=1))

    assert seen["model_calls"] == 1
    assert "✅ Completed" in surface.last_text()


def test_profile_command_denied_in_dm(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), _group_only_routing()
    )

    service.handle(_envelope("/profile research", n=1, chat_type="p2p"))

    assert seen.get("model_calls", 0) == 0
    assert "enabled only for group chats" in surface.last_text()


def test_access_policy_blocks_run_on_prebound_session(tmp_path: Path, monkeypatch):
    """A session bound before a policy change (or bound at creation) is
    re-checked at run time — the policy gate is not only a /profile gate."""
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path,
        monkeypatch,
        surface,
        _recording_fn(seen),
        _group_only_routing(),
        default_profile="research",
    )

    service.handle(_envelope("normal task", n=1, chat_type="p2p"))

    assert seen.get("model_calls", 0) == 0
    assert "enabled only for group chats" in surface.last_text()


# ── binding precedence (spec pack 07 B1/B2, spec pack 03 §2) ───────────────


def test_thread_session_inherits_chat_binding_dynamically(
    tmp_path: Path, monkeypatch
):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), seen=seen
    )

    # 1. a thread session starts without any profile (no gateway default)
    service.handle(_envelope("thread task", n=1, thread_id="th_1"))
    # 2. the chat-level session binds a profile
    service.handle(_envelope("/profile research", n=2))
    # 3. the SAME thread session now inherits the chat binding
    service.handle(_envelope("thread task again", n=3, thread_id="th_1"))

    session = _session(service, thread_id="th_1")
    assert session.profile is None, "thread binding stays unbound (dynamic)"
    assert seen["profiles"] == [None, "research"], (
        "the second thread run must inherit the chat-level binding"
    )


def test_thread_explicit_binding_wins_over_chat(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path,
        monkeypatch,
        surface,
        _recording_fn(seen),
        RoutingPolicy(group_defaults={"oc_group_1": "writing"}),
        seen=seen,
    )

    # thread binds its own profile explicitly (no run yet)
    service.handle(_envelope("/profile research", n=1, thread_id="th_1"))
    # the group default applies to a chat-level message
    service.handle(_envelope("chat task", n=2))
    # the thread's own binding wins over the group default at run time
    service.handle(_envelope("thread task", n=3, thread_id="th_1"))

    # the explicit thread binding persists; the group default is a
    # configuration fact resolved at use time, never written into the
    # session (a later config change applies to the next run)
    assert _session(service, thread_id="th_1").profile == "research"
    assert _session(service).profile is None
    assert seen["profiles"] == ["writing", "research"]


def test_group_default_applies_when_no_binding_exists(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path,
        monkeypatch,
        surface,
        _recording_fn(seen),
        RoutingPolicy(group_defaults={"oc_group_1": "writing"}),
        seen=seen,
    )

    service.handle(_envelope("hello", n=1))

    assert seen["profiles"] == ["writing"]


# ── projection of the effective profile (Feishu v0.1 live finding) ──────────


def test_projection_shows_explicit_thread_binding(tmp_path: Path, monkeypatch):
    """Explicit thread/profile binding: the model-visible block states the
    ACTUAL composed profile, so the model can answer truthfully about itself."""
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), seen=seen
    )

    service.handle(_envelope("/profile research", n=1, thread_id="th_1"))
    service.handle(_envelope("who are you", n=2, thread_id="th_1"))

    assert seen["profiles"] == ["research"]
    assert "active composition profile: research" in seen["last_prompt"]


def test_projection_shows_group_default_while_session_profile_is_none(
    tmp_path: Path, monkeypatch
):
    """Group default: session.profile stays None (config resolved at use
    time), yet the projection must show the EFFECTIVE profile — never a
    misleading 'none'."""
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path,
        monkeypatch,
        surface,
        _recording_fn(seen),
        RoutingPolicy(group_defaults={"oc_group_1": "writing"}),
        seen=seen,
    )

    service.handle(_envelope("who are you", n=1))

    assert _session(service).profile is None
    assert "active composition profile: writing" in seen["last_prompt"]


def test_projection_states_core_agent_and_keeps_actor_role_distinct(
    tmp_path: Path, monkeypatch
):
    """No binding anywhere: the block says core-agent composition, and the
    supervisor actor role stays a speaker fact — never readable as the
    agent's own profile (the live conflation that motivated this fix)."""
    seen: dict = {}
    surface = FakeSurface()
    service = _service(
        tmp_path, monkeypatch, surface, _recording_fn(seen), seen=seen
    )

    service.handle(_envelope("who are you", n=1, actor_role="supervisor"))

    assert (
        "active composition profile: (none — core agent composition"
        in seen["last_prompt"]
    )
    assert (
        "current actor role: supervisor (the speaker's role, not this agent's profile)"
        in seen["last_prompt"]
    )


def test_group_default_respects_access_policy(tmp_path: Path, monkeypatch):
    """A group default pointing at a restricted profile in a disallowed group
    is denied at run time, never executed."""
    seen: dict = {}
    surface = FakeSurface()
    routing = RoutingPolicy(
        group_defaults={"oc_other": "research"},
        profile_access={"research": ProfileAccessRule(allowed_channel_ids=("oc_lab",))},
    )
    service = _service(tmp_path, monkeypatch, surface, _recording_fn(seen), routing)

    service.handle(_envelope("hello", n=1, channel_id="oc_other"))

    assert seen.get("model_calls", 0) == 0
    assert "enabled only in approved channels" in surface.last_text()


# ── store: creator identity survives multi-operator groups ─────────────────


def test_session_keeps_creator_user_id_across_speakers(tmp_path: Path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    created = store.get_or_create_session(
        surface="feishu",
        tenant_id="default",
        user_id="ou_creator",
        channel_id="oc_group_1",
        thread_id=None,
        default_profile=None,
    )
    colleague = created.model_copy(update={"user_id": "ou_colleague"})
    store.save_session(colleague)

    stored = store.get_session(
        surface="feishu",
        tenant_id="default",
        user_id="ou_colleague",
        channel_id="oc_group_1",
        thread_id=None,
    )
    assert stored is not None
    assert stored.user_id == "ou_creator", (
        "first writer owns the session: approval tokens stay with the "
        "binding creator even when colleagues speak afterwards"
    )
