"""Shared host-runner machinery for production showcase cases.

Both case runners (``sanlian_showcase.py``, ``case_showcase.py``) build the
same kind of workbench: caller-selected Writing Skill packs, deterministic
showcase directories, JSON-clean receipts. Everything here is deterministic —
no model calls, no benchmark joins. Case-specific content (task, writing
plan, prompts, README wording) stays in each runner.
"""

from __future__ import annotations

import difflib
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

BENCH = REPO / "benchmarks" / "editorial-learning"
DEFAULT_TECHNIQUES = BENCH / "curated" / "techniques.jsonl"
DEFAULT_MEMORY = BENCH / "compiled" / "evidence.jsonl"

# The curated Writing Skill pack ids (caller-selected methodology records).
TECHNIQUE_IDS = (
    "T001",
    "T002",
    "T003",
    "T004",
    "T005",
    "T006",
    "T007",
    "T008",
    "T009",
    "T010",
    "T011",
    "T012",
    "T013",
    "T014",
    "T015",
    "T016",
    "T017",
    "T018",
    "T019",
    "T020",
)


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"missing jsonl: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_techniques(path: Path = DEFAULT_TECHNIQUES) -> list[dict]:
    """The curated Writing Skill pack (caller-owned methodology records)."""
    records = load_jsonl(path)
    wanted = set(TECHNIQUE_IDS)
    selected = [t for t in records if t.get("id") in wanted]
    if len(selected) != len(TECHNIQUE_IDS):
        raise SystemExit(
            f"technique pack incomplete: expected {len(TECHNIQUE_IDS)} ids, "
            f"found {len(selected)} in {path}"
        )
    return selected


def select_memory(path: Path = DEFAULT_MEMORY) -> list[dict]:
    """Corpus evidence records as editorial memory (caller-owned)."""
    records = load_jsonl(path)
    wanted = {f"corpus.{tid}" for tid in TECHNIQUE_IDS}
    selected = [e for e in records if e.get("id") in wanted]
    if len(selected) != len(TECHNIQUE_IDS):
        raise SystemExit(
            f"memory pack incomplete: expected {len(TECHNIQUE_IDS)} ids, "
            f"found {len(selected)} in {path}"
        )
    return selected


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def json_default(obj: Any) -> Any:
    """Run receipts carry Decimal token counts / datetimes — keep JSON-clean."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_showcase_inputs(
    showcase: Path,
    *,
    task: dict,
    writing_plan: dict,
    files: list,
) -> None:
    """Raw material files (exact bytes) + the host-authored writing plan."""
    for f in files:
        write_text(showcase / f"01-raw-{Path(f.source_ref).name}", f.text)
    write_text(
        showcase / "02-writing-plan.md",
        "# 写作计划（host-authored）\n\n"
        f"## task\n\n```json\n{json.dumps(task, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## writing_plan\n\n```json\n"
        f"{json.dumps(writing_plan, ensure_ascii=False, indent=2)}\n```\n",
    )


def write_showcase_results(
    showcase: Path,
    *,
    identity: dict,
    writer_record: dict,
    editor_record: dict,
    workspace_root: Path,
) -> tuple[str, str]:
    """Writer draft / editor final / diff / receipt (identity is runner-owned
    receipt prefix: fixture or case record + task + plan + packs)."""
    from examples.production_writing import final_artifact_text

    draft_text, _ = final_artifact_text(workspace_root, writer_record["run_id"])
    final_text, _ = final_artifact_text(workspace_root, editor_record["run_id"])
    write_text(showcase / "03-writer-draft.md", draft_text)
    write_text(showcase / "04-editor-final.md", final_text)
    diff = "".join(
        difflib.unified_diff(
            draft_text.splitlines(keepends=True),
            final_text.splitlines(keepends=True),
            fromfile="03-writer-draft.md",
            tofile="04-editor-final.md",
        )
    )
    write_text(
        showcase / "05-diff-writer-to-final.diff",
        diff or "(writer draft and editor final are identical)\n",
    )
    write_text(
        showcase / "receipt.json",
        json.dumps(
            {
                **identity,
                "writer": writer_record,
                "editor": editor_record,
            },
            ensure_ascii=False,
            indent=2,
            default=json_default,
        ),
    )
    return draft_text, final_text
