"""Composition and capability-truth acceptance for the general knowledge
worker profile (spec pack 05 A1-A5, M5/M6 behavioral gates).

The plugin under test is the real installed ``zuaef-knowledge-worker``
distribution; profiles resolve from the repository ``profiles/`` directory
unless a synthetic config root is used.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.composition import (
    build_profile_agent,
    installed_plugins,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError
from zuaef_agent.runtime import TerminalRun, execute_run

REPO_ROOT = Path(__file__).parents[1]
PROFILE = "general-knowledge-worker"

DOCUMENT_TOOLS = {
    "inspect_document",
    "read_document",
    "search_document",
    "search_documents",
}
RESEARCH_TOOLS = {"web_search", "get_page", "answer", "research", "finance_research"}


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


def _config_root() -> Path:
    return REPO_ROOT


def test_plugin_is_discoverable_after_install():
    """A1: clean install exposes the entry point (uv sync installed it)."""
    assert ("knowledge-worker", "0.1.0") in installed_plugins()


def test_unrelated_profiles_do_not_activate_it(tmp_path, monkeypatch):
    """A2: installing never activates; existing profiles stay unchanged."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-only")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("ZUAEF_WORDPRESS_USERNAME", "test-only")
    monkeypatch.setenv("ZUAEF_WORDPRESS_APP_PASSWORD", "test-only")
    settings = _settings(tmp_path)
    quant = resolve_profile("quant-decision", settings, config_root=_config_root())
    assert [ref.id for ref in quant.plugins] == ["quant", "telegram"]

    wordpress = resolve_profile(
        "wordpress-operator", settings, config_root=_config_root()
    )
    assert "knowledge-worker" not in {ref.id for ref in wordpress.plugins}


def test_removing_allow_capabilities_fails_before_model_work(tmp_path):
    """A3: capabilities are denied unless the profile explicitly allows them."""
    settings = _settings(tmp_path)
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "kw-nocaps.toml").write_text(
        'schema = 1\nname = "kw-nocaps"\n\n[[plugins]]\nid = "knowledge-worker"\n',
        encoding="utf-8",
    )
    with pytest.raises(CompositionError, match="allow_capabilities"):
        resolve_profile("kw-nocaps", settings, config_root=config_root)


def test_profile_builds_plugin_search_with_core_web_disabled(
    tmp_path, monkeypatch
):
    """A4: the build composes You.com tools and document tools while the
    core WebSearch/WebFetch/Shell surface stays unauthorized (no name
    collision — Agent construction materializes the capability toolsets)."""
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    agent, snapshot = build_profile_agent(
        settings,
        run_id=uuid4().hex,
        profile=PROFILE,
        config_root=_config_root(),
    )

    effective = snapshot.generalist or {}
    assert effective["enable_web_search"] is False
    assert effective["enable_web_fetch"] is False
    assert effective["enable_shell"] is False
    assert effective["enable_repo_context"] is False

    capability_names = {
        type(capability).__name__
        for capability in agent.root_capability.capabilities
    }
    assert {"YouSearch", "YouResearch"} <= capability_names
    assert "WebSearch" not in capability_names
    assert "WebFetch" not in capability_names
    assert "Shell" not in capability_names

    from pydantic_ai import RunContext
    from pydantic_ai.usage import RunUsage

    ctx = RunContext(
        deps=CoreDeps(workspace_root=settings.workspace_root, run_id=""),
        usage=RunUsage(),
        prompt="",
        model=None,
    )
    user_names: set[str] = set()
    from pydantic_ai import FunctionToolset

    for toolset in agent.toolsets:
        if type(toolset) is FunctionToolset:
            user_names |= set(toolset.tools)
    assert DOCUMENT_TOOLS <= user_names
    assert not (DOCUMENT_TOOLS & RESEARCH_TOOLS)
    assert ctx is not None  # composed surface needs no run to list plain tools


def test_existing_profiles_still_validate_and_build(tmp_path, monkeypatch):
    """A5: vertical deployments are untouched by the new workspace member."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-only")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    monkeypatch.setenv("ZUAEF_WORDPRESS_USERNAME", "test-only")
    monkeypatch.setenv("ZUAEF_WORDPRESS_APP_PASSWORD", "test-only")
    settings = _settings(tmp_path)
    for name in ("quant-decision", "wordpress-operator"):
        snapshot = resolve_profile(name, settings, config_root=_config_root())
        assert snapshot.profile == name
    agent, _ = build_profile_agent(
        settings,
        run_id=uuid4().hex,
        profile="quant-decision",
        config_root=_config_root(),
    )
    assert agent is not None


def test_unknown_config_key_fails_composition(tmp_path, monkeypatch):
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "kw-typo.toml").write_text(
        'schema = 1\nname = "kw-typo"\n\n[[plugins]]\nid = "knowledge-worker"\n'
        "allow_capabilities = true\n\n[plugins.config]\nserch_results = 6\n",
        encoding="utf-8",
    )
    with pytest.raises(CompositionError, match="unknown key"):
        resolve_profile("kw-typo", settings, config_root=config_root)


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"search_results": 21}, "search_results"),
        ({"search_results": 0}, "must be"),
        ({"search_mode": "books"}, "search_mode"),
        ({"research_effort": "frontier"}, "research_effort"),
        ({"finance_effort": "lite"}, "finance_effort"),
        ({"page_chars": 0}, "page_chars"),
        ({"research_enabled": "yes"}, "boolean"),
        ({"output_language": 5}, "output_language"),
    ],
)
def test_config_contract_is_enforced(
    tmp_path, monkeypatch, config: dict, message: str
):
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    body = "\n".join(
        f"{key} = {_toml_value(value)}" for key, value in config.items()
    )
    (config_root / "profiles" / "kw-bad.toml").write_text(
        'schema = 1\nname = "kw-bad"\n\n[[plugins]]\nid = "knowledge-worker"\n'
        "allow_capabilities = true\n\n[plugins.config]\n"
        + body
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(CompositionError, match=message):
        resolve_profile("kw-bad", settings, config_root=config_root)


def test_research_disabled_drops_you_research(tmp_path, monkeypatch):
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "kw-noresearch.toml").write_text(
        'schema = 1\nname = "kw-noresearch"\n\n[[plugins]]\n'
        'id = "knowledge-worker"\nallow_capabilities = true\n\n'
        "[plugins.config]\nresearch_enabled = false\n",
        encoding="utf-8",
    )
    agent, _snapshot = build_profile_agent(
        settings, run_id=uuid4().hex, profile="kw-noresearch", config_root=config_root
    )
    names = {type(capability).__name__ for capability in agent.root_capability.capabilities}
    assert "YouSearch" in names and "YouResearch" not in names


def test_plugin_skill_dir_reaches_the_bundle():
    from zuaef_knowledge_worker import build_plugin

    from zuaef_agent.plugin_api import PluginEnv

    env = PluginEnv(
        plugin_id="knowledge-worker",
        plugin_version="0.1.0",
        workspace_root=Path("."),
        state_root=Path("."),
    )
    bundle = build_plugin(env, {"research_enabled": False})
    assert len(bundle.skill_dirs) == 1
    skill = bundle.skill_dirs[0] / "knowledge-worker" / "SKILL.md"
    assert skill.is_file()


def test_capability_truth_guidance_is_composed(tmp_path, monkeypatch):
    """M6 static guard: the truth contract is present in the surfaces the
    model actually sees (skill guidance + core instructions). A Skill being
    present must never read as execution authority."""
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    agent, _ = build_profile_agent(
        settings, run_id=uuid4().hex, profile=PROFILE, config_root=_config_root()
    )
    from zuaef_agent.core import CORE_INSTRUCTIONS

    assert (
        "Do not claim an external action happened unless the corresponding"
        in CORE_INSTRUCTIONS
    )
    skill = (
        Path(__file__).parents[1]
        / "plugins/zuaef-knowledge-worker/zuaef_knowledge_worker/skills"
        / "knowledge-worker/SKILL.md"
    )
    text = skill.read_text(encoding="utf-8")
    assert "Never claim that code, deployment" in text
    assert "does not itself grant" in text
    assert "untrusted evidence" in text
    assert "artifacts/knowledge-worker" in text
    # Always-on plugin guidance (reproduced field failure 2026-09-08: the
    # model claimed it could execute bmad-build-auto, whose workflow needs
    # shell commands this profile does not compose). The truth contract must
    # be visible even when no deferred Skill has been loaded.
    from zuaef_knowledge_worker.document_tools import make_document_toolset

    toolset = make_document_toolset(
        workspace_root=settings.workspace_root, chunk_chars=100, max_bytes=1000
    )
    toolset_instructions = "\n".join(toolset._instructions)
    assert "Execution truth" in toolset_instructions
    assert agent is not None


def test_end_to_end_document_run_through_runtime(tmp_path, monkeypatch):
    """M5/M7 seam: the composed profile executes a real document read inside
    execute_run; the receipt records the completed tool effect."""
    monkeypatch.setenv("YDC_API_KEY", "test-only-not-a-credential")
    settings = _settings(tmp_path)
    inbox = settings.workspace_root / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "note.txt").write_text("PIT means performance inspection test.\n", encoding="utf-8")

    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings, run_id=run_id, profile=PROFILE, config_root=_config_root()
    )
    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(), run_id=run_id
    )

    def scripted(messages, info):
        if any(isinstance(part, ToolReturnPart) for m in messages for part in getattr(m, "parts", [])):
            return ModelResponse(parts=[TextPart(content="PIT means performance inspection test.")])
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="read_document",
                    args={"path": "inbox/note.txt"},
                    tool_call_id="call-1",
                )
            ]
        )

    with agent.override(model=FunctionModel(scripted)):
        outcome = execute_run(
            agent,
            deps,
            prompt="Read inbox/note.txt",
            settings=settings,
            run_id=run_id,
            composition=snapshot,
        )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.state == "terminal"
    read_facts = [
        fact
        for fact in outcome.receipt.tool_effect_facts
        if fact.tool_name == "read_document"
    ]
    assert [fact.status for fact in read_facts] == ["completed"]
    assert "performance inspection test" in (outcome.presentation or "")
