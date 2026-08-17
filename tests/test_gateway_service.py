"""GatewayService tests — SPEC v0.3 §78.

Full mocked flows through the real service dispatch: message → paused →
approval button → resume → terminal. FunctionModel is injected through
``core.resolve_model``; the fixture plugin registry is injected through the
bridge's composition seams (the same pattern as the bridge tests).
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import EntryPoint
from pathlib import Path

from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent import core as core_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.service import WAITING_FOR_APPROVAL, GatewayService
from zuaef_agent.gateway.store import GatewayStore
from zuaef_agent.models import PauseReceipt, RunReceipt, RunSummary
from zuaef_agent.receipt_store import ReceiptStore

models.ALLOW_MODEL_REQUESTS = False

EP = EntryPoint(
    name="fixture-ace-writing",
    value="fixture_plugins.writing:create_plugin",
    group="zuaef.plugins",
)
DISCOVER = {"fixture-ace-writing": EP}
VERSIONS = {"fixture-ace-writing": "0.2.1"}
PROFILE = 'schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\nace_root = "/v1"\n'


class FakeSurface:
    surface_name = "telegram"

    def __init__(self):
        self.texts: list[tuple[str, str]] = []
        self.documents: list[tuple[str, Path, str | None]] = []
        self.approvals: list[dict] = []
        self.callback_answers: list[tuple[str, str]] = []

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id: str, text: str) -> None:
        self.texts.append((channel_id, text))

    def send_document(self, channel_id: str, path: Path, *, caption=None) -> None:
        self.documents.append((channel_id, path, caption))

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
        approve_label: str = "Approve",
        deny_label: str = "Deny",
    ) -> None:
        self.approvals.append(
            {
                "channel_id": channel_id,
                "text": text,
                "token": approve_token,
                "approve_label": approve_label,
                "deny_label": deny_label,
            }
        )

    def answer_callback(self, callback_id: str, text: str) -> None:
        self.callback_answers.append((callback_id, text))

    def last_text(self) -> str:
        return "".join(text for _, text in self.texts)


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


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


def _write_profile(tmp_path: Path, name: str = "writing", text: str = PROFILE) -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


def _fixture_builder(settings, *, run_id=None, profile=None, snapshot=None, config_root=None, **_):
    from zuaef_agent.composition import build_profile_agent as real

    return real(
        settings,
        run_id=run_id,
        profile=profile,
        snapshot=snapshot,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )


def _fixture_validate(profile, settings, *, config_root=None, **kw):
    from zuaef_agent.composition import resolve_profile

    resolve_profile(
        profile,
        settings,
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )


def _final(status="completed", outcome="done"):
    return ModelResponse(
        parts=[
            ToolCallPart(
                "final_result",
                {"status": status, "outcome": outcome, "artifacts": [], "evidence": []},
            )
        ]
    )


def _pause_fn(seen: dict):
    def fn(messages, info):
        seen["model_calls"] = seen.get("model_calls", 0) + 1
        has_return = any(
            getattr(part, "part_kind", None) == "tool-return"
            for message in messages
            for part in getattr(message, "parts", [])
        )
        if not has_return:
            return ModelResponse(
                parts=[ToolCallPart("publish_article", {"article_id": "a1"})]
            )
        return _final()

    return fn


def _service(tmp_path: Path, monkeypatch, surface: FakeSurface, fn) -> GatewayService:
    settings = _settings(tmp_path)
    _write_profile(tmp_path)
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    monkeypatch.setattr(
        core_module, "resolve_model", lambda s: FunctionModel(fn)
    )
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent", _fixture_builder
    )
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
        default_profile="writing",
        config_root=tmp_path / "config",
    )


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


def _session(service: GatewayService) -> object:
    return service.store.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )


def _ensure_session(
    service: GatewayService,
    *,
    user_id: str = "42",
    channel_id: str = "42",
    default_profile: str | None = "writing",
):
    return service.store.get_or_create_session(
        surface="telegram",
        tenant_id="default",
        user_id=user_id,
        channel_id=channel_id,
        thread_id=None,
        default_profile=default_profile,
    )


def test_normal_message_starts_run_and_sets_last_terminal(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final(outcome="checked"))

    service.handle(_envelope("check the post"))

    session = _session(service)
    assert session.active_run_id is None
    assert session.last_terminal_run_id
    assert "✅ Completed" in surface.last_text()
    assert "checked" in surface.last_text()


def test_paused_run_sets_paused_run_id_and_creates_token(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))

    service.handle(_envelope("publish the article"))

    session = _session(service)
    assert session.paused_run_id
    assert session.active_run_id is None
    assert session.last_terminal_run_id is None
    assert len(surface.approvals) == 1
    approval = surface.approvals[0]
    assert "⚠️ Approval required" in approval["text"]
    assert "publish_article" in approval["text"]
    binding = service.store.resolve_approval(approval["token"])
    assert binding is not None
    assert binding.state == "pending"
    assert binding.paused_run_id == session.paused_run_id


def test_normal_message_while_paused_is_rejected(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    calls_before = seen["model_calls"]

    service.handle(_envelope("do another thing", n=2))

    assert WAITING_FOR_APPROVAL in surface.last_text()
    assert seen["model_calls"] == calls_before, "no second run may start while paused"


def test_approve_callback_resumes_and_settles(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    paused_run_id = _session(service).paused_run_id
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

    session = _session(service)
    assert session.paused_run_id is None
    assert session.last_terminal_run_id
    assert session.last_terminal_run_id != paused_run_id
    assert surface.callback_answers == [("cb-1", "Approved. Resuming…")]
    receipt = service.receipts.read(session.last_terminal_run_id)
    assert receipt.continued_from_run_id == paused_run_id
    assert receipt.conversation_id == session.conversation_id
    assert any(e.tool_name == "publish_article" for e in receipt.verified_tool_effects)
    assert "✅ Completed" in surface.last_text()


def test_deny_callback_resumes_without_effect(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    token = surface.approvals[0]["token"]

    service.handle(
        _envelope("", n=2, callback_token=token, callback_action="deny")
    )

    session = _session(service)
    assert session.paused_run_id is None
    receipt = service.receipts.read(session.last_terminal_run_id)
    assert not [
        e for e in receipt.verified_tool_effects if e.status == "completed"
    ]


def test_duplicate_approval_is_rejected_without_second_resume(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    token = surface.approvals[0]["token"]

    service.handle(_envelope("", n=2, callback_token=token, callback_action="approve"))
    settled_run_id = _session(service).last_terminal_run_id
    model_calls_after_first = seen["model_calls"]

    service.handle(_envelope("", n=3, callback_token=token, callback_action="approve"))

    assert "already approved" in surface.last_text()
    assert seen["model_calls"] == model_calls_after_first
    assert _session(service).last_terminal_run_id == settled_run_id


def test_foreign_user_token_rejected(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    token = surface.approvals[0]["token"]

    service.handle(
        _envelope(
            "",
            n=2,
            user_id="99",
            channel_id="99",
            callback_token=token,
            callback_action="approve",
        )
    )

    assert "another user" in surface.last_text()
    assert _session(service).paused_run_id, "run must stay paused"


def test_new_invalidates_interactive_gate(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    token = surface.approvals[0]["token"]
    old_conversation = _session(service).conversation_id

    service.handle(_envelope("/new", n=2))

    session = _session(service)
    assert session.paused_run_id is None
    assert session.conversation_id != old_conversation
    assert session.profile == "writing", "/new keeps the profile"
    binding = service.store.resolve_approval(token)
    assert binding.state == "expired"
    assert "New ZUAEF conversation started" in surface.last_text()


def test_profile_switch_forbidden_while_paused(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))

    service.handle(_envelope("/profile other", n=2))

    assert "waiting for approval" in surface.last_text()
    assert _session(service).profile == "writing"


def test_profile_switch_when_ready(tmp_path: Path, monkeypatch):
    _write_profile(
        tmp_path,
        "other",
        text='schema = 1\nname = "other"\n\n[[plugins]]\nid = "hardware-scout"\n',
    )
    ep2 = EntryPoint(
        name="hardware-scout",
        value="fixture_plugins.hardware:create_plugin",
        group="zuaef.plugins",
    )
    DISCOVER["hardware-scout"] = ep2
    VERSIONS["hardware-scout"] = "0.1.0"

    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    service.handle(_envelope("/profile other", n=1))

    assert _session(service).profile == "other"
    assert "Current profile: other" in surface.last_text()


def test_status_is_host_grounded_and_never_calls_model(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    model_calls = seen["model_calls"]

    service.handle(_envelope("/status", n=2))

    assert seen["model_calls"] == model_calls, "/status must not call the model"
    assert "State: PAUSED" in surface.last_text()
    assert "Pending approvals: 1" in surface.last_text()
    assert "publish_article" in surface.last_text()


def test_status_after_terminal_shows_last_state(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final(status="partial"))

    service.handle(_envelope("do it", n=1))
    service.handle(_envelope("/status", n=2))

    assert "State: LAST PARTIAL" in surface.last_text()


def test_slash_approve_and_deny_share_resume_semantics(tmp_path: Path, monkeypatch):
    seen: dict = {}
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, _pause_fn(seen))
    service.handle(_envelope("publish the article", n=1))
    paused_run_id = _session(service).paused_run_id
    token = surface.approvals[0]["token"]

    service.handle(_envelope("/approve", n=2))

    session = _session(service)
    assert session.paused_run_id is None
    receipt = service.receipts.read(session.last_terminal_run_id)
    assert receipt.continued_from_run_id == paused_run_id
    assert any(e.tool_name == "publish_article" for e in receipt.verified_tool_effects)
    # stale button dies after slash resume
    assert service.store.resolve_approval(token).state == "expired"


def test_slash_approve_without_paused_run(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    service.handle(_envelope("/approve", n=1))
    assert "Nothing is awaiting approval" in surface.last_text()


def test_artifacts_delivers_verified_files_only(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    settings = service.settings
    workspace = settings.workspace_root
    report = workspace / "artifacts" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# report", encoding="utf-8")
    now = datetime.now(UTC)
    receipt = RunReceipt(
        run_id="run-art-1",
        model="test",
        started_at=now,
        finished_at=now,
        status="completed",
        summary=RunSummary(status="completed", outcome="done"),
        verified_artifacts=[
            {"path": "artifacts/report.md", "size": 8, "sha256": "x" * 64},
            # claimed by the model but never host-verified → absent here
        ],
    )
    ReceiptStore(settings.state_root).write(receipt)
    session = _ensure_session(service)
    session = session.model_copy(update={"last_terminal_run_id": "run-art-1"})
    service.store.save_session(session)

    service.handle(_envelope("/artifacts", n=2))

    assert len(surface.documents) == 1
    assert surface.documents[0][0] == "42"
    assert surface.documents[0][1].name == "report.md"


def test_artifacts_missing_file_sends_path_and_size(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    settings = service.settings
    now = datetime.now(UTC)
    receipt = RunReceipt(
        run_id="run-art-2",
        model="test",
        started_at=now,
        finished_at=now,
        status="completed",
        summary=RunSummary(status="completed", outcome="done"),
        verified_artifacts=[
            {"path": "artifacts/ghost.md", "size": 4096, "sha256": "y" * 64}
        ],
    )
    ReceiptStore(settings.state_root).write(receipt)
    session = _ensure_session(service)
    session = session.model_copy(update={"last_terminal_run_id": "run-art-2"})
    service.store.save_session(session)

    service.handle(_envelope("/artifacts", n=2))

    assert surface.documents == []
    assert "artifacts/ghost.md" in surface.last_text()
    assert "4096 bytes" in surface.last_text()


def test_help_lists_commands(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    service.handle(_envelope("/help", n=1))
    for command in ("/new", "/profile", "/status", "/approve", "/deny", "/artifacts"):
        assert command in surface.last_text()


def test_recover_sessions_reconciles_routing_state(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    settings = service.settings
    now = datetime.now(UTC)
    # paused run with a pause receipt → stays paused
    ReceiptStore(settings.state_root).write(
        PauseReceipt(
            run_id="run-p",
            conversation_id="c1",
            model="test",
            started_at=now,
            finished_at=now,
        )
    )
    # active run with a terminal receipt → settles to last_terminal
    ReceiptStore(settings.state_root).write(
        RunReceipt(
            run_id="run-t",
            model="test",
            started_at=now,
            finished_at=now,
            status="completed",
            summary=RunSummary(status="completed", outcome="done"),
        )
    )
    s1 = _ensure_session(service)
    s1 = s1.model_copy(update={"paused_run_id": "run-p"})
    service.store.save_session(s1)
    s2 = _ensure_session(service, user_id="43", channel_id="43", default_profile=None)
    service.store.save_session(s2.model_copy(update={"active_run_id": "run-t"}))
    s3 = _ensure_session(service, user_id="44", channel_id="44", default_profile=None)
    service.store.save_session(s3.model_copy(update={"active_run_id": "run-gone"}))

    warnings = service.recover_sessions()

    assert any("run-gone" in w for w in warnings)
    assert _session(service).paused_run_id == "run-p"
    assert (
        service.store.get_session(
            surface="telegram",
            tenant_id="default",
            user_id="43",
            channel_id="43",
            thread_id=None,
        ).last_terminal_run_id
        == "run-t"
    )
    assert (
        service.store.get_session(
            surface="telegram",
            tenant_id="default",
            user_id="44",
            channel_id="44",
            thread_id=None,
        ).active_run_id
        is None
    )


def test_unauthorized_user_rejected_at_service(tmp_path: Path, monkeypatch):
    surface = FakeSurface()
    service = _service(tmp_path, monkeypatch, surface, lambda m, i: _final())
    service.allowed_user_ids = {"42"}
    seen: dict = {}
    monkeypatch.setattr(
        core_module, "resolve_model", lambda s: FunctionModel(_pause_fn(seen))
    )
    service.handle(_envelope("do it", n=1, user_id="999", channel_id="999"))
    assert seen.get("model_calls", 0) == 0
    assert surface.texts == []
