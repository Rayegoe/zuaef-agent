"""Host-grounded interaction identity — P3B-3 T001/T002/T003/T013.

The model never infers who it is talking to: the surface states the actor
role, the interaction projection renders deterministic environment facts,
context assembles in a fixed order (interaction → Case background → literal
raw request), and the Telegram supervisor console grounds actor_role=
supervisor for every authorized operator.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src")]

from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway import bridge
from zuaef_agent.gateway.interaction_projection import project_interaction_context
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.telegram import TelegramAdapter


def test_supervisor_on_bound_case_projects_full_identity_block():
    block = project_interaction_context("telegram", "supervisor", case_id="stillevo")
    assert block is not None
    assert block.startswith("Current interaction (host-grounded):")
    assert "- surface: telegram" in block
    assert "- current actor role: supervisor" in block
    assert "returns to this supervisor in the current conversation" in block
    assert "no channel tool is needed to reply here" in block
    assert "stillevo) is a different business party from the current actor" in block
    assert "replying normally in this conversation is NOT customer delivery" in block


def test_projection_is_environment_facts_not_workflow():
    block = project_interaction_context("telegram", "supervisor", case_id="c1")
    assert block is not None
    for workflow_phrase in ("first", "then call", "must save", "workflow", "步骤"):
        assert workflow_phrase not in block, workflow_phrase


def test_unknown_actor_never_becomes_the_case_customer():
    block = project_interaction_context("telegram", "unknown", case_id="c1")
    assert block is not None
    assert "- current actor role: unknown" in block
    assert "never assume the current speaker is the Case customer" in block


def test_unbound_conversation_states_no_case_without_inventing_a_customer():
    block = project_interaction_context("telegram", "supervisor")
    assert block is not None
    assert "- no Case is bound to this conversation" in block
    assert "different business party" not in block


def test_no_host_facts_projects_nothing():
    assert project_interaction_context(None, None) is None


# ── active composition profile vs actor role (Feishu v0.1 live finding) ──────


def test_profile_is_stated_adjacent_to_actor_role_not_conflated():
    block = project_interaction_context(
        "feishu", "supervisor", active_profile="quant-decision"
    )
    assert block is not None
    assert "- active composition profile: quant-decision" in block
    assert "- current actor role: supervisor (the speaker's role, not this agent's profile)" in block
    # both facts present and distinct
    assert block.index("current actor role") < block.index("active composition profile")


def test_core_agent_composition_stated_when_no_profile_bound():
    block = project_interaction_context("feishu", "supervisor", active_profile=None)
    assert block is not None
    assert (
        "- active composition profile: (none — core agent composition, "
        "no business profile)" in block
    )


def test_profile_alone_is_enough_to_project_a_block():
    block = project_interaction_context(None, None, active_profile="research")
    assert block is not None
    assert "- active composition profile: research" in block
    assert "- current actor role: unknown" in block


def test_telegram_adapter_grounds_authorized_operators_as_supervisor(tmp_path):
    """The Telegram console's allowlist IS the supervisor roster (T002):
    every normalized inbound from an authorized user carries actor_role=
    supervisor; unauthorized users never produce an envelope at all."""
    adapter = TelegramAdapter(
        token="t",
        allowed_user_ids={"42"},
        workspace_root=tmp_path,
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"ok": True, "result": {}})
            )
        ),
    )
    message = adapter._normalize_message(
        {
            "message_id": 7,
            "from": {"id": 42},
            "chat": {"id": 42, "type": "private"},
            "text": "改写这篇文章",
        }
    )
    assert message is not None
    assert message.actor_role == "supervisor"
    callback = adapter._normalize_callback(
        {
            "id": "cb1",
            "from": {"id": 42},
            "message": {"chat": {"id": 42, "type": "private"}},
            "data": "zc:cases:",
        }
    )
    assert callback is not None
    assert callback.actor_role == "supervisor"


def test_envelope_defaults_to_unknown_not_customer():
    envelope = InboundEnvelope(
        surface="web", user_id="u", channel_id="c", message_id="m", text="hi"
    )
    assert envelope.actor_role == "unknown"


# ── context assembly order + raw-request preservation (T003) ─────────────────


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


def _make_case(root: Path) -> None:
    case_dir = root / "cases" / "stillevo-beauty"
    case_dir.mkdir(parents=True)
    (case_dir / "case.md").write_text(
        "---\ncase_id: stillevo-beauty\ngoal: 推进到 Pilot。\nstatus: active\n---\n",
        encoding="utf-8",
    )
    (case_dir / "situation.json").write_text(
        '{"schema_version":1,"case_id":"stillevo-beauty","state":{"customer":{"company":"云朵美妆"}}}',
        encoding="utf-8",
    )


def test_bridge_assembles_interaction_then_literal_request(tmp_path: Path, monkeypatch):
    """v1.2 T005: the bridge assembles host-grounded interaction + the
    byte-literal raw request. A bound Case's background is NOT projected here —
    the composed Case plugin capability owns it (no bridge-side Case branch)."""
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    captured: dict[str, object] = {}

    def fake_execute_run(agent, deps, *, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["bindings"] = dict(deps.bindings)
        from zuaef_agent.runtime import TerminalRun

        return TerminalRun(presentation="ok", receipt=None)  # type: ignore[arg-type]

    monkeypatch.setattr(bridge, "execute_run", fake_execute_run)
    raw = "客户觉得上一篇还是太模板化，\n结合他之前的情况和材料再改一版给我看。"
    bridge.start_profile_run(
        settings=settings,
        profile=None,
        prompt=raw,
        conversation_id="c1",
        case_id="stillevo-beauty",
        surface="telegram",
        actor_role="supervisor",
    )
    prompt = str(captured["prompt"])
    # Deterministic ordering: host-grounded interaction → the byte-literal raw
    # user request at the tail. No Case brief in the bridge prompt.
    assert prompt.startswith("Current interaction (host-grounded):")
    interaction_end = prompt.index("\n\n---\n\n")
    interaction, rest = (
        prompt[:interaction_end],
        prompt[interaction_end + len("\n\n---\n\n") :],
    )
    assert "current actor role: supervisor" in interaction
    assert "Customer context (bound case" not in rest
    assert rest == raw
    # The binding still threads into the run's deps.
    assert captured["bindings"] == {"case": "stillevo-beauty"}


def test_bridge_raw_request_survives_unmodified_without_case(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    def fake_execute_run(agent, deps, *, prompt, **kwargs):
        captured["prompt"] = prompt
        from zuaef_agent.runtime import TerminalRun

        return TerminalRun(presentation="ok", receipt=None)  # type: ignore[arg-type]

    monkeypatch.setattr(bridge, "execute_run", fake_execute_run)
    raw = "给我看一版"
    bridge.start_profile_run(
        settings=settings,
        profile=None,
        prompt=raw,
        conversation_id="c2",
        surface="telegram",
        actor_role="supervisor",
    )
    prompt = str(captured["prompt"])
    assert prompt.endswith(raw)
    assert "Customer context" not in prompt
    assert "给我看" in prompt  # never rewritten into delivery semantics
    assert "发送" not in prompt.split("给我看")[0]


def test_gateway_service_threads_surface_and_actor_role_into_the_run(
    tmp_path: Path, monkeypatch
):
    from types import SimpleNamespace

    from zuaef_agent.gateway.service import GatewayService
    from zuaef_agent.gateway.store import GatewayStore

    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    class Surface:
        surface_name = "telegram"

        def poll_once(self, *, timeout_seconds):
            return []

        def pending_cursor(self):
            return None

        def send_text(self, channel_id, text): ...

        def send_document(self, channel_id, path, *, caption=None): ...

        def send_approval(
            self,
            channel_id,
            *,
            text,
            approve_token,
            approve_label="Approve",
            deny_label="Deny",
        ): ...

        def send_keyboard(self, channel_id, *, text, buttons): ...

        def answer_callback(self, callback_id, text): ...

    def fake_start(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            presentation="ok",
            receipt=SimpleNamespace(run_id="r-x", execution_state="completed"),
        )

    monkeypatch.setattr(bridge, "start_profile_run", fake_start)
    service = GatewayService(
        settings=settings,
        store=GatewayStore(tmp_path / "gateway.sqlite3"),
        surface=Surface(),
        default_profile=None,
    )
    service.handle(
        InboundEnvelope(
            surface="telegram",
            user_id="42",
            channel_id="42",
            message_id="m-1",
            text="改写这篇文章",
            actor_role="supervisor",
        )
    )
    assert captured["surface"] == "telegram"
    assert captured["actor_role"] == "supervisor"
