from __future__ import annotations

import subprocess
import sys
from datetime import UTC

import pytest

from zuaef_agent import cli
from zuaef_agent import config as config_module
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import PauseReceipt, RunSummary
from zuaef_agent.runtime import PausedRun, TerminalRun


def test_exit_code_mapping(tmp_path, monkeypatch):
    from datetime import datetime

    from zuaef_agent.models import RunReceipt

    now = datetime.now(UTC)

    def make(status: str) -> TerminalRun:
        summary = RunSummary(status=status, outcome="x")  # type: ignore[arg-type]
        receipt = RunReceipt(
            run_id="r",
            model="m",
            started_at=now,
            finished_at=now,
            status=status,  # type: ignore[arg-type]
            summary=summary,
        )
        return TerminalRun(summary=summary, receipt=receipt)

    assert cli._outcome_exit_code(make("completed")) == cli.EXIT_COMPLETED
    assert cli._outcome_exit_code(make("partial")) == cli.EXIT_PARTIAL
    assert cli._outcome_exit_code(make("blocked")) == cli.EXIT_BLOCKED

    pause = PauseReceipt(
        run_id="r",
        conversation_id="c",
        model="m",
        started_at=now,
        finished_at=now,
    )
    paused = PausedRun(requests=None, message_history=[], conversation_id="c", pause_receipt=pause)
    assert cli._outcome_exit_code(paused) == cli.EXIT_PAUSED
    assert cli.EXIT_PAUSED not in (cli.EXIT_COMPLETED, cli.EXIT_PARTIAL, cli.EXIT_BLOCKED)


def test_invalid_zero_limit_is_a_process_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys, "argv", ["zuaef-agent", "run", "task", "--request-limit", "0", "--workspace", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == cli.EXIT_PROCESS_ERROR


def test_cli_run_prints_receipt_and_exits_by_status(monkeypatch, tmp_path, capsys):
    from datetime import datetime

    from zuaef_agent.models import RunReceipt

    now = datetime.now(UTC)
    summary = RunSummary(status="completed", outcome="done")
    receipt = RunReceipt(
        run_id="r1",
        model="m",
        started_at=now,
        finished_at=now,
        status="completed",
        summary=summary,
    )
    monkeypatch.setattr(sys, "argv", ["zuaef-agent", "run", "task", "--workspace", str(tmp_path)])
    monkeypatch.setattr(cli, "run_task", lambda task, settings=None: TerminalRun(summary=summary, receipt=receipt))
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == cli.EXIT_COMPLETED
    assert '"state": "terminal"' in capsys.readouterr().out


def test_lazy_provider_import_for_normal_model():
    """CAP-5: a normal model id must not import OpenAI-specific modules."""
    code = (
        "import sys; "
        "from zuaef_agent.config import AgentSettings; "
        "from zuaef_agent.providers import resolve_model; "
        "m = resolve_model(AgentSettings()); "
        "assert isinstance(m, str), m; "
        "assert 'pydantic_ai.models.openai' not in sys.modules; "
        "assert 'openai' not in sys.modules; "
        "print('ok')"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_compat_endpoint_still_resolves(tmp_path):
    from pydantic_ai.models.openai import OpenAIChatModel

    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="http://localhost:8000/v1",
        compat_model="local-model",
        workspace_root=tmp_path / "w",
    )
    model = resolve_model(settings)
    assert isinstance(model, OpenAIChatModel)


def test_product_research_env_is_loaded_from_project_root(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "LLM_API_BASE=https://compatible.example/v1\n"
        "LLM_API_KEY=secret-from-dotenv\n"
        "LLM_MODEL=compatible-model\n"
        "LLM_API_MODE=chat\n"
        "LLM_ENABLE_THINKING=false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "PROJECT_ROOT", project_root)
    for name in (
        "ZUAEF_OPENAI_BASE_URL",
        "ZUAEF_OPENAI_API_KEY",
        "ZUAEF_COMPAT_MODEL",
        "ZUAEF_OPENAI_API_MODE",
        "LLM_API_BASE",
        "LLM_API_KEY",
        "LLM_MODEL",
        "LLM_API_MODE",
        "LLM_ENABLE_THINKING",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = AgentSettings.from_env()

    assert settings.openai_base_url == "https://compatible.example/v1"
    assert settings.openai_api_key == "secret-from-dotenv"
    assert settings.compat_model == "compatible-model"
    assert settings.openai_api_mode == "chat"
    assert settings.openai_enable_thinking is False


def test_zuaef_provider_env_takes_precedence_over_product_research_env(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "LLM_API_BASE=https://fallback.example/v1\n"
        "LLM_API_KEY=fallback-key\n"
        "LLM_MODEL=fallback-model\n"
        "LLM_API_MODE=responses\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "PROJECT_ROOT", project_root)
    monkeypatch.setenv("ZUAEF_OPENAI_BASE_URL", "https://preferred.example/v1")
    monkeypatch.setenv("ZUAEF_OPENAI_API_KEY", "preferred-key")
    monkeypatch.setenv("ZUAEF_COMPAT_MODEL", "preferred-model")
    monkeypatch.setenv("ZUAEF_OPENAI_API_MODE", "chat")

    settings = AgentSettings.from_env()

    assert settings.openai_base_url == "https://preferred.example/v1"
    assert settings.openai_api_key == "preferred-key"
    assert settings.compat_model == "preferred-model"
    assert settings.openai_api_mode == "chat"


def test_compat_provider_ignores_invalid_host_proxy(tmp_path, monkeypatch):
    from pydantic_ai.models.openai import OpenAIChatModel

    from zuaef_agent.providers import resolve_model

    monkeypatch.setenv("ALL_PROXY", "socks://127.0.0.1:7897")
    settings = AgentSettings(
        openai_base_url="https://compatible.example/v1",
        openai_api_key="test-key",
        compat_model="compatible-model",
        workspace_root=tmp_path / "w",
    )

    model = resolve_model(settings)

    assert isinstance(model, OpenAIChatModel)


def test_responses_mode_resolves_explicitly(tmp_path):
    from pydantic_ai.models.openai import OpenAIResponsesModel

    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="https://api.openai.com/v1",
        openai_api_key="test-key",
        compat_model="gpt-test",
        openai_api_mode="responses",
        workspace_root=tmp_path / "w",
    )

    model = resolve_model(settings)

    assert isinstance(model, OpenAIResponsesModel)


def test_chat_mode_forwards_explicit_thinking_toggle(tmp_path):
    from pydantic_ai.models.openai import OpenAIChatModel

    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="https://api.deepseek.com",
        openai_api_key="test-key",
        compat_model="deepseek-v4-flash",
        openai_enable_thinking=False,
        workspace_root=tmp_path / "w",
    )

    model = resolve_model(settings)

    assert isinstance(model, OpenAIChatModel)
    assert model.settings == {"extra_body": {"thinking": {"type": "disabled"}}}


def test_deepseek_uses_official_provider_profile(tmp_path):
    """T005: DeepSeek capability flags come from the official
    ``DeepSeekProvider.model_profile`` — ZUAEF no longer copies model flags."""
    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="https://api.deepseek.com",
        openai_api_key="test-key",
        compat_model="deepseek-chat",
        workspace_root=tmp_path / "w",
    )
    model = resolve_model(settings)

    assert model.system == "deepseek"  # official DeepSeekProvider
    profile = dict(model.profile)
    # Flags the official deepseek_model_profile owns (previously hand-copied):
    assert profile["openai_chat_thinking_field"] == "reasoning_content"
    assert profile["openai_chat_send_back_thinking_parts"] == "field"
    assert profile["supports_json_object_output"] is True
    assert profile["openai_supports_tool_choice_required"] is True


def test_deepseek_v4_does_not_force_tool_choice(tmp_path):
    """The official DeepSeek profile is what forbids forced tool_choice on v4."""
    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="https://api.deepseek.com",
        openai_api_key="test-key",
        compat_model="deepseek-v4-flash",
        workspace_root=tmp_path / "w",
    )
    model = resolve_model(settings)
    assert dict(model.profile)["openai_supports_tool_choice_required"] is False


def test_generic_endpoint_uses_official_default_profile(tmp_path):
    """T005: generic OpenAI-compatible endpoints rely on the official profile —
    the locally copied capability flags are gone from AgentSettings."""
    from pydantic_ai.models.openai import OpenAIChatModel

    from zuaef_agent.providers import resolve_model

    settings = AgentSettings(
        openai_base_url="http://localhost:8000/v1",
        openai_api_key="test-key",
        compat_model="local-model",
        openai_api_mode="chat",
        workspace_root=tmp_path / "w",
    )
    model = resolve_model(settings)
    assert isinstance(model, OpenAIChatModel)
    # No local capability-flag fields survive on the settings object.
    assert not hasattr(settings, "openai_strict_tool_definitions")
