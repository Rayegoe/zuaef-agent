"""Integrity-only facts (v1.2 SPEC §6): byte identity, containment, ledger facts.

No semantic evidence parsing, no knowledge truth validation — a hash proves
byte change, never content correctness.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic_ai_harness.step_persistence import FileStepStore, StepEvent

from zuaef_agent.integrity import (
    IntegrityError,
    latest_tool_effects,
    read_tool_effects,
    run_timings_from_events,
    sha256_file,
    snapshot_artifacts,
    verify_artifact,
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
    with pytest.raises(IntegrityError, match="unchanged"):
        verify_artifact("artifacts/old.md", workspace_root=workspace, snapshot=snapshot)

    # changed -> owned with "modified"
    keep.write_text("new content", encoding="utf-8")
    verified = verify_artifact("artifacts/old.md", workspace_root=workspace, snapshot=snapshot)
    assert verified.sha256 == sha256_file(keep)
    assert verified.size == len(b"new content")
    assert verified.change == "modified"

    # new -> owned with "created"
    fresh = workspace / "artifacts" / "new.md"
    fresh.write_text("fresh", encoding="utf-8")
    verified = verify_artifact("artifacts/new.md", workspace_root=workspace, snapshot=snapshot)
    assert verified.path == "artifacts/new.md"
    assert verified.change == "created"


def test_artifact_containment_and_existence(tmp_path: Path):
    workspace = _workspace(tmp_path)
    snapshot = {}

    with pytest.raises(IntegrityError, match="workspace-relative"):
        verify_artifact("/etc/passwd", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(IntegrityError, match="workspace-relative"):
        verify_artifact("../x.md", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(IntegrityError, match="artifacts/"):
        verify_artifact("knowledge/x.md", workspace_root=workspace, snapshot=snapshot)
    with pytest.raises(IntegrityError, match="does not exist"):
        verify_artifact("artifacts/missing.md", workspace_root=workspace, snapshot=snapshot)

    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = workspace / "artifacts" / "link.md"
    link.symlink_to(outside)
    with pytest.raises(IntegrityError):
        verify_artifact("artifacts/link.md", workspace_root=workspace, snapshot=snapshot)


def test_tool_effect_facts_via_public_stepstore(tmp_path: Path):
    """Ledger facts read the public StepStore event ledger, never the private
    ``tool_effects.jsonl`` backend."""
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

    latest = latest_tool_effects(records)
    by_id = {r["tool_call_id"]: r["status"] for r in latest}
    assert by_id == {"c1": "completed", "c2": "started"}

    # An empty run has no ledger entries at all.
    assert read_tool_effects(step_dir, "run-ghost") == []


def test_run_timings_pair_existing_harness_event_timestamps():
    start = datetime(2026, 8, 21, tzinfo=UTC)
    events = [
        StepEvent(run_id="run-a", kind="run_started", step_index=0, timestamp=start),
        StepEvent(
            run_id="run-a",
            kind="model_request_started",
            step_index=1,
            timestamp=start + timedelta(milliseconds=1),
        ),
        StepEvent(
            run_id="run-a",
            kind="model_request_completed",
            step_index=1,
            timestamp=start + timedelta(milliseconds=11),
        ),
        StepEvent(
            run_id="run-a",
            kind="tool_call_started",
            step_index=2,
            timestamp=start + timedelta(milliseconds=12),
            tool_call_id="call-1",
            tool_name="read_material",
        ),
        StepEvent(
            run_id="run-a",
            kind="tool_call_completed",
            step_index=2,
            timestamp=start + timedelta(milliseconds=17),
            tool_call_id="call-1",
            tool_name="read_material",
        ),
        StepEvent(
            run_id="run-a",
            kind="tool_call_started",
            step_index=3,
            timestamp=start + timedelta(milliseconds=18),
            tool_call_id="call-2",
            tool_name="write_article",
        ),
    ]

    assert run_timings_from_events(events) == {
        "request_latencies_ms": [10.0],
        "tool_latencies_ms": {
            "read_material": [5.0],
            "write_article": [None],
        },
    }
