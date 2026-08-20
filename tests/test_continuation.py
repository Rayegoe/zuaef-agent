"""Shared continuation seam tests — SPEC v0.3 §24–§25, §77.

The CLI and the Gateway must execute the same resume orchestration
(``resume_paused_run``); these tests prove the contract itself: a paused run
is resumed from its PauseReceipt + StepPersistence history + frozen
CompositionSnapshot, with approve/deny semantics, and that the CLI delegates
rather than reimplementing.

The fixture plugins under ``tests/fixture_plugins/`` are real importable
modules whose ``zuaef.plugins`` entry points are constructed here (hermetic:
nothing is pip-installed). ``FunctionModel`` is injected through
``core.resolve_model`` because ``resume_paused_run`` builds the resumed agent
itself — an ``agent.override`` on the paused agent would not reach it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import EntryPoint
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent import core as core_module
from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.continuation import resume_paused_run
from zuaef_agent.models import CoreDeps, RunReceipt
from zuaef_agent.receipt_store import ReceiptStore
from zuaef_agent.runtime import PausedRun, TerminalRun, execute_run

models.ALLOW_MODEL_REQUESTS = False


def _ep(module: str, name: str, factory: str = "create_plugin") -> EntryPoint:
    return EntryPoint(
        name=name,
        value=f"fixture_plugins.{module}:{factory}",
        group="zuaef.plugins",
    )


DISCOVER = {
    "fixture-ace-writing": _ep("writing", "fixture-ace-writing"),
    "hardware-scout": _ep("hardware", "hardware-scout"),
    "capability-plugin": _ep("capability", "capability-plugin"),
    "conflict-plugin": _ep("conflict", "conflict-plugin"),
    "broken-plugin": _ep("broken", "broken-plugin"),
    "invalid-bundle": _ep("broken", "invalid-bundle", "create_invalid"),
    "never-enabled": _ep("never_enabled", "never-enabled"),
}

VERSIONS = {
    "fixture-ace-writing": "0.2.1",
    "hardware-scout": "0.1.0",
    "capability-plugin": "0.3.0",
    "conflict-plugin": "0.0.1",
    "broken-plugin": "0.0.1",
    "invalid-bundle": "0.0.1",
    "never-enabled": "0.0.1",
}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


WRITING_PROFILE = """\
schema = 1
name = "writing"

[[plugins]]
id = "fixture-ace-writing"
allow_capabilities = false

[plugins.config]
ace_root = "/v1"
"""


def _write_profile(
    tmp_path: Path,
    name: str,
    text: str = WRITING_PROFILE,
) -> Path:
    config_root = tmp_path / "config"
    directory = config_root / "profiles"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


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


def _has_tool_return(messages) -> bool:
    return any(
        getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
        for message in messages
        for part in getattr(message, "parts", [])
    )


def _return_outcomes(messages) -> list[tuple[str, str]]:
    """(tool_name, content) of every resolved call the model observed — with a
    natural-text terminal this is the structural view of what an approval did."""
    return [
        (getattr(part, "tool_name", ""), str(getattr(part, "content", "")))
        for message in messages
        for part in getattr(message, "parts", [])
        if getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
    ]


def _model_fn(seen: dict):
    def fn(messages, info):
        seen["returns"] = _return_outcomes(messages)
        if not _has_tool_return(messages):
            return ModelResponse(
                parts=[ToolCallPart("publish_article", {"article_id": "a1"})]
            )
        return ModelResponse(parts=[TextPart(content="article handled")])

    return fn


def _pause_through_profile(tmp_path: Path, monkeypatch, seen: dict):
    """Pause a real run through the fixture writing profile (approval tool)."""
    monkeypatch.setattr(
        core_module, "resolve_model", lambda settings: FunctionModel(_model_fn(seen))
    )
    settings = _settings(tmp_path)
    config_root = _write_profile(tmp_path, "writing")
    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="writing",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=_vf,
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    paused = execute_run(
        agent,
        deps,
        prompt="publish the article",
        settings=settings,
        run_id=run_id,
        composition=snapshot,
    )
    assert isinstance(paused, PausedRun)
    assert paused.pause_receipt.pending_approvals[0]["tool_name"] == "publish_article"
    return settings, paused


def test_resume_approve_executes_tool_and_settles(tmp_path: Path, monkeypatch):
    seen: dict = {}
    settings, paused = _pause_through_profile(tmp_path, monkeypatch, seen)

    outcome = resume_paused_run(
        settings,
        paused.pause_receipt.run_id,
        decision="approve",
        discover=lambda: DISCOVER,
        version_for=_vf,
    )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.continued_from_run_id == paused.pause_receipt.run_id
    assert outcome.receipt.conversation_id == paused.pause_receipt.conversation_id
    assert any(
        name == "publish_article" and "published a1" in content
        for name, content in seen["returns"]
    )
    settled = [
        e
        for e in outcome.receipt.tool_effect_facts
        if e.tool_name == "publish_article"
    ]
    assert settled and settled[0].status == "completed"


def test_resume_deny_delivers_tool_denied_no_execution(tmp_path: Path, monkeypatch):
    seen: dict = {}
    settings, paused = _pause_through_profile(tmp_path, monkeypatch, seen)

    outcome = resume_paused_run(
        settings,
        paused.pause_receipt.run_id,
        decision="deny",
        reason="operator refused",
        discover=lambda: DISCOVER,
        version_for=_vf,
    )

    assert isinstance(outcome, TerminalRun)
    assert not any(
        name == "publish_article" and "published a1" in content
        for name, content in seen["returns"]
    )
    assert not [
        e
        for e in outcome.receipt.tool_effect_facts
        if e.tool_name == "publish_article" and e.status == "completed"
    ]


def test_resume_rejects_non_paused_receipt(tmp_path: Path):
    settings = _settings(tmp_path)
    receipt = RunReceipt(
        run_id="r1",
        model="test",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execution_state="completed",
        outcome="done",
    )
    ReceiptStore(settings.state_root).write(receipt)

    with pytest.raises(ValueError, match="not paused"):
        resume_paused_run(settings, "r1", decision="approve")


def test_resume_uses_frozen_composition_ignoring_mutable_profile(
    tmp_path: Path, monkeypatch
):
    """After the pause, the profile mutates (config change) and then vanishes
    entirely; resume must still rebuild from the frozen snapshot."""
    seen: dict = {}
    settings, paused = _pause_through_profile(tmp_path, monkeypatch, seen)
    frozen_composition_id = paused.pause_receipt.composition.composition_id

    # Mutate the profile config, then delete the profile file completely.
    _write_profile(
        tmp_path,
        "writing",
        text='schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\nace_root = "/mutated"\n',
    )
    (tmp_path / "config" / "profiles" / "writing.toml").unlink()

    outcome = resume_paused_run(
        settings,
        paused.pause_receipt.run_id,
        decision="approve",
        discover=lambda: DISCOVER,
        version_for=_vf,
    )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.composition is not None
    assert outcome.receipt.composition.composition_id == frozen_composition_id
    assert outcome.receipt.composition.plugins[0].config == {"ace_root": "/v1"}


def test_resume_version_drift_fails_before_model_request(
    tmp_path: Path, monkeypatch
):
    seen: dict = {}
    settings, paused = _pause_through_profile(tmp_path, monkeypatch, seen)

    drifted = {
        name: ("99.0.0" if name == "fixture-ace-writing" else version)
        for name, version in VERSIONS.items()
    }

    with pytest.raises(ValueError, match="version"):
        resume_paused_run(
            settings,
            paused.pause_receipt.run_id,
            decision="approve",
            discover=lambda: DISCOVER,
            version_for=lambda ep: drifted[ep.name],
        )
