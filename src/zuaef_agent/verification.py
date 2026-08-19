"""Host-side verification of model-claimed results.

The model proposes artifact paths, knowledge ids and tool-effect refs; these
functions turn proposals into verified facts or explicit rejection reasons.
Ownership of an artifact never relies on mtime: the runtime snapshots
``workspace/artifacts/**`` before execution and a claimed artifact must be new
or have a changed SHA-256 afterwards.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from pydantic_ai_harness.step_persistence import FileStepStore

from .knowledge_store import REQUIRED_SOURCE_TYPES, KnowledgeStore
from .models import ArtifactVerification

ARTIFACT_DIR = "artifacts"

_EVIDENCE_RE = re.compile(r"^(artifact|knowledge|tool-effect):(.+)$")

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


class VerificationError(Exception):
    """Why a model-claimed reference could not be verified."""


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
        raise VerificationError(f"artifact path not workspace-relative: {path_str!r}")
    if not rel.parts or rel.parts[0] != ARTIFACT_DIR:
        raise VerificationError(f"artifact must live under {ARTIFACT_DIR}/: {path_str!r}")
    target = (workspace_root / Path(*rel.parts)).resolve()
    if not target.is_relative_to(workspace_root.resolve()):
        raise VerificationError(f"artifact path escapes workspace: {path_str!r}")
    return target


def verify_artifact(
    path_str: str,
    *,
    workspace_root: Path,
    snapshot: dict[str, str],
) -> ArtifactVerification:
    """Verify containment, existence, regular file, run ownership, size, SHA-256."""
    rel = PurePosixPath(path_str.strip())
    target = normalize_artifact_path(path_str, workspace_root=workspace_root)
    if not target.exists():
        raise VerificationError(f"artifact does not exist: {path_str!r}")
    if target.is_symlink() or not target.is_file():
        raise VerificationError(f"artifact is not a regular file: {path_str!r}")
    digest = sha256_file(target)
    rel_key = rel.as_posix()
    pre = snapshot.get(rel_key)
    if pre is not None and pre == digest:
        raise VerificationError(f"artifact unchanged by this run: {path_str!r}")
    return ArtifactVerification(path=rel_key, size=target.stat().st_size, sha256=digest)


def verify_knowledge(knowledge_id: str, *, store: KnowledgeStore, run_id: str) -> str:
    """Verify id, file existence, frontmatter run ownership and source rules."""
    target = store.path_for(knowledge_id)  # validates id, reserved ids, containment
    if not target.is_file():
        raise VerificationError(f"knowledge node does not exist: {knowledge_id!r}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        raise VerificationError(f"knowledge node missing frontmatter: {knowledge_id!r}")
    try:
        _, raw_frontmatter, _ = text.split("---", 2)
        frontmatter: dict[str, Any] = yaml.safe_load(raw_frontmatter) or {}
    except ValueError as exc:
        raise VerificationError(f"knowledge frontmatter unparsable: {knowledge_id!r}") from exc
    if not isinstance(frontmatter, dict):
        raise VerificationError(f"knowledge frontmatter not a mapping: {knowledge_id!r}")
    generated = frontmatter.get("generated")
    if not isinstance(generated, dict) or generated.get("run_id") != run_id:
        raise VerificationError(f"knowledge node not owned by run {run_id}: {knowledge_id!r}")
    doc_type = frontmatter.get("type")
    if doc_type in REQUIRED_SOURCE_TYPES and not frontmatter.get("sources"):
        raise VerificationError(f"knowledge type {doc_type!r} requires sources: {knowledge_id!r}")
    return str(target.relative_to(store.root.parent).as_posix())


def parse_evidence_ref(ref: str) -> tuple[str, str]:
    """Parse ``kind:value`` evidence references; unparseable refs are rejected."""
    match = _EVIDENCE_RE.fullmatch(ref.strip())
    if not match:
        raise VerificationError(f"evidence ref not parseable (expected artifact:… / knowledge:… / tool-effect:…): {ref!r}")
    return match.group(1), match.group(2)


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


def verify_tool_effect(
    tool_call_id: str,
    *,
    step_store_dir: Path,
    run_id: str,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Verify a tool-effect ref resolves to a ledger entry owned by this run."""
    records = latest_tool_effects(
        records if records is not None else read_tool_effects(step_store_dir, run_id)
    )
    for record in records:
        if record.get("tool_call_id") == tool_call_id:
            if record.get("run_id") not in (None, run_id):
                raise VerificationError(f"tool-effect not owned by run {run_id}: {tool_call_id!r}")
            if record.get("status") == "started":
                raise VerificationError(f"tool-effect started but never settled: {tool_call_id!r}")
            return record
    raise VerificationError(f"tool-effect not in ledger: {tool_call_id!r}")
