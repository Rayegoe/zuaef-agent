"""Runtime contract tests through the shared execute_run seam.

FunctionModel drives deterministic branches (per the Gate: TestModel/FunctionModel
may only cover deterministic branches — the real-model slice is the Gate's job).
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RunUsage

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps, RunSummary
from zuaef_agent.runtime import (
    PausedRun,
    TerminalRun,
    _usage_payload,
    decide,
    execute_run,
    finalize_terminal,
)
from zuaef_agent.verification import sha256_file

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


def _final(summary: dict) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("final_result", summary)])


def _has_tool_return(messages) -> bool:
    return any(
        getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
        for message in messages
        for part in getattr(message, "parts", [])
    )


def test_seam_tool_run_verified_completed(tmp_path: Path):
    settings = _settings(tmp_path)
    marker_root = tmp_path / ".state-proof"
    run_id = uuid4().hex
    agent, deps = _compose(settings, marker_root, run_id)

    def fn(messages, info):
        if not _has_tool_return(messages):
            return ModelResponse(parts=[ToolCallPart("write_report", {"content": "# Report\n\nFindings."})])
        return _final(
            {
                "status": "completed",
                "outcome": "report written",
                "artifacts": ["artifacts/report.md"],
                "evidence": ["artifact:artifacts/report.md"],
            }
        )

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="write the report", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.summary.status == "completed"
    report = settings.workspace_root / "artifacts" / "report.md"
    assert report.is_file()
    assert outcome.receipt.verified_artifacts[0].path == "artifacts/report.md"
    assert outcome.receipt.verified_artifacts[0].sha256 == sha256_file(report)
    assert outcome.summary.artifacts == ["artifacts/report.md"]
    assert Path(outcome.receipt.summary.receipt).is_file()


def test_fake_artifact_claim_degrades_completed_to_partial(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        return _final(
            {
                "status": "completed",
                "outcome": "ghost report",
                "artifacts": ["artifacts/ghost.md"],
                "evidence": ["artifact:artifacts/ghost.md"],
            }
        )

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="fake it", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.summary.status == "partial"
    assert outcome.summary.artifacts == []
    assert outcome.receipt.degraded
    assert "ghost.md" in outcome.receipt.degraded[0]


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
        return _final(
            {
                "status": "completed",
                "outcome": "claims the old file",
                "artifacts": ["artifacts/report.md"],
                "evidence": ["artifact:artifacts/report.md"],
            }
        )

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="claim it", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.summary.status == "partial"
    assert outcome.receipt.verified_artifacts == []
    assert any("unchanged" in note for note in outcome.receipt.degraded)


def _approval_fn(messages, info):
    if not _has_tool_return(messages):
        return ModelResponse(parts=[ToolCallPart("record_external_effect", {"effect_id": "e1"})])
    return _final(
        {
            "status": "completed",
            "outcome": "side effect handled",
            "artifacts": [],
            "evidence": [],
        }
    )


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
    settled = [e for e in outcome2.receipt.verified_tool_effects if e.tool_name == "record_external_effect"]
    assert settled and settled[0].status == "completed"
    assert not outcome2.receipt.unresolved_effects


def test_pause_settles_and_resume_inherits_artifact_and_knowledge(tmp_path: Path):
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
        if "write_knowledge" not in called:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "write_knowledge",
                        {
                            "knowledge_id": "concepts/pause-proof",
                            "doc_type": "concept",
                            "title": "Pause Proof",
                            "body": "Evidence survives a native approval pause.",
                            "tags": [],
                            "sources": [
                                {
                                    "id": "guide",
                                    "resource": "file:///guide.md",
                                    "title": "Guide",
                                    "evidence": "section 1",
                                }
                            ],
                        },
                    )
                ]
            )
        if "write_report" not in called:
            return ModelResponse(parts=[ToolCallPart("write_report", {"content": "# Pause proof"})])
        if "record_external_effect" not in called:
            return ModelResponse(parts=[ToolCallPart("record_external_effect", {"effect_id": "pause-proof"})])
        return _final(
            {
                "status": "completed",
                "outcome": "pause proof completed",
                "artifacts": ["artifacts/report.md"],
                "evidence": [
                    "artifact:artifacts/report.md",
                    "knowledge:concepts/pause-proof",
                ],
            }
        )

    with agent.override(model=FunctionModel(fn)):
        paused = execute_run(agent, deps, prompt="prove pause inheritance", settings=settings, run_id=run_id)

    assert isinstance(paused, PausedRun)
    assert [item.path for item in paused.pause_receipt.verified_artifacts] == ["artifacts/report.md"]
    assert paused.pause_receipt.verified_knowledge == ["concepts/pause-proof"]

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
    assert terminal.summary.status == "completed", terminal.receipt.degraded
    assert terminal.receipt.continued_from_run_id == run_id
    assert [item.path for item in terminal.receipt.verified_artifacts] == ["artifacts/report.md"]
    assert terminal.receipt.verified_knowledge == ["concepts/pause-proof"]


def test_unresolved_started_effect_blocks_run(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    ledger_dir = settings.step_store_dir / run_id
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "tool_effects.jsonl").write_text(
        json.dumps(
            {
                "tool_call_id": "call_x",
                "tool_name": "record_external_effect",
                "run_id": run_id,
                "status": "started",
                "started_at": "2026-08-14T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    outcome = finalize_terminal(
        RunSummary(status="completed", outcome="claims success", artifacts=[], evidence=[]),
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
    )

    assert outcome.receipt.status == "blocked"
    assert outcome.receipt.unresolved_effects[0].tool_call_id == "call_x"
    assert outcome.summary.status == "blocked"


def test_foreign_completed_effect_is_not_verified(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    ledger_dir = settings.step_store_dir / run_id
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "tool_effects.jsonl").write_text(
        json.dumps(
            {
                "tool_call_id": "call_foreign",
                "tool_name": "record_external_effect",
                "run_id": "another-run",
                "status": "completed",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    outcome = finalize_terminal(
        RunSummary(status="completed", outcome="claims success"),
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
    )

    assert outcome.receipt.verified_tool_effects == []
    assert any("not owned" in note for note in outcome.receipt.degraded)


def test_host_discovered_invalid_knowledge_is_not_verified(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    target = settings.workspace_root / "knowledge" / "concepts" / "invalid.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        f"---\ntype: concept\ntitle: Invalid\nsources: []\ngenerated:\n  run_id: {run_id}\n---\nbody\n",
        encoding="utf-8",
    )

    outcome = finalize_terminal(
        RunSummary(status="completed", outcome="claims success"),
        settings=settings,
        run_id=run_id,
        conversation_id="conv-x",
        model_label="test",
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        usage={},
        snapshot={},
    )

    assert outcome.receipt.verified_knowledge == []
    assert any("sources" in note for note in outcome.receipt.degraded)


def test_execute_run_rejects_identity_mismatch(tmp_path: Path):
    settings = _settings(tmp_path)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id="deps-run")

    with pytest.raises(ValueError, match="deps.run_id"):
        execute_run(object(), deps, prompt="x", settings=settings, run_id="other-run")


def test_provider_failure_leaves_blocked_receipt(tmp_path: Path):
    settings = _settings(tmp_path)
    run_id = uuid4().hex
    agent, deps = _compose(settings, tmp_path / ".state-proof", run_id)

    def fn(messages, info):
        raise UnexpectedModelBehavior("provider exploded")

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="go", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.summary.status == "blocked"
    assert "provider exploded" in (outcome.receipt.error or "")
    assert outcome.receipt.usage_complete is False
    assert outcome.receipt.run_id == run_id
    assert outcome.receipt.conversation_id
    assert Path(outcome.summary.receipt).is_file(), "failure must not exit without a receipt"


def test_knowledge_written_via_capability_is_verified(tmp_path: Path):
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
                            "doc_type": "concept",
                            "title": "Shared Seam",
                            "body": "One runtime, many compositions.",
                            "tags": [],
                            "sources": [
                                {"id": "src-1", "resource": "file:///guide.md", "title": None, "evidence": None}
                            ],
                        },
                    )
                ]
            )
        return _final(
            {
                "status": "completed",
                "outcome": "knowledge captured",
                "artifacts": [],
                "evidence": ["knowledge:concepts/shared-seam"],
            }
        )

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(agent, deps, prompt="capture knowledge", settings=settings, run_id=run_id)

    assert isinstance(outcome, TerminalRun)
    assert outcome.summary.status == "completed", outcome.receipt.degraded
    assert "concepts/shared-seam" in outcome.receipt.verified_knowledge
    assert outcome.receipt.knowledge_updates == ["knowledge/concepts/shared-seam.md"]
    assert "knowledge:concepts/shared-seam" in outcome.summary.evidence
