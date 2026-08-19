from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic_ai_harness.step_persistence import FileStepStore, StepEvent

from zuaef_agent.knowledge_store import KnowledgeStore
from zuaef_agent.models import SourceRef
from zuaef_agent.verification import (
    VerificationError,
    parse_evidence_ref,
    read_tool_effects,
    sha256_file,
    snapshot_artifacts,
    verify_artifact,
    verify_knowledge,
    verify_tool_effect,
)


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    artifacts = workspace / "artifacts"
    artifacts.mkdir(parents=True)
    return workspace


def test_snapshot_and_ownership_new_changed_unchanged(tmp_path: Path):
    workspace = _workspace(tmp_path)
    keep = workspace / "artifacts" / "old.md"
    keep.write_text("old", encoding="utf-8")

    snapshot = snapshot_artifacts(workspace)
    assert set(snapshot) == {"artifacts/old.md"}

    # unchanged -> rejected
    with pytest.raises(VerificationError, match="unchanged"):
        verify_artifact("artifacts/old.md", workspace_root=workspace, snapshot=snapshot)

    # changed -> owned
    keep.write_text("new content", encoding="utf-8")
    verified = verify_artifact("artifacts/old.md", workspace_root=workspace, snapshot=snapshot)
    assert verified.sha256 == sha256_file(keep)
    assert verified.size == len(b"new content")

    # new -> owned
    fresh = workspace / "artifacts" / "new.md"
    fresh.write_text("fresh", encoding="utf-8")
    verified = verify_artifact("artifacts/new.md", workspace_root=workspace, snapshot=snapshot)
    assert verified.path == "artifacts/new.md"


def test_artifact_containment_and_existence(tmp_path: Path):
    workspace = _workspace(tmp_path)
    snapshot = {}

    with pytest.raises(VerificationError, match="workspace-relative"):
        verify_artifact("/etc/passwd", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(VerificationError, match="workspace-relative"):
        verify_artifact("../x.md", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(VerificationError, match="artifacts/"):
        verify_artifact("knowledge/x.md", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(VerificationError, match="does not exist"):
        verify_artifact("artifacts/missing.md", workspace_root=workspace, snapshot=snapshot)

    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = workspace / "artifacts" / "link.md"
    link.symlink_to(outside)
    with pytest.raises(VerificationError):
        verify_artifact("artifacts/link.md", workspace_root=workspace, snapshot=snapshot)


def test_evidence_ref_parsing():
    assert parse_evidence_ref("artifact:artifacts/a.md") == ("artifact", "artifacts/a.md")
    assert parse_evidence_ref("knowledge:concepts/x") == ("knowledge", "concepts/x")
    assert parse_evidence_ref("tool-effect:call_1") == ("tool-effect", "call_1")
    for bad in ("I checked the file", "artifact:", ":x", "bogus:x"):
        with pytest.raises(VerificationError):
            parse_evidence_ref(bad)


def test_knowledge_verification_ownership_and_sources(tmp_path: Path):
    workspace = _workspace(tmp_path)
    store = KnowledgeStore(workspace)
    store.write_doc(
        knowledge_id="concepts/owned",
        doc_type="concept",
        title="Owned",
        body="body",
        sources=[SourceRef(id="s1", resource="file:///x.md")],
        run_id="run-a",
    )

    assert verify_knowledge("concepts/owned", store=store, run_id="run-a") == "knowledge/concepts/owned.md"
    with pytest.raises(VerificationError, match="not owned by run"):
        verify_knowledge("concepts/owned", store=store, run_id="run-b")
    with pytest.raises(VerificationError, match="does not exist"):
        verify_knowledge("concepts/missing", store=store, run_id="run-a")


def test_tool_effect_verification_via_public_stepstore(tmp_path: Path):
    """Tool-effect verification reads the public StepStore event ledger, never
    the private ``tool_effects.jsonl`` backend (T004)."""
    step_dir = tmp_path / "steps"
    store = FileStepStore(step_dir)
    asyncio.run(
        store.append_event(
            StepEvent(
                run_id="run-a", kind="tool_call_started", step_index=0, tool_call_id="c2", tool_name="boom"
            )
        )
    )
    asyncio.run(
        store.append_event(
            StepEvent(
                run_id="run-a", kind="tool_call_completed", step_index=1, tool_call_id="c1", tool_name="write_report"
            )
        )
    )

    # The public read collapses the event stream to latest-per-call.
    records = read_tool_effects(step_dir, "run-a")
    assert {r["tool_call_id"] for r in records} == {"c1", "c2"}

    verified = verify_tool_effect("c1", step_store_dir=step_dir, run_id="run-a")
    assert verified["status"] == "completed"

    with pytest.raises(VerificationError, match="started but never settled"):
        verify_tool_effect("c2", step_store_dir=step_dir, run_id="run-a")
    with pytest.raises(VerificationError, match="not in ledger"):
        verify_tool_effect("c4", step_store_dir=step_dir, run_id="run-a")

    # An empty run has no ledger entries at all.
    assert read_tool_effects(step_dir, "run-ghost") == []


def test_tool_effect_ownership_check_on_raw_records(tmp_path: Path):
    """The defensive ownership check still rejects a record owned by another
    run when injected as raw records (unit-level; the public store cannot
    produce a foreign row inside a run's own ledger)."""
    step_dir = tmp_path / "steps"
    records = [
        {"tool_call_id": "c3", "tool_name": "other", "run_id": "run-z", "status": "completed"},
    ]
    with pytest.raises(VerificationError, match="not owned"):
        verify_tool_effect("c3", step_store_dir=step_dir, run_id="run-a", records=records)
