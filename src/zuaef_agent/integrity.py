"""Integrity-only host facts (v1.2 SPEC §6).

This module owns byte/integrity and ledger facts ONLY:

- ``sha256_file`` — byte identity;
- ``snapshot_artifacts`` — bounded pre-run artifact byte snapshot;
- ``normalize_artifact_path`` / ``verify_artifact`` — containment + changed-byte
  facts (a changed hash proves change, never correctness);
- ``read_tool_effects`` / ``latest_tool_effects`` — StepStore tool-call ledger
  projection (execution facts).

It does NOT parse model-claimed evidence references, validate knowledge
semantics, or downgrade a run because a source field is absent.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic_ai_harness.step_persistence import FileStepStore

from .models import ArtifactFact

ARTIFACT_DIR = "artifacts"

# The harness persistent StepEvent ledger kinds that describe a tool call's
# lifecycle; the runtime reads them through the public StepStore API.
_TOOL_EVENT_KINDS = frozenset(
    {"tool_call_started", "tool_call_completed", "tool_call_failed"}
)

_STATUS_BY_KIND = {
    "tool_call_started": "started",
    "tool_call_completed": "completed",
    "tool_call_failed": "failed",
}


class IntegrityError(Exception):
    """Why a byte/integrity or ledger fact could not be established."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_artifacts(workspace_root: Path) -> dict[str, str]:
    """Bounded pre-run snapshot: relpath -> SHA-256 for existing artifacts."""
    artifacts_dir = workspace_root / ARTIFACT_DIR
    if not artifacts_dir.is_dir():
        return {}
    root = workspace_root.resolve()
    snapshot: dict[str, str] = {}
    for path in sorted(artifacts_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            continue
        snapshot[path.relative_to(root).as_posix()] = sha256_file(resolved)
    return snapshot


def normalize_artifact_path(path_str: str, *, workspace_root: Path) -> Path:
    """Validate a claimed artifact path and return its resolved target."""
    rel = PurePosixPath(path_str.strip())
    if rel.is_absolute() or ".." in rel.parts:
        raise IntegrityError(f"artifact path not workspace-relative: {path_str!r}")
    if not rel.parts or rel.parts[0] != ARTIFACT_DIR:
        raise IntegrityError(f"artifact must live under {ARTIFACT_DIR}/: {path_str!r}")
    target = (workspace_root / Path(*rel.parts)).resolve()
    if not target.is_relative_to(workspace_root.resolve()):
        raise IntegrityError(f"artifact path escapes workspace: {path_str!r}")
    return target


def verify_artifact(
    path_str: str,
    *,
    workspace_root: Path,
    snapshot: dict[str, str],
) -> ArtifactFact:
    """Produce a byte fact: containment, existence, regular file, size, SHA-256."""
    rel = PurePosixPath(path_str.strip())
    target = normalize_artifact_path(path_str, workspace_root=workspace_root)
    if not target.exists():
        raise IntegrityError(f"artifact does not exist: {path_str!r}")
    if target.is_symlink() or not target.is_file():
        raise IntegrityError(f"artifact is not a regular file: {path_str!r}")
    digest = sha256_file(target)
    rel_key = rel.as_posix()
    pre = snapshot.get(rel_key)
    if pre is not None and pre == digest:
        raise IntegrityError(f"artifact unchanged by this run: {path_str!r}")
    change = "modified" if pre is not None else "created"
    return ArtifactFact(
        path=rel_key, size=target.stat().st_size, sha256=digest, change=change
    )


def _records_from_events(events: Sequence[Any]) -> list[dict[str, Any]]:
    """Project a StepEvent stream onto the ``{tool_call_id, tool_name, run_id,
    status}`` record shape. Non-tool boundary events are skipped; a missing
    tool_call_id is not a ledger row."""
    records: list[dict[str, Any]] = []
    for event in events:
        status = _STATUS_BY_KIND.get(event.kind)
        if status is None or not event.tool_call_id:
            continue
        records.append(
            {
                "tool_call_id": event.tool_call_id,
                "tool_name": event.tool_name,
                "run_id": event.run_id,
                "status": status,
            }
        )
    return records


def read_tool_effects(step_store_dir: Path, run_id: str) -> list[dict[str, Any]]:
    r"""Return the latest tool-effect record per ``tool_call_id`` for a run.

    Built on the public Harness StepStore API (``FileStepStore.list_events``)
    — ZUAEF never parses the private ``tool_effects.jsonl`` layout, which is
    not a stable contract (UPSTREAM_BASELINE.md §9 / SPEC §14).
    """
    store = FileStepStore(step_store_dir)
    events = asyncio.run(store.list_events(run_id=run_id))
    return latest_tool_effects(_records_from_events(events))


def latest_tool_effects(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse an append-only ledger to the latest record per tool_call_id."""
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        tool_call_id = record.get("tool_call_id")
        if tool_call_id is not None:
            latest[tool_call_id] = record
    return list(latest.values())
