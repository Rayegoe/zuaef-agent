"""Sequential-v1 experiment shared machinery.

Owns the three things every other script depends on:
  - paths and the authoritative evidence seams (static vs adaptive),
  - the leak-free gate (what may be visible when task Tn runs),
  - receipt schemas (run / judgment / promotion) and canonical JSON.

Anti-fabrication is structural here: there is no code path that *writes* an
operator judgment field — templates are written `null`, and promotion is
gated on an operator-confirmed judgment record.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

BENCH = Path(__file__).resolve().parents[3]
REPO = BENCH.parents[1]
EXP = Path(
    os.environ.get("ZUAEF_SEQUENTIAL_EXP_ROOT")
    or (BENCH / "experiments" / "sequential-v1")
)

RUNS = EXP / "runs"
JUDGMENTS = EXP / "judgments"
PROMOTIONS = EXP / "promotions"
PROMO_RECEIPTS = PROMOTIONS / "receipts"
CANDIDATES = PROMOTIONS / "candidates"
RUNTIME_EVIDENCE = PROMOTIONS / "runtime-evidence.jsonl"
COMPILED_EVIDENCE = BENCH / "compiled" / "evidence.jsonl"
TASKS_DIR = BENCH / "tasks"
FULL_TASKS_DIR = REPO / "data" / "derived" / "tasks_full"

MODES = ("base", "static", "adaptive")
TASK_IDS = [f"T{i:02d}" for i in range(1, 21)]
HUMAN_PATCH_WEIGHT = 4.0
HUMAN_PATCH_APPROVER = "operator:v1"

MOVE_RE = re.compile(r"\[editorial move \| (\w+) \| origin: (\w+)\]")
EVIDENCE_LINE_RE = re.compile(r"^evidence: (.+)$", re.MULTILINE)

# --- canonical serialization ---------------------------------------------------


def canon(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canon(obj) + "\n", encoding="utf-8")


def write_yaml_like(path: Path, lines: list[str]) -> None:
    """Deterministic template writer (no yaml dependency; strict schema)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


# --- benchmark data -------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict]:
    """Parse JSONL with fail-loud line numbers; skips blank lines."""
    if not path.is_file():
        return []
    records: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: malformed JSON — {exc}") from None
        if not isinstance(rec, dict):
            raise SystemExit(f"{path}:{lineno}: record must be a JSON object")
        records.append(rec)
    return records


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{path}: cannot load JSON — {exc}") from None


def task_rows() -> list[dict]:
    return load_jsonl(BENCH / "benchmark.jsonl")


def full_task(task_id: str) -> dict:
    path = FULL_TASKS_DIR / f"{task_id}.json"
    if not path.is_file():
        raise SystemExit(
            f"{path} missing — run scripts/fetch_sources.py && scripts/build_tasks.py"
        )
    return load_json(path)


# --- evidence seam (the B-vs-C difference) --------------------------------------


def corpus_entries() -> list[dict]:
    return load_jsonl(COMPILED_EVIDENCE)


def builtin_seed_ids() -> list[str]:
    return [
        f"seed.{s}"
        for s in (
            "template-connectors.001",
            "summary-pressure.001",
            "uniform-paragraphs.001",
            "low-concrete-anchor.001",
            "abstract-noun-density.001",
            "after-exemplar.001",
        )
    ]


def promoted_human_entries(promotion_receipts_dir: Path | None = None) -> list[dict]:
    """All human-patch entries promoted so far, from promotion receipts only.

    The directory is resolved at call time (a default arg would freeze the
    module path at import, breaking test/scratch overrides).
    """
    promo_dir = promotion_receipts_dir or PROMO_RECEIPTS
    entries: list[dict] = []
    for receipt in sorted(promo_dir.glob("T*.json")):
        rec = load_json(receipt)
        for patch in rec.get("patches", []):
            if patch.get("source_type") == "human_patch":
                entries.append(patch)
    return entries


def rebuild_runtime_evidence() -> int:
    """Regenerate promotions/runtime-evidence.jsonl from corpus + receipts.

    Derived file, never hand-edited: single source of truth for what adaptive
    mode may see is `promotions/receipts/*.json` + the compiled corpus.
    """
    entries = [*corpus_entries(), *promoted_human_entries()]
    RUNTIME_EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_EVIDENCE.write_text(
        "".join(canon(e) + "\n" for e in entries), encoding="utf-8"
    )
    return len([e for e in entries if e.get("source_type") == "human_patch"])


def available_evidence_snapshot(task_sequence: int) -> dict:
    """Exact snapshot of what adaptive task Tn is allowed to see.

    The leak-free invariant lives here: promoted human patches are the ones
    whose task sequence is strictly < n. No file reads — pure function of the
    promotion receipts, so it is unit-testable in isolation.
    """
    human = [
        p["id"] for p in promoted_human_entries() if task_sequence_of(p) < task_sequence
    ]
    seq = [task_sequence_of(p) for p in promoted_human_entries()]
    if max(seq, default=0) >= task_sequence:
        raise SystemExit(
            f"leak guard: future/current promotion detected (max seq {max(seq, default=0)} "
            f">= {task_sequence}) — refusing to snapshot adaptive evidence"
        )
    return {
        "task_sequence": task_sequence,
        "builtin_seed": builtin_seed_ids(),
        "corpus_observation": [e["id"] for e in corpus_entries()],
        "promoted_human_patch": sorted(human),
        "counts": {
            "builtin_seed": 6,
            "corpus_observation": len(corpus_entries()),
            "promoted_human_patch": len(human),
        },
    }


def task_sequence_of(entry: dict) -> int:
    """Recover the source task sequence from a patch/promotion id.

    Patch ids are `human.experiment.<T##>.<n>`; promotion receipts carry
    `source_task`. Fall back on scanning ids defensively.
    """
    if entry.get("source_task"):
        try:
            return int(entry["source_task"][1:])
        except ValueError:
            raise SystemExit(
                f"bad source_task {entry['source_task']!r} in {entry.get('id')!r}"
            ) from None
    match = re.search(r"human\.experiment\.(T\d\d)", entry.get("id", ""))
    if match:
        try:
            return int(match.group(1)[1:])
        except ValueError:
            pass
    raise SystemExit(f"cannot recover task sequence from {entry.get('id')!r}")


# --- run receipt schema ----------------------------------------------------------


def new_run_receipt(*, task_id: str, mode: str, evidence_snapshot: dict | None) -> dict:
    return {
        "schema_version": "1.0",
        "task_id": task_id,
        "mode": mode,
        "model": None,  # set by the runner
        "started_at": None,
        "finished_at": None,
        "available_evidence": evidence_snapshot,
        "retrieved_evidence": [],  # ids of evidence the interventions cited
        "signals": {},  # run_trajectory_sensors of final draft
        "intervention": {
            "moves": [],  # [action, origin] pairs in order
            "evidence_ids": [],
            "count": 0,
        },
        "save": {"veto_count": 0},
        "output": {"artifact_sha256": None, "draft_sha256": None},
        "judgment": {"status": "pending", "receipt_path": None},
        "promotion": {"promoted": False, "patch_id": None, "receipt_path": None},
    }


def finalize_run_receipt(
    rec: dict,
    *,
    trace: dict,
    signals: dict,
    draft: str,
    draft_sha256: str,
    model: str,
    started_at: str,
    finished_at: str,
    run_id: str | None = None,
) -> None:
    rec["model"] = model
    if run_id:
        rec["run_id"] = run_id
    rec["started_at"], rec["finished_at"] = started_at, finished_at
    rec["retrieved_evidence"] = sorted(trace.get("evidence_cited", []))
    rec["signals"] = {k: round(v, 4) for k, v in signals.items()}
    rec["intervention"] = {
        "moves": trace.get("interventions", []),
        "evidence_ids": sorted(trace.get("evidence_cited", [])),
        "count": len(trace.get("interventions", [])),
    }
    rec["save"]["veto_count"] = trace.get("save_vetoes", 0)
    rec["output"]["draft_sha256"] = draft_sha256
    rec["output"]["artifact_sha256"] = draft_sha256  # saved artifact == draft text path


def trace_from_messages(messages) -> dict:
    """Recover the editorial trace from run history (same recovery run_benchmark uses)."""
    interventions: list[str] = []
    evidence_ids: list[str] = []
    vetoes = 0
    from pydantic_ai.messages import RetryPromptPart

    for message in messages:
        for part in getattr(message, "parts", []):
            content = getattr(part, "content", "")
            if isinstance(content, str):
                interventions.extend(m["move"] for m in MOVE_RE.finditer(content))
                for line in EVIDENCE_LINE_RE.findall(content):
                    evidence_ids.extend(e.strip() for e in line.split(",") if e.strip())
            if isinstance(part, RetryPromptPart) and "EDITORIAL SAVE VETO" in str(
                getattr(part, "content", "")
            ):
                vetoes += 1
    return {
        "interventions": interventions,
        "evidence_cited": sorted(set(evidence_ids)),
        "save_vetoes": vetoes,
    }
