"""Behavioral checks of the installed native coding composition."""
import asyncio
import subprocess
from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness import FileSystem, RepoContext, Shell
from zuaef_coding.plugin import build_plugin

from zuaef_agent.composition import (
    build_profile_agent,
    installed_plugins,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginEnv

ROOT = Path(__file__).parents[1]


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "AGENTS.md").write_text("Preserve unrelated edits.\n")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.1'\n")
    return root


def bundle(repo, **config):
    return build_plugin(PluginEnv("coding", "0.1.0", repo.parent, repo.parent / "state"),
                        {"repo_root": str(repo), **config})


@pytest.mark.parametrize("config", [
    {"unknown": True}, {"code_mode": "true"}, {"allow_codex": 1},
    {"allow_pi": None}, {"allow_local_commit": "false"}, {"output_language": 42},
])
def test_invalid_config(repo, config):
    with pytest.raises(CompositionError):
        bundle(repo, **config)


def test_root_fails_closed(tmp_path, repo):
    missing = tmp_path / "missing"
    with pytest.raises(CompositionError):
        bundle(missing)
    assert not missing.exists()
    (repo / "AGENTS.md").unlink()
    with pytest.raises(CompositionError):
        bundle(repo)


def test_non_git_and_nested_root_rejected(tmp_path, repo):
    for root in (tmp_path / "plain", repo / "nested"):
        root.mkdir()
        (root / "AGENTS.md").touch()
        (root / "pyproject.toml").touch()
        with pytest.raises(CompositionError):
            bundle(root)


def test_git_worktree_supported(repo, tmp_path):
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
    worktree = tmp_path / "worktree"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree)],
                   check=True, capture_output=True)
    assert (worktree / ".git").is_file()
    assert bundle(worktree).capabilities


@pytest.mark.parametrize("mode", [False, True])
def test_real_tools_edit_test_and_complete(repo, mode, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-sentinel")
    monkeypatch.setenv("FEISHU_APP_SECRET", "test-only-sentinel")
    b = bundle(repo, code_mode=mode)
    turns = []

    async def scripted(messages, info):
        names = [t.name for t in info.function_tools]
        assert len(names) == len(set(names))
        assert "repo_run_command" in names and "run_command" in names
        assert ("run_code" in names) is mode
        turns.append(names)
        if len(turns) == 1:
            call = ToolCallPart("run_code", {"code": "await repo_write_file(path='answer.py', content='ANSWER = 42\\n')"}) if mode else ToolCallPart("repo_write_file", {"path": "answer.py", "content": "ANSWER = 42\n"})
            return ModelResponse(parts=[call])
        if len(turns) == 2:
            return ModelResponse(parts=[ToolCallPart("repo_run_command", {"command":
                'python -c "from answer import ANSWER; assert ANSWER == 42; import os; assert not os.getenv(\'OPENAI_API_KEY\'); assert not os.getenv(\'FEISHU_APP_SECRET\')"'})])
        if len(turns) == 3:
            return ModelResponse(parts=[ToolCallPart("run_command", {"command":
                'python -c "import os; assert not os.getenv(\'OPENAI_API_KEY\'); assert not os.getenv(\'FEISHU_APP_SECRET\')"'})])
        # Real tool errors must fail the assertion rather than allowing a fake completion.
        transcript = str(messages)
        assert "exit code: 1" not in transcript.lower()
        assert "Traceback" not in transcript
        return ModelResponse(parts=[TextPart("completed")])

    a = Agent(FunctionModel(scripted), capabilities=[FileSystem(repo.parent), *b.capabilities],
              toolsets=list(b.toolsets))
    result = asyncio.run(a.run("Create answer.py and validate it."))
    assert result.output == "completed"
    assert (repo / "answer.py").read_text() == "ANSWER = 42\n"
    assert len(turns) == 4


@pytest.mark.parametrize("path", [".env", ".env.local", "nested/.env", "private.key",
                                  "private.pem", "secrets.txt", ".git/config", "../outside"])
def test_repo_files_deny_secret_and_escape(repo, path):
    b = bundle(repo)
    fs = b.capabilities[1].wrapped.get_toolset()
    async def check():
        with pytest.raises((ModelRetry, PermissionError)):
            await fs.read_file(path)
        with pytest.raises((ModelRetry, PermissionError)):
            await fs.write_file(path, "blocked")
    asyncio.run(check())


def test_secret_symlink_denied(repo):
    (repo / ".env").write_text("test-only-secret")
    (repo / "alias.txt").symlink_to(repo / ".env")
    fs = bundle(repo).capabilities[1].wrapped.get_toolset()
    with pytest.raises((ModelRetry, PermissionError)):
        asyncio.run(fs.read_file("alias.txt"))


def _coding_repo_context(b):
    matches = [c for c in b.capabilities if isinstance(c, RepoContext)]
    assert len(matches) == 1
    return matches[0]


def test_repo_context_narrowed_to_agents_authority(repo):
    # Spec v0.1 §12.A: AGENTS.md stays always-on authority; README is retrieval
    # material and the asset inventory is a startup ritual, not a coding need.
    rc = _coding_repo_context(bundle(repo))
    assert tuple(rc.filenames) == ("AGENTS.md",)
    assert rc.expose_inventory_tool is False
    # repo FileSystem/Shell remain present beside it.
    caps = bundle(repo).capabilities

    def _is_shell(c):
        return isinstance(c, Shell) or getattr(c, "wrapped", None).__class__ is Shell

    assert sum(_is_shell(c) for c in caps) == 2  # workspace + repo Shell
    assert any(getattr(c, "wrapped", None).__class__.__name__ == "FileSystem"
               for c in caps)


def test_always_on_discipline_without_skill_load(repo):
    # Spec v0.1 §12.B/§12.C: the mandatory discipline lives in the always-on
    # plugin instructions; deferred skill discovery is never required for it.
    b = bundle(repo)
    lowered = str(b.toolsets[0]._instructions).lower()
    for clause in (
        "already supplied by repocontext",
        "do not create, read or maintain a plan",
        "do not inventory agent capabilities",
        "planning only for genuinely multi-step work",
        "no more than two files",
        "as soon as you have enough evidence",
        "on-demand resources, not startup steps",
        "never push",
        "do not read credentials",
        "bare allowed command names",
        "changed, tested, committed and activation",
        "local commits allowed: false",
    ):
        assert clause in lowered, clause
    assert "load the coding skill" not in lowered
    assert b.skill_dirs  # optional deeper skill material stays available


def test_cli_flags_and_commit_guidance(repo):
    b = bundle(repo, allow_codex=True, allow_pi=True, allow_local_commit=True)
    assert {"codex", "pi"} <= set(b.capabilities[0].allowed_commands)
    assert "Local commits allowed: True" in str(b.toolsets[0]._instructions)
    assert "systemctl" not in b.capabilities[0].allowed_commands
    assert "codex" not in bundle(repo).capabilities[0].allowed_commands


def test_installed_profile_and_other_profiles(tmp_path, monkeypatch):
    assert ("coding", "0.1.0") in installed_plugins()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-only")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("YDC_API_KEY", "test-only")
    # Host ceilings ON so the effective policy discriminates the profile's
    # own requests (Spec v0.1 §12.D): ToolSearch/ConversationSearch denied,
    # context controls kept.
    settings = AgentSettings(model="test", workspace_root=tmp_path / "workspace",
                             runtime_state_root=tmp_path / "state",
                             enable_tool_search=True, enable_conversation_search=True,
                             enable_context_controls=True)
    agent, snap = build_profile_agent(settings, profile="coding", config_root=ROOT)
    assert snap.plugins[0].id == "coding"
    assert snap.generalist["enable_shell"] is False
    assert snap.generalist["enable_tool_search"] is False
    assert snap.generalist["enable_conversation_search"] is False
    assert snap.generalist["enable_context_controls"] is True
    # Full core combination actually collects schemas and completes, offline.
    seen_tools: set[str] = set()

    async def scripted(messages, info):
        seen_tools.update(t.name for t in info.function_tools)
        assert "repo_run_command" in {t.name for t in info.function_tools}
        return ModelResponse(parts=[TextPart("done")])
    with agent.override(model=FunctionModel(scripted)):
        assert asyncio.run(agent.run("check", deps=CoreDeps(
            workspace_root=settings.workspace_root, run_id="coding-composition"))).output == "done"
    # No inventory startup ritual on the composed coding surface (§12.A).
    assert "inventory_agent_context" not in seen_tools
    for name in ("quant-decision", "general-knowledge-worker"):
        other = resolve_profile(name, settings, config_root=ROOT)
        assert "coding" not in {ref.id for ref in other.plugins}


def test_skill_md_mandates_targeted_pytest_before_local_commit():
    skill = ROOT / "plugins/zuaef-coding/zuaef_coding/skills/coding/SKILL.md"
    assert skill.is_file()
    assert "targeted pytest" in skill.read_text(encoding="utf-8")
