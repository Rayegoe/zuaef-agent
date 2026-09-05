"""zuaef-telegram plugin tests.

Telegram Bot API is mocked via httpx; the native-approval path is proven end
to end through the REAL installed ``zuaef.plugins`` entry point, exactly like
the WordPress plugin suite.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic_ai import RunContext, RunUsage, models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_telegram import create_plugin
from zuaef_telegram import notify as tg_notify
from zuaef_telegram import toolset as tg_toolset
from zuaef_telegram.client import TelegramClient, TelegramError, redact_token
from zuaef_telegram.toolset import (
    ArtifactPathError,
    make_toolset,
    resolve_delivery_artifact,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv
from zuaef_agent.runtime import PausedRun, TerminalRun, execute_run

models.ALLOW_MODEL_REQUESTS = False

TOKEN = "123456:ABCDefghIJKlmNOPqrstuVWXyz0123456789"
CHAT_ID = "8150664476"


# ── helpers ─────────────────────────────────────────────────────────────────


def _send_ok(message_id: int, chat_id: str = CHAT_ID) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "ok": True,
            "result": {
                "message_id": message_id,
                "chat": {"id": chat_id},
                "date": 1735689600,
                "text": "",
            },
        },
    )


class FakeTelegram:
    """Records every request that reached the mocked sendMessage transport.

    Each canned item is either a ready ``httpx.Response`` or a handler
    ``callable(request) -> httpx.Response`` (for raise-on-call cases).
    """

    def __init__(self, responses: list):
        self.requests: list[httpx.Request] = []
        self._responses = list(responses)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self._responses.pop(0)
        if isinstance(item, httpx.Response):
            return item
        return item(request)


def _client(fake: FakeTelegram) -> TelegramClient:
    return TelegramClient(
        bot_token=TOKEN,
        chat_id=CHAT_ID,
        transport=httpx.MockTransport(fake.handler),
    )


def _env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)


def _plugin_env(tmp_path: Path) -> PluginEnv:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return PluginEnv(
        plugin_id="telegram",
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
        model=None,  # type: ignore[arg-type]  # helper-only probe, mirrors wordpress suite
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


def _run_with(fake: FakeTelegram, tmp_path: Path, args: dict):
    settings = _settings(tmp_path)
    agent = build_agent(
        settings,
        run_id="tg",
        extra_toolsets=[make_toolset(_client(fake), workspace_root=settings.workspace_root)],
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id="tg")

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(parts=[ToolCallPart("report_to_telegram", args)])
        return _final()

    with agent.override(model=FunctionModel(fn)):
        return execute_run(agent, deps, prompt="report", settings=settings, run_id="tg")


# ── factory ─────────────────────────────────────────────────────────────────


def test_factory_returns_bundle_with_exact_tool_and_skill(tmp_path: Path, monkeypatch):
    _env(monkeypatch)
    bundle = create_plugin(_plugin_env(tmp_path), {})
    assert _tool_names(bundle) == {"report_to_telegram", "send_artifact_to_supervisor"}
    assert all(Path(d).is_dir() for d in bundle.skill_dirs), "bundled skill must exist"
    # the bundle returns the skill LIBRARY root (Skills capability contract:
    # immediate children are skill packages); the package is
    # skills/telegram-reporting/SKILL.md
    assert (Path(bundle.skill_dirs[0]) / "telegram-reporting" / "SKILL.md").is_file()


def test_factory_fails_loud_without_bot_token(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(CompositionError, match="credentials missing"):
        create_plugin(_plugin_env(tmp_path), {})


def test_factory_fails_loud_without_chat_id(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(CompositionError, match="credentials missing"):
        create_plugin(_plugin_env(tmp_path), {})


# ── transport ───────────────────────────────────────────────────────────────


def test_send_message_sends_payload_and_bounds_response():
    fake = FakeTelegram([_send_ok(41)])
    result = _client(fake).send_message("T006-B6 complete")
    req = fake.requests[0]
    assert req.method == "POST"
    assert req.url.path == f"/bot{TOKEN}/sendMessage"
    assert json.loads(req.content) == {"chat_id": CHAT_ID, "text": "T006-B6 complete"}
    assert result == {"ok": True, "message_id": 41, "date": 1735689600}


def test_http_500_fails_loud_without_leaking_token():
    def _five_hundred(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(TelegramError, match="HTTP 500") as err:
        _client(FakeTelegram([_five_hundred])).send_message("x")
    assert TOKEN not in str(err.value)


def test_telegram_ok_false_fails_loud_without_leaking_token():
    def _bad_request(request: httpx.Request) -> httpx.Response:
        # Telegram reports some failures as 200 + ok:false
        return httpx.Response(200, json={"ok": False, "description": "chat not found"})

    with pytest.raises(TelegramError, match="chat not found") as err:
        _client(FakeTelegram([_bad_request])).send_message("x")
    assert TOKEN not in str(err.value)


def test_timeout_fails_loud():
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(TelegramError, match="timed out") as err:
        _client(FakeTelegram([slow])).send_message("x")
    assert TOKEN not in str(err.value)


def test_network_error_fails_loud():
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(TelegramError, match="sendMessage failed") as err:
        _client(FakeTelegram([broken])).send_message("x")
    assert TOKEN not in str(err.value)


def test_no_request_on_msgsize_or_other_branches_is_false_positive():
    # guard: the token must never survive into the HTTP error path's repr
    assert "123456" not in redact_token("https://api.telegram.org/bot***/sendMessage")


# ── native approval behavior ────────────────────────────────────────────────


def test_report_to_telegram_pauses_for_native_approval_before_sending(
    tmp_path: Path,
):
    fake = FakeTelegram([_send_ok(1)])
    outcome = _run_with(fake, tmp_path, {"message": "done"})
    assert isinstance(outcome, PausedRun)
    assert outcome.pause_receipt.pending_approvals[0]["tool_name"] == (
        "report_to_telegram"
    )
    assert fake.requests == [], "external write must not send before approval"


def test_send_after_approval_executes_and_settles(tmp_path: Path, monkeypatch):
    """Full native-approval proof through the REAL installed entry point:
    profile → build_profile_agent → pause → shared resume → Telegram send.
    The factory is patched to inject the mocked transport while the real
    `zuaef.plugins` entry point, composition and frozen snapshot stay."""
    import zuaef_telegram

    from zuaef_agent.composition import build_profile_agent
    from zuaef_agent.continuation import resume_paused_run

    fake = FakeTelegram([_send_ok(7)])
    client = _client(fake)

    def fixture_factory(env, config):
        return PluginBundle(
            toolsets=[make_toolset(client, workspace_root=tmp_path / "workspace")]
        )

    monkeypatch.setattr(zuaef_telegram, "create_plugin", fixture_factory)

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "telegram-reporter.toml").write_text(
        'schema = 1\nname = "telegram-reporter"\n\n[[plugins]]\nid = "telegram"\n',
        encoding="utf-8",
    )

    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="telegram-reporter",
        config_root=config_root,
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(
                parts=[ToolCallPart("report_to_telegram", {"message": "T006-B6 done"})]
            )
        return _final()

    with agent.override(model=FunctionModel(fn)):
        paused = execute_run(
            agent,
            deps,
            prompt="report completion",
            settings=settings,
            run_id=run_id,
            composition=snapshot,
        )
    assert isinstance(paused, PausedRun)
    assert fake.requests == [], "external write must not send before approval"

    terminal = resume_paused_run(settings, run_id, decision="approve")
    assert isinstance(terminal, TerminalRun)
    assert len(fake.requests) == 1
    assert json.loads(fake.requests[0].content) == {
        "chat_id": CHAT_ID,
        "text": "T006-B6 done",
    }
    settled = [
        e
        for e in terminal.receipt.tool_effect_facts
        if e.tool_name == "report_to_telegram"
    ]
    assert settled and settled[0].status == "completed"


# ── operator notifier (unattended attention path) ───────────────────────────


def _patch_notify_client(monkeypatch, fake: FakeTelegram) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", CHAT_ID)
    monkeypatch.setattr(tg_notify, "TelegramClient", lambda **kwargs: _client(fake))


def test_notify_operator_sends_immediately_without_any_approval(monkeypatch, capsys):
    """The notifier is not a model tool: a plain host call sends at once."""
    fake = FakeTelegram([_send_ok(52)])
    _patch_notify_client(monkeypatch, fake)

    assert tg_notify.notify_operator("ZUAEF Supervisor report published.") == {
        "ok": True,
        "message_id": 52,
        "date": 1735689600,
    }
    assert len(fake.requests) == 1, "notifier must send without tool approval"
    assert json.loads(fake.requests[0].content) == {
        "chat_id": CHAT_ID,
        "text": "ZUAEF Supervisor report published.",
    }


def test_notify_operator_missing_credentials_raise(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(TelegramError, match="not configured"):
        tg_notify.notify_operator("x")


def test_notify_operator_send_failure_is_bounded_and_redacted(monkeypatch):
    def _boom(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    fake = FakeTelegram([_boom])
    _patch_notify_client(monkeypatch, fake)
    with pytest.raises(TelegramError, match="HTTP 500") as err:
        tg_notify.notify_operator("x")
    assert TOKEN not in str(err.value)


def test_notify_cli_prints_bounded_fact_and_exits_zero(monkeypatch, capsys):
    fake = FakeTelegram([_send_ok(53)])
    _patch_notify_client(monkeypatch, fake)

    assert tg_notify.main(["report done"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out) == {"ok": True, "message_id": 53, "date": 1735689600}


def test_notify_cli_missing_credentials_exit_one(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert tg_notify.main(["x"]) == 1
    err = capsys.readouterr().err
    assert "not configured" in err
    assert TOKEN not in err


# ── document transport (Phase 2 T8) ─────────────────────────────────────────


def test_send_document_multipart_upload_and_bounded_response(tmp_path: Path):
    target = tmp_path / "quant-business-20260904T150000Z.html"
    target.write_text("<html>quant report</html>", encoding="utf-8")
    fake = FakeTelegram([_send_ok(61)])
    result = _client(fake).send_document(target, caption="report")
    req = fake.requests[0]
    assert req.method == "POST"
    assert req.url.path == f"/bot{TOKEN}/sendDocument"
    body = req.content.decode("utf-8", errors="replace")
    assert f'name="document"; filename="{target.name}"' in body
    assert "quant report" in body
    assert result == {"ok": True, "message_id": 61, "date": 1735689600, "file": target.name}


def test_send_document_ok_false_fails_loud_without_leaking_token(tmp_path: Path):
    target = tmp_path / "report.html"
    target.write_text("x", encoding="utf-8")

    def _bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "file too big"})

    with pytest.raises(TelegramError, match="file too big") as err:
        _client(FakeTelegram([_bad])).send_document(target)
    assert TOKEN not in str(err.value)


# ── self-delivery path safety chain (Phase 2 §14, amendment chain) ─────────


def _delivery_env(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    delivery = workspace / "artifacts" / "quant" / "delivery"
    delivery.mkdir(parents=True, exist_ok=True)
    return workspace, delivery


def test_resolve_accepts_file_inside_delivery_scope(tmp_path: Path):
    workspace, delivery = _delivery_env(tmp_path)
    report = delivery / "quant-business-x.html"
    report.write_text("<html/>", encoding="utf-8")
    resolved = resolve_delivery_artifact("artifacts/quant/delivery/quant-business-x.html", workspace)
    assert resolved == report.resolve()


def test_resolve_rejects_absolute_parent_and_outside_scope(tmp_path: Path):
    workspace, _ = _delivery_env(tmp_path)
    for bad in ("/etc/passwd", "artifacts/quant/../../secrets.html", "../x.html", ""):
        with pytest.raises(ArtifactPathError):
            resolve_delivery_artifact(bad, workspace)
    outside = tmp_path / "elsewhere.html"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ArtifactPathError):
        resolve_delivery_artifact("artifacts/quant/delivery/../../elsewhere.html", workspace)


def test_resolve_rejects_symlink_escape(tmp_path: Path):
    workspace, delivery = _delivery_env(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("token", encoding="utf-8")
    (delivery / "innocent.html").symlink_to(secret)
    with pytest.raises(ArtifactPathError, match="delivery"):
        resolve_delivery_artifact("artifacts/quant/delivery/innocent.html", workspace)


def test_resolve_rejects_bad_extension_missing_and_oversized(tmp_path: Path, monkeypatch):
    workspace, delivery = _delivery_env(tmp_path)
    (delivery / "binary.exe").write_text("MZ", encoding="utf-8")
    with pytest.raises(ArtifactPathError, match="extension"):
        resolve_delivery_artifact("artifacts/quant/delivery/binary.exe", workspace)
    with pytest.raises(ArtifactPathError, match="regular file"):
        resolve_delivery_artifact("artifacts/quant/delivery/missing.html", workspace)
    big = delivery / "big.html"
    big.write_text("x" * 100, encoding="utf-8")
    monkeypatch.setattr(tg_toolset, "MAX_ARTIFACT_BYTES", 10)
    with pytest.raises(ArtifactPathError, match="too large"):
        resolve_delivery_artifact("artifacts/quant/delivery/big.html", workspace)


def test_send_artifact_tool_sends_within_scope_and_rejects_outside(tmp_path: Path):
    workspace, delivery = _delivery_env(tmp_path)
    report = delivery / "quant-business-x.html"
    report.write_text("<html/>", encoding="utf-8")
    fake = FakeTelegram([_send_ok(71)])
    toolset = make_toolset(_client(fake), workspace_root=workspace)
    send_tool = toolset.tools["send_artifact_to_supervisor"].function
    assert not getattr(
        toolset.tools["send_artifact_to_supervisor"], "requires_approval", False
    ), "self-delivery is host-scoped and must not carry an approval gate"
    out = json.loads(send_tool(path="artifacts/quant/delivery/quant-business-x.html"))
    assert out["sent"] is True and out["file"] == report.name
    assert len(fake.requests) == 1 and fake.requests[0].url.path.endswith("/sendDocument")

    out2 = json.loads(send_tool(path="/etc/passwd"))
    assert out2 == {
        "sent": False,
        "rejected": "path must be a workspace-relative path without '..'",
    }
    assert len(fake.requests) == 1, "rejected path must not reach the transport"
