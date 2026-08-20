"""Gateway runtime bridge tests — SPEC v0.3 §76.

FunctionModel drives deterministic branches; ``resolve_model`` is patched so
the agents the bridge builds use it. All runs flow through the real
``build_profile_agent`` / ``execute_run`` / ``resume_paused_run`` seams.
"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent import core as core_module
from zuaef_agent.composition import CompositionError
from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.bridge import (
    project_prompt,
    resume_for_surface,
    start_profile_run,
    validate_profile,
)
from zuaef_agent.gateway.models import AttachmentRef, InboundEnvelope
from zuaef_agent.runtime import PausedRun, TerminalRun

models.ALLOW_MODEL_REQUESTS = False

EP = EntryPoint(
    name="fixture-ace-writing",
    value="fixture_plugins.writing:create_plugin",
    group="zuaef.plugins",
)
DISCOVER = {"fixture-ace-writing": EP}
VERSIONS = {"fixture-ace-writing": "0.2.1"}


def _vf(ep: EntryPoint) -> str:
    return VERSIONS[ep.name]


PROFILE = 'schema = 1\nname = "writing"\n\n[[plugins]]\nid = "fixture-ace-writing"\n\n[plugins.config]\nace_root = "/v1"\n'


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


def _write_profile(tmp_path: Path, name: str, text: str = PROFILE) -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / f"{name}.toml").write_text(text, encoding="utf-8")
    return config_root


def _config_root(tmp_path: Path) -> Path:
    return tmp_path / "config"


def _final(status="completed", outcome="done"):
    return ModelResponse(parts=[TextPart(content=outcome)])


def _use_model(monkeypatch, fn):
    monkeypatch.setattr(core_module, "resolve_model", lambda settings: FunctionModel(fn))


def _build_with_discover(settings, *, run_id=None, profile=None, snapshot=None, config_root=None, **_):
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


def test_start_profile_run_completes_and_propagates_identity(
    tmp_path: Path, monkeypatch
):
    _write_profile(tmp_path, "writing")
    _use_model(monkeypatch, lambda messages, info: _final())
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent",
        lambda settings, run_id=None, profile=None, **kw: _build_with_discover(
            settings, run_id=run_id, profile=profile, **kw
        ),
    )

    outcome = start_profile_run(
        settings=settings,
        profile="writing",
        prompt="publish",
        conversation_id="conv-gw-1",
        config_root=_config_root(tmp_path),
    )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.conversation_id == "conv-gw-1"
    assert outcome.receipt.composition is not None
    assert outcome.receipt.composition.profile == "writing"
    assert outcome.receipt.composition.plugins[0].id == "fixture-ace-writing"


def test_start_profile_run_without_profile_uses_core_agent(
    tmp_path: Path, monkeypatch
):
    _use_model(monkeypatch, lambda messages, info: _final())
    settings = _settings(tmp_path)

    outcome = start_profile_run(
        settings=settings,
        profile=None,
        prompt="hello",
        conversation_id="conv-gw-2",
    )

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.composition is None
    assert outcome.receipt.conversation_id == "conv-gw-2"


def test_pause_then_shared_resume_preserves_frozen_composition(
    tmp_path: Path, monkeypatch
):
    _write_profile(tmp_path, "writing")

    def fn(messages, info):
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

    _use_model(monkeypatch, fn)
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent",
        lambda settings, run_id=None, profile=None, **kw: _build_with_discover(
            settings, run_id=run_id, profile=profile, **kw
        ),
    )

    paused = start_profile_run(
        settings=settings,
        profile="writing",
        prompt="publish article",
        conversation_id="conv-gw-3",
        config_root=_config_root(tmp_path),
    )
    assert isinstance(paused, PausedRun)
    assert paused.pause_receipt.pending_approvals[0]["tool_name"] == "publish_article"

    # Mutate + remove the profile: resume must use the frozen snapshot.
    _write_profile(tmp_path, "writing", PROFILE.replace("/v1", "/mutated"))
    (tmp_path / "config" / "profiles" / "writing.toml").unlink()
    monkeypatch.setattr(
        "zuaef_agent.continuation.build_profile_agent",
        lambda settings, run_id=None, profile=None, snapshot=None, **kw: _build_with_discover(
            settings, run_id=run_id, profile=profile, snapshot=snapshot, **kw
        ),
    )

    terminal = resume_for_surface(
        settings, paused.pause_receipt.run_id, decision="approve"
    )

    assert isinstance(terminal, TerminalRun)
    assert terminal.receipt.continued_from_run_id == paused.pause_receipt.run_id
    assert terminal.receipt.conversation_id == "conv-gw-3"
    assert terminal.receipt.composition.composition_id == (
        paused.pause_receipt.composition.composition_id
    )
    assert terminal.receipt.composition.plugins[0].config == {"ace_root": "/v1"}


def test_deny_resume_delivers_tool_denied(tmp_path: Path, monkeypatch):
    _write_profile(tmp_path, "writing")

    def fn(messages, info):
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

    _use_model(monkeypatch, fn)
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        "zuaef_agent.gateway.bridge.build_profile_agent",
        lambda settings, run_id=None, profile=None, **kw: _build_with_discover(
            settings, run_id=run_id, profile=profile, **kw
        ),
    )
    paused = start_profile_run(
        settings=settings,
        profile="writing",
        prompt="go",
        conversation_id="c4",
        config_root=_config_root(tmp_path),
    )
    monkeypatch.setattr(
        "zuaef_agent.continuation.build_profile_agent",
        lambda settings, run_id=None, profile=None, snapshot=None, **kw: _build_with_discover(
            settings, run_id=run_id, profile=profile, snapshot=snapshot, **kw
        ),
    )

    terminal = resume_for_surface(
        settings,
        paused.pause_receipt.run_id,
        decision="deny",
        reason="operator refused",
    )

    assert isinstance(terminal, TerminalRun)
    assert not [
        e
        for e in terminal.receipt.tool_effect_facts
        if e.tool_name == "publish_article" and e.status == "completed"
    ]


def test_project_prompt_with_and_without_attachments():
    envelope = InboundEnvelope(
        surface="telegram", user_id="42", channel_id="42", message_id="m1", text="  帮我分析这个预算  "
    )
    assert project_prompt(envelope) == "帮我分析这个预算"

    envelope = envelope.model_copy(
        update={
            "attachments": [
                AttachmentRef(kind="document", local_path="inbox/telegram/a1-budget.csv")
            ]
        }
    )
    projected = project_prompt(envelope)
    assert projected.startswith("帮我分析这个预算")
    assert "Attached files available in the workspace:" in projected
    assert "- inbox/telegram/a1-budget.csv" in projected


def test_validate_profile_accepts_and_rejects(tmp_path: Path):
    _write_profile(tmp_path, "writing")
    settings = _settings(tmp_path)

    validate_profile(
        "writing",
        settings,
        config_root=_config_root(tmp_path),
        discover=lambda: DISCOVER,
        version_for=_vf,
    )

    with pytest.raises(CompositionError):
        validate_profile("missing-profile", settings)
    with pytest.raises(CompositionError):
        validate_profile(
            "writing",
            settings,
            config_root=_config_root(tmp_path),
            discover=dict,
            version_for=_vf,
        )
