"""Gateway CLI and runner tests — SPEC v0.3 Stage 6: parser, startup
validation (fail closed), polling loop, cursor persistence, shutdown."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

from zuaef_agent import cli
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.models import InboundEnvelope
from zuaef_agent.gateway.runner import GatewayConfig, load_gateway_config, run_gateway

ALLOWLIST = {"42"}


class LoopAdapter:
    """Fake surface whose poll returns scripted events then raises
    KeyboardInterrupt, simulating the gateway loop shutdown."""

    surface_name = "telegram"

    def __init__(self, events: list[InboundEnvelope], cursor: str):
        self.events = list(events)
        self.cursor = cursor
        self.offset = None
        self.sent: list[str] = []
        self.polls = 0
        self.closed = False
        self.probed = False

    def probe(self):
        self.probed = True
        return {"ok": True}

    def set_offset(self, offset):
        self.offset = offset

    def poll_once(self, *, timeout_seconds):
        self.polls += 1
        if self.events:
            batch, self.events = self.events, []
            return batch
        raise KeyboardInterrupt

    def pending_cursor(self):
        return self.cursor

    def send_text(self, channel_id: str, text: str) -> None:
        self.sent.append(text)

    def send_document(self, channel_id, path, *, caption=None) -> None:
        pass

    def send_approval(self, channel_id, *, text, approve_token, approve_label="Approve", deny_label="Deny") -> None:
        pass

    def answer_callback(self, callback_id: str, text: str) -> None:
        pass

    def close(self) -> None:
        self.closed = True


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


def _config(tmp_path: Path, **overrides) -> GatewayConfig:
    base = {
        "surface": "telegram",
        "profile": None,
        "config_root": None,
        "telegram_token": "123456:TEST-TOKEN",
        "allowed_user_ids": frozenset(ALLOWLIST),
    }
    base.update(overrides)
    return GatewayConfig(**base)


def test_parser_accepts_gateway_start_with_flags():
    args = cli._parser().parse_args(
        [
            "gateway",
            "start",
            "--surface",
            "telegram",
            "--profile",
            "wordpress-operator",
            "--workspace",
            "/tmp/w",
            "--model",
            "m",
            "--config-root",
            "/tmp/c",
        ]
    )
    assert args.command == "gateway"
    assert args.gateway_command == "start"
    assert args.surface == "telegram"
    assert args.profile == "wordpress-operator"


def test_parser_rejects_missing_surface():
    # argparse exits non-zero for a missing required flag — fail closed.
    with pytest.raises(SystemExit):
        cli._parser().parse_args(["gateway", "start"])


def test_load_gateway_config_from_env(monkeypatch):
    monkeypatch.setenv("ZUAEF_TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("ZUAEF_TELEGRAM_ALLOWED_USERS", "1, 2 ,3")
    monkeypatch.setenv("ZUAEF_TELEGRAM_POLL_TIMEOUT", "7")
    monkeypatch.setenv("ZUAEF_GATEWAY_APPROVAL_TTL", "3600")
    monkeypatch.setenv("ZUAEF_GATEWAY_MAX_UPLOAD_BYTES", "100")
    monkeypatch.setenv("ZUAEF_GATEWAY_MAX_ARTIFACT_BYTES", "50")

    config = load_gateway_config(type("Args", (), {})())

    assert config.telegram_token == "tok"
    assert config.allowed_user_ids == frozenset({"1", "2", "3"})
    assert config.poll_timeout == 7
    assert config.approval_ttl_seconds == 3600
    assert config.max_upload_bytes == 100
    assert config.max_artifact_bytes == 50


def test_load_gateway_config_telegram_token_fallback(monkeypatch):
    """ZUAEF_TELEGRAM_BOT_TOKEN wins; plain TELEGRAM_BOT_TOKEN (as commonly
    present in existing .env files) is an accepted fallback."""
    monkeypatch.delenv("ZUAEF_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fallback-token")
    config = load_gateway_config(type("Args", (), {})())
    assert config.telegram_token == "fallback-token"

    monkeypatch.setenv("ZUAEF_TELEGRAM_BOT_TOKEN", "preferred-token")
    config = load_gateway_config(type("Args", (), {})())
    assert config.telegram_token == "preferred-token"


def test_runner_silences_httpx_request_logging(tmp_path: Path):
    """httpx INFO logs full URLs — which embed /bot<TOKEN>/ paths. The runner
    must silence them (SPEC §17/§71): the bot token never enters logs."""
    import logging

    with pytest.raises(ValueError):
        run_gateway(
            config=_config(tmp_path, telegram_token=None), settings=_settings(tmp_path)
        )
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_gateway_start_fails_closed_without_token(tmp_path: Path):
    config = _config(tmp_path, telegram_token=None)
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        run_gateway(config=config, settings=_settings(tmp_path))


def test_gateway_start_fails_closed_with_empty_allowlist(tmp_path: Path):
    config = _config(tmp_path, allowed_user_ids=frozenset())
    with pytest.raises(ValueError, match="ALLOWED_USERS"):
        run_gateway(config=config, settings=_settings(tmp_path))


def test_gateway_start_fails_closed_for_invalid_profile(tmp_path: Path, monkeypatch):
    from zuaef_agent.plugin_api import CompositionError

    def fail(profile, settings, *, config_root=None):
        raise CompositionError(f"profile {profile!r} is not installed")

    monkeypatch.setattr(
        "zuaef_agent.gateway.runner.bridge.validate_profile", fail
    )
    config = _config(tmp_path, profile="ghost-profile")
    with pytest.raises(CompositionError, match="ghost-profile"):
        run_gateway(config=config, settings=_settings(tmp_path))


def test_gateway_start_fails_when_probe_fails(tmp_path: Path):
    class DeadProbe:
        surface_name = "telegram"

        def probe(self):
            raise httpx.HTTPError("telegram getMe failed")

    config = _config(tmp_path)
    with pytest.raises(httpx.HTTPError):
        run_gateway(
            config=config,
            settings=_settings(tmp_path),
            adapter_factory=lambda c, s: DeadProbe(),
        )


def test_gateway_start_rejects_non_telegram_surface(tmp_path: Path):
    config = _config(tmp_path, surface="feishu")
    with pytest.raises(ValueError, match="telegram only"):
        run_gateway(config=config, settings=_settings(tmp_path))


def test_gateway_loop_survives_transient_poll_errors(tmp_path: Path):
    """A proxy disconnect during long polling must not kill the gateway: log,
    retry, keep the process alive (cursor not yet advanced → re-receive)."""

    class FlakyAdapter(LoopAdapter):
        def poll_once(self, *, timeout_seconds):
            self.polls += 1
            if self.polls == 1:
                raise httpx.HTTPError("Server disconnected without sending a response.")
            raise KeyboardInterrupt

    adapter = FlakyAdapter([], cursor=None)
    config = _config(tmp_path, poll_retry_seconds=0)

    code = run_gateway(
        config=config,
        settings=_settings(tmp_path),
        adapter_factory=lambda c, s: adapter,
    )

    assert code == 0
    assert adapter.polls == 2, "the loop must retry after a transient poll failure"
    assert adapter.closed


def test_gateway_loop_survives_transient_send_errors(tmp_path: Path):
    """A failed outbound send for one event must not kill the gateway; the
    cursor is still persisted and polling continues."""

    class SendFails(LoopAdapter):
        def send_text(self, channel_id: str, text: str) -> None:
            raise httpx.HTTPError("send failed")

    adapter = SendFails(
        [
            InboundEnvelope(
                surface="telegram",
                user_id="42",
                channel_id="42",
                message_id="m1",
                text="/status",
            )
        ],
        cursor="3",
    )
    config = _config(tmp_path)

    code = run_gateway(
        config=config,
        settings=_settings(tmp_path),
        adapter_factory=lambda c, s: adapter,
    )

    assert code == 0
    from zuaef_agent.gateway.store import GatewayStore

    store = GatewayStore(_settings(tmp_path).state_root / "gateway.sqlite3")
    assert store.get_cursor("telegram") == "3"


def test_gateway_loop_handles_events_persists_cursor_and_shuts_down(
    tmp_path: Path,
):
    envelope = InboundEnvelope(
        surface="telegram", user_id="42", channel_id="42", message_id="m1", text="/status"
    )
    adapter = LoopAdapter([envelope], cursor="5")
    settings = _settings(tmp_path)
    config = _config(tmp_path)

    code = run_gateway(
        config=config,
        settings=settings,
        adapter_factory=lambda c, s: adapter,
    )

    assert code == 0
    assert adapter.probed
    assert adapter.polls == 2
    assert adapter.closed
    assert any("State: READY" in text for text in adapter.sent)

    from zuaef_agent.gateway.store import GatewayStore

    store = GatewayStore(settings.state_root / "gateway.sqlite3")
    assert store.get_cursor("telegram") == "5"
    # restart resumes from the persisted offset
    adapter2 = LoopAdapter([], cursor="6")
    run_gateway(
        config=config,
        settings=settings,
        adapter_factory=lambda c, s: adapter2,
    )
    assert adapter2.offset == 5


def test_gateway_loop_recovers_sessions_on_startup(tmp_path: Path):
    from datetime import UTC, datetime

    from zuaef_agent.models import PauseReceipt
    from zuaef_agent.receipt_store import ReceiptStore

    settings = _settings(tmp_path)
    config = _config(tmp_path)
    now = datetime.now(UTC)
    ReceiptStore(settings.state_root).write(
        PauseReceipt(
            run_id="run-p",
            conversation_id="c1",
            model="test",
            started_at=now,
            finished_at=now,
        )
    )
    from zuaef_agent.gateway.store import GatewayStore

    store = GatewayStore(settings.state_root / "gateway.sqlite3")
    store.get_or_create_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
        default_profile=None,
    )
    session = store.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )
    store.save_session(session.model_copy(update={"active_run_id": "run-p"}))
    store.close()

    adapter = LoopAdapter([], cursor=None)
    run_gateway(
        config=config,
        settings=settings,
        adapter_factory=lambda c, s: adapter,
    )

    store2 = GatewayStore(settings.state_root / "gateway.sqlite3")
    session2 = store2.get_session(
        surface="telegram",
        tenant_id="default",
        user_id="42",
        channel_id="42",
        thread_id=None,
    )
    assert session2.paused_run_id == "run-p"
    assert session2.active_run_id is None


def test_cli_gateway_error_is_process_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["zuaef-agent", "gateway", "start", "--surface", "telegram", "--workspace", str(tmp_path)],
    )
    monkeypatch.setenv("ZUAEF_TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("ZUAEF_TELEGRAM_ALLOWED_USERS", "")
    monkeypatch.delenv("ZUAEF_GATEWAY_DEFAULT_PROFILE", raising=False)
    monkeypatch.setattr(
        "zuaef_agent.gateway.runner.load_gateway_config",
        lambda args: GatewayConfig(
            surface="telegram", telegram_token=None, allowed_user_ids=frozenset()
        ),
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == cli.EXIT_PROCESS_ERROR
    assert "BOT_TOKEN" in capsys.readouterr().err


def test_cli_gateway_delegates_to_runner(monkeypatch, tmp_path):
    calls: dict = {}

    def fake_run_gateway(*, config, settings):
        calls["config"] = config
        calls["settings"] = settings
        return 0

    monkeypatch.setattr(
        "zuaef_agent.gateway.runner.run_gateway", fake_run_gateway
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zuaef-agent",
            "gateway",
            "start",
            "--surface",
            "telegram",
            "--profile",
            "wordpress-operator",
            "--workspace",
            str(tmp_path),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert calls["config"].profile == "wordpress-operator"
    assert calls["settings"].workspace_root == tmp_path
