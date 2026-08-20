"""Runtime contract tests through the shared execute_run seam.

FunctionModel drives deterministic branches (per the Gate: TestModel/FunctionModel
may only cover deterministic branches — the real-model slice is the Gate's job).
Receipt assertions use v2 operational facts (artifact_facts / tool_effect_facts /
execution_state) — never semantic verification fields.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RunUsage
from pydantic_ai_harness.step_persistence import FileStepStore, StepEvent

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.integrity import sha256_file
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import (
    PausedRun,
    TerminalRun,
    _usage_payload,
    decide,
    execute_run,
    finalize_terminal,
)

models.ALLOW_MODEL_REQUESTS = False


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


def _business_toolset(marker_root: Path):
    from pydantic_ai import FunctionToolset

    ts: FunctionToolset[CoreDeps] = FunctionToolset()

    @ts.tool
    def write_report(ctx, content: str) -> str:
        target = ctx.deps.workspace_root / "artifacts" / "report.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {target.name}"

    @ts.tool(requires_approval=True)
    def record_external_effect(ctx, effect_id: str) -> str:
        marker_root.mkdir(parents=True, exist_ok=True)
        conversation = getattr(ctx, "conversation_id", None) or ctx.deps.run_id
        marker = marker_root / f"external-effect-{conversation}.marker"
        marker.write_text(effect_id, encoding="utf-8")
        return f"recorded {marker.name}"

    return ts


def _compose(settings: AgentSettings, marker_root: Path, run_id: str):
    agent = build_agent(settings, run_id=run_id, extra_toolsets=[_business_toolset(marker_root)])
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    return agent, deps


def _final(text: str = "done") -> ModelResponse:
    """Natural terminal: plain text is the whole presentation (P3B-2 INV-1)."""
    return ModelResponse(parts=[TextPart(content=text)])


def _has_tool_return(messages) -> bool:
    return any(
        getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
        for message in messages
        for part in getattr(message, "parts", [])
    )


def test_seam_tool_run_records_completed_with_artifact_fact(tmp_path: Path):
    settings = _settings(tmp_path)
    marker_root = tmp_path / ".state-proof"
    run_id = uuid4().hex
    agent, deps = _compose(settings, marker_root, run_id)

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(parts=[ToolCallPart("write_report", {"content": "# Report\n\nFindings."})])
        return _final("Report written.")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="write the report", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "completed"
    assert outcome.presentation == "Report written."
    report = settings.workspace_root / "artifacts" / "report.md"
    assert report.is_file()
    assert outcome.receipt.artifact_facts[0].path == "artifacts/report.md"
    assert outcome.receipt.artifact_facts[0].sha256 == sha256_file(report)
    assert outcome.receipt.artifact_facts[0].change == "created"
    assert not outcome.receipt.unresolved_effects


def test_natural_terminal_settles_completed_with_zero_artifacts(tmp_path: Path):
    """A plain answer with no artifact claim is a full completion — the
    settlement never requires model-crafted artifact/evidence refs."""
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        return _final("这是改写后的正文。")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="改写这篇文章", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "completed"
    assert outcome.receipt.artifact_facts == []
    assert outcome.presentation == "这是改写后的正文。"


def test_usage_payload_accepts_run_usage_tracker_directly():
    payload = _usage_payload(RunUsage(requests=1, input_tokens=2, output_tokens=1))

    assert payload["requests"] == 1
    assert payload["input_tokens"] == 2


def test_unchanged_preexisting_artifact_not_owned_by_run(tmp_path: Path):
    settings = _settings(tmp_path)
    artifacts = settings.workspace_root / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "report.md").write_text("old content", encoding="utf-8")
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        return _final("claims nothing; the file predates the run")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="claim it", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "completed"
    assert outcome.receipt.artifact_facts == []


def _approval_fn(messages, info):
    if not _has_tool_return(messages):
        return ModelResponse(parts=[ToolCallPart("record_external_effect", {"effect_id": "e1"})])
    return _final("side effect handled")


def test_pause_then_deny_leaves_no_side_effect(tmp_path: Path):
    settings = _settings(tmp_path)
    marker_root = tmp_path / ".state-proof"
    run_id = uuid4().hex
    agent, deps = _compose(settings, marker_root, run_id)

    with agent.override(model=FunctionModel(_approval_fn)):
        outcome = execute_run(agent, deps, prompt="record the effect", settings=settings, run_id=run_id)

    assert isinstance(outcome, PausedRun)
    assert outcome.pause_receipt.state == "paused"
    assert outcome.pause_receipt.pending_approvals[0]["tool_name"] == "record_external_effect"
    assert outcome.message_history
    assert outcome.conversation_id
    assert not list(marker_root.glob("*.marker"))

    run_id2 = uuid4().hex
    agent2, deps2 = _compose(settings, marker_root, run_id2)
    with agent2.override(model=FunctionModel(_approval_fn)):
        outcome2 = execute_run(
            agent2,
            deps2,
            settings=settings,
            run_id=run_id2,
            conversation_id=outcome.conversation_id,
            message_history=outcome.message_history,
            deferred_tool_results=decide(outcome, approve=False),
            prior_pause_receipt=outcome.pause_receipt,
        )

    assert isinstance(outcome2, TerminalRun)
    assert outcome2.receipt.run_id != outcome.pause_receipt.run_id
    assert outcome2.receipt.conversation_id == outcome.pause_receipt.conversation_id
    assert not list(marker_root.glob("*.marker")), "denied side effect must not exist"


def test_pause_then_approve_executes_and_settles_effect(tmp_path: Path):
    settings = _settings(tmp_path)
    marker_root = tmp_path / ".state-proof"
    run_id = uuid4().hex
    agent, deps = _compose(settings, marker_root, run_id)

    with agent.override(model=FunctionModel(_approval_fn)):
        outcome = execute_run(agent, deps, prompt="record the effect", settings=settings, run_id=run_id)

    assert isinstance(outcome, PausedRun)
    assert not list(marker_root.glob("*.marker")), "tool must not run before approval"

    run_id2 = uuid4().hex
    agent2, deps2 = _compose(settings, marker_root, run_id2)
    with agent2.override(model=FunctionModel(_approval_fn)):
        outcome2 = execute_run(
            agent2,
            deps2,
            settings=settings,
            run_id=run_id2,
            conversation_id=outcome.conversation_id,
            message_history=outcome.message_history,
            deferred_tool_results=decide(outcome, approve=True),
            prior_pause_receipt=outcome.pause_receipt,
        )

    assert isinstance(outcome2, TerminalRun)
    markers = list(marker_root.glob("*.marker"))
    assert len(markers) == 1, "approved side effect executed exactly once"
    settled = [e for e in outcome2.receipt.tool_effect_facts if e.tool_name == "record_external_effect"]
    assert settled and settled[0].status == "completed"
    assert not outcome2.receipt.unresolved_effects


def test_pause_settles_and_resume_inherits_artifact_facts(tmp_path: Path):
    settings = _settings(tmp_path)
    marker_root = tmp_path / ".state-proof"
    run_id = uuid4().hex
    agent, deps = _compose(settings, marker_root, run_id)

    def fn(messages, info):
        called = [
            part.tool_name
            for message in messages
            for part in getattr(message, "parts", [])
            if getattr(part, "part_kind", None) == "tool-call"
        ]
        if "write_report" not in called:
            return ModelResponse(parts=[ToolCallPart("write_report", {"content": "# Pause proof"})])
        if "record_external_effect" not in called:
            return ModelResponse(parts=[ToolCallPart("record_external_effect", {"effect_id": "pause-proof"})])
        return _final("pause proof completed")

    with agent.override(model=FunctionModel(fn)):
        paused = execute_run(agent, deps, prompt="prove pause inheritance", settings=settings, run_id=run_id)

    assert isinstance(paused, PausedRun)
    assert [item.path for item in paused.pause_receipt.artifact_facts] == ["artifacts/report.md"]

    run_id2 = uuid4().hex
    agent2, deps2 = _compose(settings, marker_root, run_id2)
    with agent2.override(model=FunctionModel(fn)):
        terminal = execute_run(
            agent2,
            deps2,
            settings=settings,
            run_id=run_id2,
            conversation_id=paused.conversation_id,
            message_history=paused.message_history,
            deferred_tool_results=decide(paused, approve=True),
            prior_pause_receipt=paused.pause_receipt,
        )

    assert isinstance(terminal, TerminalRun)
    assert terminal.receipt.execution_state == "completed"
    assert terminal.receipt.continued_from_run_id == run_id
    assert [item.path for item in terminal.receipt.artifact_facts] == ["artifacts/report.md"]


def test_unresolved_started_effect_is_failed_execution(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    store = FileStepStore(settings.step_store_dir)
    asyncio.run(
        store.append_event(
            StepEvent(
                run_id=run_id,
                kind="tool_call_started",
                step_index=0,
                tool_call_id="call_x",
                tool_name="record_external_effect",
            )
        )
    )

    outcome = finalize_terminal(
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
        execution_state="completed",
        outcome="claims success",
    )

    assert outcome.receipt.execution_state == "failed"
    assert outcome.receipt.unresolved_effects[0].tool_call_id == "call_x"


def test_foreign_run_effects_are_not_recorded(tmp_path: Path):
    """A completed effect owned by a different run is not in this run's ledger:
    the public StepStore keeps per-run ledgers, so a foreign event never enters
    this run's facts."""
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    store = FileStepStore(settings.step_store_dir)
    asyncio.run(
        store.append_event(
            StepEvent(
                run_id=run_id,
                kind="tool_call_completed",
                step_index=0,
                tool_call_id="call_own",
                tool_name="record_external_effect",
            )
        )
    )
    asyncio.run(
        store.append_event(
            StepEvent(
                run_id="another-run",
                kind="tool_call_completed",
                step_index=0,
                tool_call_id="call_foreign",
                tool_name="record_external_effect",
            )
        )
    )

    outcome = finalize_terminal(
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
        execution_state="completed",
        outcome="claims success",
    )

    own_ids = {e.tool_call_id for e in outcome.receipt.tool_effect_facts}
    assert "call_own" in own_ids
    assert "call_foreign" not in own_ids
    assert outcome.receipt.execution_state == "completed"


def test_unsourced_knowledge_write_is_still_a_provenance_fact(tmp_path: Path):
    """v1.2: a knowledge doc written by the run is recorded as a provenance
    fact even without semantic source validation — the kernel never claims a
    source field proves support."""
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    target = settings.workspace_root / "knowledge" / "concepts" / "note.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        f"---\ntype: project-note\ntitle: Note\ngenerated:\n  run_id: {run_id}\n---\nbody\n",
        encoding="utf-8",
    )

    outcome = finalize_terminal(
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
        execution_state="completed",
        outcome="claims success",
    )

    assert outcome.receipt.knowledge_updates == ["knowledge/concepts/note.md"]
    assert outcome.receipt.execution_state == "completed"


def test_execute_run_rejects_identity_mismatch(tmp_path: Path):
    settings = _settings(tmp_path)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id="deps-run")

    with pytest.raises(ValueError, match="deps.run_id"):
        execute_run(object(), deps, prompt="x", settings=settings, run_id="other-run")


def test_provider_failure_leaves_failed_receipt(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        raise UnexpectedModelBehavior("provider exploded")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="go", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "failed"
    assert "provider exploded" in (outcome.receipt.error or "")
    assert outcome.receipt.usage_complete is False
    assert outcome.receipt.run_id == run_id
    assert outcome.receipt.conversation_id


def test_knowledge_written_via_capability_is_a_provenance_fact(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write_knowledge",
                        {
                            "knowledge_id": "concepts/shared-seam",
                            "title": "Shared Seam",
                            "body": "One runtime, many compositions. Source: https://ai.pydantic.dev/capabilities",
                            "tags": [],
                        },
                    )
                ]
            )
        return _final("knowledge captured")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="capture knowledge", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "completed"
    assert outcome.receipt.knowledge_updates == ["knowledge/concepts/shared-seam.md"]
    # No evidence refs are synthesized from the write — the doc records
    # provenance, not proof.
    assert not hasattr(outcome.receipt, "verified_knowledge")
