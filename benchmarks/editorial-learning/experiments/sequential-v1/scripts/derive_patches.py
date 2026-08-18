"""Derive candidate human-patch records from a confirmed judgment.

Strictly mechanical: reads judgments/T##.yaml (operator-confirmed), maps the
situation → action → instruction shape required by the EditorialEvidence
schema, validates every record through the real EditorialEvidenceStore, and
writes candidates to promotions/candidates/T##.json.

Nothing is promoted here — promotion happens only when run_experiment's
adaptive loop runs the confirmed task and moves the candidate into
promotions/receipts/. This keeps "candidate formation" and "promotion" as two
explicit, auditable steps.

The derived record is exactly an EditorialEvidence (extra="forbid"), so the
source task travels in the candidate/receipt CONTAINER (source_task), never
inside the record the runtime store loads.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[3]
REPO = BENCH.parents[1]
sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
sys.path[:0] = [str(Path(__file__).resolve().parent)]

# pyright: reportMissingImports=false
# (deliberate sys.path-bootstrapped seam imports)
import common
from zuaef_ace_writing.editorial import (
    COGNITIVE_ACTIONS,
    EditorialEvidenceStore,
)

FROZEN_ACTIONS = set(COGNITIVE_ACTIONS)
FROZEN_SENSORS = {
    "template_connectors",
    "summary_pressure",
    "uniform_paragraphs",
    "low_concrete_anchor_density",
    "abstract_noun_density",
}


def parse_judgment(path: Path) -> dict:
    """Parse the judgment YAML template (strict, no yaml dependency)."""
    if not path.is_file():
        raise SystemExit(f"judgment file missing: {path}")
    rec: dict[str, object] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise SystemExit(f"{path}:{lineno}: malformed line: {line!r}")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "interventions_useful":
            rec[key] = [s.strip() for s in value.strip("[]").split(",") if s.strip()]
            continue
        if value.lower() in ("null", ""):
            rec[key] = None
        elif value.lower() == "true":
            rec[key] = True
        elif value.lower() == "false":
            rec[key] = False
        elif "|" in value:  # block string for excerpts
            rec[key] = value.split("|")[-1].strip()
        else:
            rec[key] = value
    required = (
        "task_id",
        "status",
        "confirm",
        "patch_before",
        "patch_after",
        "action",
        "trigger_signals",
        "situation_tags",
    )
    missing = [k for k in required if k not in rec]
    if missing:
        raise SystemExit(f"{path}: missing required field(s): {missing}")
    return rec


def derive(judgment: dict, run_receipt: dict | None) -> list[dict]:
    """One or more human_patch records from a confirmed judgment."""
    tid = judgment["task_id"]
    before = judgment["patch_before"]
    after = judgment["patch_after"]
    if not before or not after or before == after:
        raise SystemExit(
            f"{tid}: patch_before/patch_after empty or identical — no edit to derive"
        )
    action = judgment["action"]
    if action not in FROZEN_ACTIONS:
        raise SystemExit(
            f"{tid}: action {action!r} not in frozen five {sorted(FROZEN_ACTIONS)}"
        )
    triggers = [
        s for s in str(judgment.get("trigger_signals", "")).split(",") if s.strip()
    ]
    for sig in triggers:
        if sig not in FROZEN_SENSORS:
            raise SystemExit(
                f"{tid}: trigger signal {sig!r} not in frozen five sensors"
            )
    tags = [s for s in str(judgment.get("situation_tags", "")).split(",") if s.strip()]
    run_sig = (run_receipt or {}).get("output", {}).get("draft_sha256") or "n/a"
    patch_id = f"human.experiment.{tid}.0"
    directive = judgment.get("directive") or (
        "Apply the operator's local edit: replace the vague or drifting "
        "formulation with the consciously revised one, keeping claims and the "
        "source ledger untouched."
    )
    rationale = judgment.get("rationale") or (
        f"Sequential-v1 experiment: operator revision of {tid} "
        f"(draft {run_sig[:12]}…). Minimal-patch edit confirmed by operator."
    )
    return [
        {
            "id": patch_id,
            "source_type": "human_patch",
            "source_ref": f"experiment:sequential-v1:{tid}#judgment",
            "situation_tags": tags or ["drafting"],
            "trigger_signals": triggers,
            "action": action,
            "directive": directive,
            "rationale": rationale,
            "weight": common.HUMAN_PATCH_WEIGHT,
            "approved_by": common.HUMAN_PATCH_APPROVER,
            "before_excerpt": before[:400],
            "after_excerpt": after[:400],
        }
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True, help="task id, e.g. T03")
    ap.add_argument("--judgment", help="judgment file (default judgments/T##.yaml)")
    ap.add_argument(
        "--dry-run", action="store_true", help="print records without writing"
    )
    args = ap.parse_args()
    tid = args.task.upper()
    judgment_path = (
        Path(args.judgment) if args.judgment else common.JUDGMENTS / f"{tid}.yaml"
    )
    judgment = parse_judgment(judgment_path)
    if judgment["status"] != "confirmed" or not judgment.get("confirm"):
        raise SystemExit(
            f"{judgment_path}: judgment not confirmed — refusing to derive"
        )
    run_receipt = None
    rec_path = common.RUNS / judgment["mode"] / f"{tid}_run.json"
    if rec_path.is_file():
        run_receipt = common.load_json(rec_path)
    patches = derive(judgment, run_receipt)
    # validate through the real store (raises on schema/action violations)
    tmp = common.EXP / ".validate-tmp.jsonl"
    tmp.write_text("".join(common.canon(p) + "\n" for p in patches), encoding="utf-8")
    EditorialEvidenceStore(tmp)
    tmp.unlink()
    if args.dry_run:
        for p in patches:
            print(common.canon(p))
        return
    out = common.CANDIDATES / f"{tid}.json"
    common.write_json(
        out,
        {
            "schema_version": "1.0",
            "task_id": tid,
            "source_task": tid,
            "judgment_path": str(judgment_path.relative_to(common.EXP)),
            "derive_script": "derive_patches.py",
            "count": len(patches),
            "patches": patches,
        },
    )
    print(
        f"derived {len(patches)} candidate patch(es) for {tid} -> {out.relative_to(common.REPO)}"
    )


if __name__ == "__main__":
    main()
