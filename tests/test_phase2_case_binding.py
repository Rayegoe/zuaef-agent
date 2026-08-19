"""Gateway Case binding and isolation — SPEC v1.0 §5, §7.3 (P2-3).

A channel/thread is deterministically bound to exactly one Case through the
existing Gateway SQLite store (``GatewayStore.bind_case``); the supervisor
CLI is the only writer. Conversation identity and Case identity stay separate
(``/new`` rotates the conversation but keeps the Case). The bound ``case_id``
is threaded into the run's CoreDeps by the real bridge, and the real
zuaef-case tools reject any operation on a different Case.
"""

from __future__ import annotations

import sqlite3
from importlib.metadata import EntryPoint
from pathlib import Path

from zuaef_agent import core as core_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.bridge import start_profile_run
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore
from zuaef_agent.gateway.surface import SurfaceAdapter

BINDING_PROFILE = """\
schema = 1
name = "binding-session"

[[plugins]]
id = "deps-probe"
"""


def _ep(name: str) -> EntryPoint:
    return EntryPoint(
        name=name,
        value="fixture_plugins.deps_probe:create_plugin",
        group="zuaef.plugins",
    )


DISCOVER = {"deps-probe": _ep("deps-probe")}
VERSIONS = {"deps-probe": "0.1.0"}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


class FakeSurface(SurfaceAdapter):
    surface_name = "telegram"

    def __init__(self):
        self.texts: list[tuple[str, str]] = []
        self.approvals: list[dict] = []

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id: str, text: str) -> None:
        self.texts.append((channel_id, text))

    def send_document(self, channel_id: str, path: Path, *, caption=None) -> None:
        pass

    def send_approval(self, channel_id, *, text, approve_token, approve_label="Approve", deny_label="Deny"):
        self.approvals.append({"channel_id": channel_id, "token": approve_token})

    def answer_callback(self, callback_id: str, text: str) -> None:
        pass


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_skills=False,
    )


def _key(**overrides):
    base = {
        "surface": "telegram",
        "tenant_id": "default",
        "user_id": "42",
        "channel_id": "42",
        "thread_id": None,
        "default_profile": "binding-session",
    }
    base.update(overrides)
    return base


def _get_key(**overrides):
    key = _key(**overrides)
    key.pop("default_profile", None)
    return key


# ── store-level binding ──────────────────────────────────────────────────────


def test_bind_case_persists_across_reopen(tmp_path: Path):
    db = tmp_path / "gateway.sqlite3"
    store = GatewayStore(db)
    session = store.get_or_create_session(**_key())
    bound = store.bind_case(session, "stillevo-beauty")
    assert bound.case_id == "stillevo-beauty"
    assert bound.conversation_id == session.conversation_id
    store.close()

    reopened = GatewayStore(db).get_session(**_get_key())
    assert reopened is not None
    assert reopened.case_id == "stillevo-beauty"
    assert reopened.conversation_id == session.conversation_id


def test_bind_case_unbind_clears(tmp_path: Path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    session = store.get_or_create_session(**_key())
    store.bind_case(session, "stillevo-beauty")
    unbound = store.bind_case(store.get_session(**_get_key()), None)
    assert unbound.case_id is None


def test_reset_new_conversation_keeps_case_binding(tmp_path: Path):
    """/new rotates the conversation but keeps the business Case (SPEC §5.3)."""
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    session = store.get_or_create_session(**_key())
    bound = store.bind_case(session, "stillevo-beauty")
    reset = store.reset_session(bound)
    assert reset.conversation_id != bound.conversation_id
    assert reset.case_id == "stillevo-beauty"
    assert reset.profile == bound.profile


def test_profile_switch_keeps_case_binding(tmp_path: Path):
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    session = store.get_or_create_session(**_key())
    bound = store.bind_case(session, "stillevo-beauty")
    switched = bound.model_copy(update={"profile": "other-profile"})
    store.save_session(switched)
    reloaded = store.get_session(**_get_key())
    assert reloaded.case_id == "stillevo-beauty"
    assert reloaded.profile == "other-profile"


def test_legacy_database_migrates_case_column(tmp_path: Path):
    """A database created by an earlier release (no case_id column) gets the
    column on open, keeping old session rows intact."""
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE session_bindings (
            surface TEXT NOT NULL, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL, thread_key TEXT NOT NULL,
            conversation_id TEXT NOT NULL, profile TEXT,
            active_run_id TEXT, paused_run_id TEXT, last_terminal_run_id TEXT,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY (surface, tenant_id, channel_id, thread_key)
        )
        """
    )
    conn.execute(
        "INSERT INTO session_bindings VALUES "
        "('telegram','default','42','42','','conv-old','prof',NULL,NULL,NULL,'t','t')"
    )
    conn.commit()
    conn.close()

    store = GatewayStore(db)
    row = store.get_session(
        surface="telegram", tenant_id="default", user_id="42",
        channel_id="42", thread_id=None,
    )
    assert row is not None
    assert row.conversation_id == "conv-old"
    assert row.case_id is None


# ── service → run deps threading ─────────────────────────────────────────────


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


def _write_profile(tmp_path: Path, name: str = "binding-session", text: str = BINDING_PROFILE) -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


def test_start_profile_run_threads_bound_case_into_deps(tmp_path: Path, monkeypatch):
    """The bridge puts the session's case_id into the real CoreDeps — the
    server-owned execution dependency, never model-guessed."""
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    def fn(messages, info):
        result = captured.get("probe_result")
        if result is None:
            for message in reversed(messages):
                for part in getattr(message, "parts", []):
                    if (
                        getattr(part, "part_kind", None) == "tool-return"
                        and getattr(part, "tool_name", None) == "probe_deps"
                    ):
                        captured["probe_result"] = part.content
                        break
                if "probe_result" in captured:
                    break
        if "probe_result" not in captured:
            return ModelResponse(parts=[ToolCallPart("probe_deps", {"label": "bound"})])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": "done"},
                )
            ]
        )

    monkeypatch.setattr(core_module, "resolve_model", lambda s: FunctionModel(fn))
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent", _fixture_builder
    )
    config_root = _write_profile(tmp_path)
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    session = store.get_or_create_session(**_key())
    session = store.bind_case(session, "stillevo-beauty")

    outcome = start_profile_run(
        settings=settings,
        profile="binding-session",
        prompt="probe",
        conversation_id=session.conversation_id,
        config_root=config_root,
        case_id=session.case_id,
    )
    assert captured["probe_result"] == f"bound:{outcome.receipt.run_id}:case=stillevo-beauty"
    assert outcome.receipt.case_id == "stillevo-beauty"


def test_gateway_service_injects_bound_case_into_run(tmp_path: Path, monkeypatch):
    """Full service dispatch: a bound session's ordinary inbound run receives
    the same case in deps AND in the receipt."""
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel

    def fn(messages, info):
        if "probe_result" not in captured:
            for message in reversed(messages):
                for part in getattr(message, "parts", []):
                    if (
                        getattr(part, "part_kind", None) == "tool-return"
                        and getattr(part, "tool_name", None) == "probe_deps"
                    ):
                        captured["probe_result"] = part.content
                        break
                if "probe_result" in captured:
                    break
        if "probe_result" not in captured:
            return ModelResponse(parts=[ToolCallPart("probe_deps", {"label": "bound"})])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": "done"},
                )
            ]
        )

    monkeypatch.setattr(core_module, "resolve_model", lambda s: FunctionModel(fn))
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent", _fixture_builder
    )
    config_root = _write_profile(tmp_path)
    store = GatewayStore(tmp_path / "gateway.sqlite3")
    service = GatewayService(
        settings=settings,
        store=store,
        surface=FakeSurface(),
        default_profile="binding-session",
        config_root=config_root,
    )
    session = store.get_or_create_session(**_key())
    bind_result = store.bind_case(session, "stillevo-beauty")
    assert bind_result.case_id == "stillevo-beauty"

    service.handle(
        InboundEnvelope(
            surface="telegram",
            user_id="42",
            channel_id="42",
            message_id="m-1",
            text="probe bound case",
        )
    )
    after = store.get_session(**_get_key())
    assert "case=stillevo-beauty" in str(captured["probe_result"])
    # The receipt records the same Case identity.
    from zuaef_agent.receipt_store import ReceiptStore

    receipt = ReceiptStore(settings.state_root).read(after.last_terminal_run_id)
    assert receipt.case_id == "stillevo-beauty"


# ── CLI supervisor binding operation ─────────────────────────────────────────


def test_cli_bind_case_command(tmp_path: Path, capsys):
    from zuaef_agent import cli

    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    args = cli._parser().parse_args(
        [
            "gateway",
            "bind-case",
            "--surface",
            "telegram",
            "--user",
            "42",
            "--channel",
            "42",
            "--case",
            "stillevo-beauty",
            "--workspace",
            str(workspace),
            "--state-root",
            str(state),
        ]
    )
    assert cli._gateway_bind_case(args) == cli.EXIT_COMPLETED
    store = GatewayStore(state / "gateway.sqlite3")
    session = store.get_session(
        surface="telegram", tenant_id="default", user_id="42",
        channel_id="42", thread_id=None,
    )
    assert session is not None and session.case_id == "stillevo-beauty"
    out = capsys.readouterr().out
    assert '"case_id": "stillevo-beauty"' in out
    store.close()


def test_cli_bind_case_unbind(tmp_path: Path):
    from zuaef_agent import cli

    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    store = GatewayStore(state / "gateway.sqlite3")
    session = store.get_or_create_session(**_key())
    store.bind_case(session, "stillevo-beauty")
    store.close()

    args = cli._parser().parse_args(
        [
            "gateway",
            "bind-case",
            "--surface",
            "telegram",
            "--user",
            "42",
            "--channel",
            "42",
            "--unbind",
            "--workspace",
            str(workspace),
            "--state-root",
            str(state),
        ]
    )
    assert cli._gateway_bind_case(args) == cli.EXIT_COMPLETED
    reopened = GatewayStore(state / "gateway.sqlite3")
    session = reopened.get_session(**_get_key())
    assert session is not None and session.case_id is None
    reopened.close()