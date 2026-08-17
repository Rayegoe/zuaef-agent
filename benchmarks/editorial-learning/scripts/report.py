#!/usr/bin/env python3
"""Aggregate results/{base,static,adaptive} into the learning KPI report.

Machine-side KPIs only (evidence reuse, seed vs human ratio, intervention
and veto counts, drift trend). Blind preference and human edit distance are
human fields: report.py shows them as PENDING until a judgment file exists
(results/judgments.jsonl with task_id/mode/preferred fields).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
MODES = ("base", "static", "adaptive")


def load_runs(mode: str) -> list[dict]:
    directory = BENCH / "results" / mode
    if not directory.is_dir():
        return []
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("T*_run.json"))
    ]


def kpi(runs: list[dict]) -> dict:
    if not runs:
        return {"tasks": 0}
    human = sum(
        1 for r in runs
        for e in r.get("evidence_cited", []) if e.startswith("human.")
    )
    seed = sum(
        1 for r in runs
        for e in r.get("evidence_cited", []) if e.startswith("seed.")
    )
    total_interventions = sum(len(r.get("interventions", [])) for r in runs)
    return {
        "tasks": len(runs),
        "interventions_total": total_interventions,
        "interventions_per_task": round(total_interventions / len(runs), 2),
        "save_vetoes": sum(r.get("save_vetoes", 0) for r in runs),
        "evidence_citations": {"human": human, "seed": seed},
        "human_patch_share": round(human / (human + seed), 3) if (human + seed) else None,
    }


def main() -> None:
    judgments = BENCH / "results" / "judgments.jsonl"
    blind = "PENDING (no results/judgments.jsonl)" if not judgments.is_file() else "present"
    rows = {}
    for mode in MODES:
        rows[mode] = kpi(load_runs(mode))
    print(f"blind human judgment: {blind}\n")
    for mode in MODES:
        print(f"{mode:>8}: {json.dumps(rows[mode], ensure_ascii=False)}")
    static, adaptive = rows["static"], rows["adaptive"]
    if static.get("tasks") and adaptive.get("tasks"):
        print("\nB>C learning signal (machine-side):")
        print(f"  human_patch_share: static={static['human_patch_share']} "
              f"adaptive={adaptive['human_patch_share']}")
    if not any(rows[m]["tasks"] for m in MODES):
        print("\nno results yet — run scripts/run_benchmark.py --mode {base|static|adaptive}")
        sys.exit(0)


if __name__ == "__main__":
    main()
