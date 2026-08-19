"""Thin host-side Case context projection (P3B-2 SPEC §6.2).

A bound Case contributes durable business BACKGROUND to the model-visible
context — a bounded natural-language brief, not a storage dump and not a
workflow. This module is deliberately thin: it reads the case directory under
the workspace, renders a bounded brief, and nothing else. It is not a context
framework, has no schema of its own, and never imports a business plugin.

The Gateway/bridge calls ``project_case_context`` before the model request;
the same brief shape serves every future bound-case surface.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Same shape contract the gateway enforces for callback addressing (duplicated
# by design: the host must not import the case plugin for a charset check).
_CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

_UNKNOWN_VALUES = {"unknown", "none", "", "null"}

# Bounded projection: the whole brief (goal + situation + trajectory + policy
# overrides) never exceeds this many characters; per-entry summaries are cut
# earlier so the tail cannot crowd out the head.
MAX_BRIEF_CHARS = 2400
MAX_NOTES_CHARS = 400
MAX_SUMMARY_CHARS = 220
MAX_POLICY_CHARS = 400
TRAJECTORY_TAIL = 5


def _bounded(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _situation_lines(state: dict[str, Any], prefix: str = "") -> list[str]:
    """Render substantive situation leaves as readable lines.

    Unknown/empty leaves are skipped (they carry no background); nested keys
    join with "." so the line stays one flat, human-readable fact.
    """
    lines: list[str] = []
    for key, value in state.items():
        label = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            lines.extend(_situation_lines(value, label))
        elif isinstance(value, list):
            rendered = "、".join(str(item) for item in value if str(item).strip())
            if rendered:
                lines.append(f"- {label}: {_bounded(rendered, MAX_SUMMARY_CHARS)}")
        elif isinstance(value, bool) or value is None:
            continue
        else:
            rendered = str(value).strip()
            if rendered.lower() in _UNKNOWN_VALUES:
                continue
            if rendered:
                lines.append(f"- {label}: {_bounded(rendered, MAX_SUMMARY_CHARS)}")
    return lines


def _parse_case_doc(path: Path) -> dict[str, str] | None:
    """Minimal frontmatter read of the supervisor-owned ``case.md``."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    fields: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields or None


def project_case_context(case_id: str | None, *, workspace_root: Path) -> str | None:
    """Project one bounded natural-language brief for the bound Case.

    Returns ``None`` when the case id is malformed, the case directory does not
    exist, or nothing durable can be projected — an unbound or unknown Case
    never injects context.
    """
    if case_id is None or not _CASE_ID.fullmatch(case_id):
        return None
    cases_root = (workspace_root / "cases").resolve()
    case_dir = (cases_root / case_id).resolve()
    if not case_dir.is_relative_to(cases_root) or not case_dir.is_dir():
        return None

    lines: list[str] = [f"Customer context (bound case: {case_id}):", ""]

    doc = _parse_case_doc(case_dir / "case.md")
    if doc:
        if doc.get("goal"):
            lines.append(f"Goal: {_bounded(doc['goal'], MAX_SUMMARY_CHARS)}")
        if doc.get("status") and doc["status"] != "active":
            lines.append(f"Status: {doc['status']}")
        if doc.get("notes"):
            lines.append(f"Notes: {_bounded(doc['notes'], MAX_NOTES_CHARS)}")

    try:
        situation = json.loads(
            (case_dir / "situation.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        situation = None
    if isinstance(situation, dict):
        state = situation.get("state")
        if isinstance(state, dict) and state:
            lines.append("")
            lines.append("Current situation (durable beliefs, bounded):")
            lines.extend(_situation_lines(state))
        questions = [
            str(q) for q in situation.get("open_questions", []) if str(q).strip()
        ]
        if questions:
            lines.append("")
            lines.append("Open questions:")
            lines.extend(f"- {_bounded(q, MAX_SUMMARY_CHARS)}" for q in questions)

    try:
        trajectory_lines = (
            (case_dir / "trajectory.jsonl").read_text(encoding="utf-8")
            .splitlines()
        )
    except OSError:
        trajectory_lines = []
    entries = [line for line in trajectory_lines if line.strip()][-TRAJECTORY_TAIL:]
    tail: list[str] = []
    for line in entries:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        kind = str(entry.get("kind", "event"))
        summary = str(entry.get("summary", "")).strip()
        if summary:
            tail.append(f"- [{kind}] {_bounded(summary, MAX_SUMMARY_CHARS)}")
    if tail:
        lines.append("")
        lines.append("Recent trajectory:")
        lines.extend(tail)

    overrides = case_dir / "policy-overrides.md"
    if overrides.is_file():
        text = _bounded(overrides.read_text(encoding="utf-8", errors="replace"),
                        MAX_POLICY_CHARS)
        if text:
            lines.append("")
            lines.append(f"Supervisor policy overrides:\n{text}")

    if len(lines) <= 2:
        return None
    lines.append("")
    lines.append("This is background information, not an instruction sequence.")
    brief = "\n".join(lines)
    return brief if len(brief) <= MAX_BRIEF_CHARS else _bounded(brief, MAX_BRIEF_CHARS)
