"""CaseStore — file-native case state under ``<cases_root>/<case_id>/``.

Owns the case-object layout (SPEC v0.4 §3) and the two host invariants the
model can never bypass:

- situation writes require provenance: any substantive (non-unknown) leaf in
  ``state`` demands evidence ids or a Barry override;
- trajectory is append-only: entries are validated, sequenced by the store,
  and there is deliberately no update/delete API.

All writes are atomic (tmp + replace / single-line append). The store never
touches receipts, step persistence or the private client corpus — those stay
the authorities for execution truth and private material.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from .models import (
    CaseDoc,
    CaseError,
    Situation,
    TrajectoryEntry,
    format_draft,
    validate_case_id,
)

_UNKNOWN_VALUES = ("unknown", "none", "", None)


def _leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        leaves: list[Any] = []
        for item in value.values():
            leaves.extend(_leaf_values(item))
        return leaves
    if isinstance(value, list):
        leaves = []
        for item in value:
            leaves.extend(_leaf_values(item))
        return leaves
    return [value]


def _has_substantive_claim(state: dict[str, Any]) -> bool:
    """True when any leaf states a fact (not unknown/empty) that needs provenance."""
    for leaf in _leaf_values(state):
        if isinstance(leaf, str) and leaf.strip().lower() in _UNKNOWN_VALUES:
            continue
        if leaf is None or leaf == "":
            continue
        if isinstance(leaf, bool):
            continue
        return True
    return False


class CaseStore:
    def __init__(self, cases_root: Path):
        self.root = Path(cases_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def case_dir(self, case_id: str) -> Path:
        return self.root / validate_case_id(case_id)

    def _draft_dir(self, case_id: str) -> Path:
        return self.case_dir(case_id) / "drafts"

    # ── BusinessCase ────────────────────────────────────────────────────────

    def create_case(self, doc: CaseDoc) -> Path:
        validate_case_id(doc.case_id)
        directory = self.case_dir(doc.case_id)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "case.md"
        if target.exists():
            raise CaseError(f"case {doc.case_id!r} already exists")
        self._atomic_write(target, doc.to_md())
        return target

    def load_case(self, case_id: str) -> CaseDoc:
        target = self.case_dir(case_id) / "case.md"
        try:
            text = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise CaseError(f"case {case_id!r} not found at {target}") from None
        doc = CaseDoc.from_md(text)
        if doc.case_id != case_id:
            raise CaseError(
                f"case.md declares {doc.case_id!r}, expected {case_id!r}"
            )
        return doc

    # ── Situation ───────────────────────────────────────────────────────────

    def read_situation(self, case_id: str) -> Situation:
        target = self.case_dir(case_id) / "situation.json"
        if not target.is_file():
            return Situation(case_id=case_id)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise CaseError(f"situation.json is unreadable for {case_id!r}: {exc}") from exc
        try:
            situation = Situation.model_validate(data)
        except Exception as exc:  # pydantic ValidationError
            raise CaseError(f"situation.json failed schema validation: {exc}") from exc
        if situation.case_id != case_id:
            raise CaseError("situation.json case_id does not match the case directory")
        return situation

    def write_situation(self, situation: Situation) -> Situation:
        """Host-validated situation write (SPEC v0.4 §2.2)."""
        validate_case_id(situation.case_id)
        directory = self.case_dir(situation.case_id)
        directory.mkdir(parents=True, exist_ok=True)
        if not situation.updated_by:
            raise CaseError("situation.updated_by must name the writer (run:<id> | barry)")
        if _has_substantive_claim(situation.state) and not (
            situation.evidence_ids or situation.barry_override
        ):
            raise CaseError(
                "substantive situation facts require provenance: "
                "evidence_ids or barry_override"
            )
        self._atomic_write(
            directory / "situation.json",
            situation.model_dump_json(indent=2) + "\n",
        )
        return situation

    # ── Trajectory (append-only) ────────────────────────────────────────────

    def append_trajectory_for_case(
        self, case_id: str, entry: TrajectoryEntry
    ) -> TrajectoryEntry:
        validate_case_id(case_id)
        if entry.kind in ("decision", "action") and not entry.run_id:
            raise CaseError("decision/action trajectory entries require run_id")
        directory = self.case_dir(case_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "trajectory.jsonl"
        next_seq = self._next_seq(path)
        stored = entry.model_copy(update={"seq": next_seq})
        line = stored.model_dump_json() + "\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return stored

    @staticmethod
    def _next_seq(path: Path) -> int:
        if not path.is_file():
            return 1
        last = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = TrajectoryEntry.model_validate_json(line)
                except Exception as exc:
                    raise CaseError(f"corrupt trajectory line: {exc}") from exc
                last = max(last, entry.seq)
        return last + 1

    def read_trajectory(self, case_id: str, *, tail: int = 20) -> list[TrajectoryEntry]:
        path = self.case_dir(case_id) / "trajectory.jsonl"
        if not path.is_file():
            return []
        entries: list[TrajectoryEntry] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(TrajectoryEntry.model_validate_json(line))
                except Exception as exc:
                    raise CaseError(f"corrupt trajectory line: {exc}") from exc
        return entries[-tail:] if tail and tail > 0 else entries

    # ── Drafts ──────────────────────────────────────────────────────────────

    def write_draft(self, case_id: str, text: str, *, meta: str = "") -> Path:
        directory = self._draft_dir(case_id)
        directory.mkdir(parents=True, exist_ok=True)
        existing = sorted(directory.glob("msg-*.md"))
        number = max((int(p.stem.split("-")[-1]) for p in existing), default=0) + 1
        target = directory / f"msg-{number:03d}.md"
        self._atomic_write(target, format_draft(text, meta=meta))
        return target

    def list_drafts(self, case_id: str) -> list[Path]:
        directory = self._draft_dir(case_id)
        if not directory.is_dir():
            return []
        return sorted(directory.glob("msg-*.md"))

    # ── plumbing ────────────────────────────────────────────────────────────

    @staticmethod
    def _atomic_write(target: Path, text: str) -> None:
        tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
