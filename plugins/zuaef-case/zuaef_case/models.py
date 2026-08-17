"""Typed models for the Business Case Agent (SPEC v0.4 §2).

The four case objects are file-native vocabulary: ``CaseDoc`` (BusinessCase),
``Situation``, ``TrajectoryEntry`` (Trajectory), plus drafts. Models carry no
business logic; the store owns validation and append-only semantics.
"""

from __future__ import annotations

import re
import textwrap
from datetime import UTC, datetime
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

_CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class CaseError(RuntimeError):
    """A case-object problem: invalid id, missing file, failed validation."""


def validate_case_id(case_id: str) -> str:
    if not _CASE_ID.fullmatch(case_id):
        raise CaseError(f"invalid case_id: {case_id!r}")
    return case_id


class CaseDoc(BaseModel):
    """BusinessCase (SPEC v0.4 §2.1): the long-lived goal binding runs together.

    Serialized as ``case.md`` — YAML frontmatter plus free-text notes. The
    file is supervisor-editable only (core-protected path).
    """

    case_id: str
    goal: str = Field(min_length=1)
    status: Literal["active", "paused", "closed"] = "active"
    stakeholders: dict[str, str] = Field(default_factory=dict)
    supervisor_chat_id: str = ""
    customer_chat_id: str = ""
    started_at: datetime | None = None
    notes: str = ""

    def to_md(self) -> str:
        validate_case_id(self.case_id)
        front = self.model_dump(exclude={"notes", "case_id"})
        if front.get("started_at") is not None:
            front["started_at"] = front["started_at"].astimezone(UTC).isoformat()
        payload = {"case_id": self.case_id, **front}
        body = yaml.safe_dump(
            payload, allow_unicode=True, sort_keys=False, default_flow_style=False
        ).strip()
        notes = self.notes.strip()
        if notes:
            return f"---\n{body}\n---\n\n{notes}\n"
        return f"---\n{body}\n---\n"

    @classmethod
    def from_md(cls, text: str) -> CaseDoc:
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, re.DOTALL)
        if not match:
            raise CaseError("case.md must start with YAML frontmatter (--- ... ---)")
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            raise CaseError(f"case.md frontmatter is not valid YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise CaseError("case.md frontmatter must be a mapping")
        try:
            return cls(**data, notes=match.group(2).strip())
        except ValidationError as exc:
            raise CaseError(f"case.md failed schema validation: {exc}") from exc


class Situation(BaseModel):
    """Situation (SPEC v0.4 §2.2): what the agent currently believes.

    ``state`` holds typed business sections (customer/problem/commercial/demo…).
    Every substantive (non-unknown) leaf requires provenance — evidence ids or
    a Barry override — enforced by the store on write, not by the model.
    """

    schema_version: int = 1
    case_id: str
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_by: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    barry_override: str | None = None


class TrajectoryEntry(BaseModel):
    """One append-only trajectory line (SPEC v0.4 §2.4).

    ``seq`` is assigned by the store; entries are never updated or deleted.
    A decision/action entry must carry the run_id whose receipt is its truth.
    """

    seq: int = 0
    ts: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    kind: Literal["event", "decision", "action", "feedback", "override", "approval"]
    role: Literal["customer", "agent", "barry", "system"]
    run_id: str = ""
    summary: str = Field(min_length=1)
    refs: dict[str, Any] = Field(default_factory=dict)


def format_draft(text: str, *, meta: str = "") -> str:
    """Render a draft message file body (SPEC v0.4 §6)."""
    header = f"<!-- {meta} -->\n" if meta else ""
    return header + textwrap.dedent(text).strip() + "\n"
