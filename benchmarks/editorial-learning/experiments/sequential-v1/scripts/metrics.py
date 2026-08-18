"""Aggregate sequential-v1 receipts into metrics.json (KPI aggregation).

Machine-side rows come only from real run receipts. Human-sourced KPIs
(blind preference, edit burden, intervention usefulness, claim preservation,
full-rewrite rate) are computed from judgments/ when present and reported as
PENDING otherwise — this script has no way and no permission to fill them.

The output is deterministic in the receipt set: same receipts, same bytes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]

import common
from common import JUDGMENTS, PROMO_RECEIPTS, RUNS, TASK_IDS

MODES = ("base", "static", "adaptive")


def load_runs(mode: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted((RUNS / mode).glob("T*_run.json")):
        out[p.stem] = common.load_json(p)
    return out


def load_judgments() -> list[dict]:
    records = []
    for p in sorted(JUDGMENTS.glob("T*.yaml")):
        path = p.read_text(encoding="utf-8")
        rec: dict = {"task_id": p.stem, "confirm": False, "status": "pending"}
        for line in path.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key == "preferred":
                rec[key] = value if value != "null" else None
            elif key == "confirm":
                rec[key] = value == "true"
            elif key == "status" or key == "mode":
                rec[key] = value
            elif key == "human_edit_proportion":
                try:
                    rec[key] = float(value) if value != "null" else None
                except ValueError:
                    rec[key] = None
            elif key == "claim_preserved" or key == "full_rewrite":
                rec[key] = value == "true"
            elif key == "interventions_useful":
                rec[key] = [
                    s.strip() == "true"
                    for s in value.strip("[]").split(",")
                    if s.strip()
                ]
        records.append(rec)
    return records


def machine_rows(mode: str, runs: dict[str, dict]) -> dict:
    tasks = len(runs)
    interventions = sum(r["intervention"]["count"] for r in runs.values())
    vetoes = sum(r["save"]["veto_count"] for r in runs.values())
    return {
        "tasks": tasks,
        "interventions_total": interventions,
        "interventions_per_task": round(interventions / tasks, 2) if tasks else None,
        "save_vetoes": vetoes,
        "evidence_cited": sum(len(r["retrieved_evidence"]) for r in runs.values()),
        "human_patch_citations": sum(
            1
            for r in runs.values()
            for e in r["retrieved_evidence"]
            if e.startswith("human.experiment.")
        ),
    }


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def human_rows(judgments: list[dict], runs_by_mode: dict[str, dict[str, dict]]) -> dict:
    confirmed = [j for j in judgments if j.get("confirm")]
    preferred: list[str] = [
        str(j.get("preferred")) for j in confirmed if j.get("preferred")
    ]
    useful_lists = [j.get("interventions_useful") or [] for j in confirmed]
    useful = [u for lst in useful_lists for u in lst if isinstance(u, bool)]
    edit_burden: list[float] = [
        parsed
        for j in confirmed
        if (parsed := _as_float(j.get("human_edit_proportion"))) is not None
    ]
    claimed = [
        j.get("claim_preserved")
        for j in confirmed
        if isinstance(j.get("claim_preserved"), bool)
    ]
    rewrites = [j for j in confirmed if isinstance(j.get("full_rewrite"), bool)]

    def _p(pending: bool, value) -> dict:
        return {"pending": pending, "value": value}

    kpis = {
        "blind_preference": _p(
            not preferred,
            {
                "adaptive_wins": preferred.count("adaptive"),
                "static_wins": preferred.count("static"),
                "base_wins": preferred.count("base"),
                "ties": preferred.count("tie"),
            },
        ),
        "intervention_precision": _p(
            not useful,
            {
                "useful_total": sum(useful),
                "interventions_judged": len(useful),
                "rate": round(sum(useful) / len(useful), 3) if useful else None,
            },
        ),
        "false_intervention_rate": _p(
            not useful,
            {
                "false_total": len(useful) - sum(useful),
                "interventions_judged": len(useful),
                "rate": round((len(useful) - sum(useful)) / len(useful), 3)
                if useful
                else None,
            },
        ),
        "human_edit_burden": _p(
            not edit_burden,
            {
                "tasks_judged": len(edit_burden),
                "mean_proportion": round(sum(edit_burden) / len(edit_burden), 3)
                if edit_burden
                else None,
                "by_task": {
                    f"{j['task_id']}_{j['mode']}": j.get("human_edit_proportion")
                    for j in confirmed
                    if (j.get("human_edit_proportion")) is not None
                },
            },
        ),
        "claim_preservation": _p(
            not claimed,
            {
                "tasks_judged": len(claimed),
                "preserved": sum(1 for c in claimed if c),
                "rate": round(sum(1 for c in claimed if c) / len(claimed), 3)
                if claimed
                else None,
            },
        ),
        "full_rewrite_rate": _p(
            not rewrites,
            {
                "tasks_judged": len(rewrites),
                "full_rewrites": sum(1 for r in rewrites if r.get("full_rewrite")),
                "rate": round(
                    sum(1 for r in rewrites if r.get("full_rewrite")) / len(rewrites),
                    3,
                )
                if rewrites
                else None,
            },
        ),
    }
    # per-task judgment summary for the trend table
    trend = {
        j["task_id"]: {
            "mode": j["mode"],
            "preferred": j.get("preferred"),
            "human_edit_proportion": j.get("human_edit_proportion"),
            "claim_preserved": j.get("claim_preserved"),
            "full_rewrite": j.get("full_rewrite"),
        }
        for j in confirmed
    }
    return {"kpis": kpis, "trend": trend}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(common.EXP / "metrics.json"))
    args = ap.parse_args()

    runs_by_mode = {m: load_runs(m) for m in MODES}
    judgments = load_judgments()
    machine = {m: machine_rows(m, runs_by_mode[m]) for m in MODES}
    hm = human_rows(judgments, runs_by_mode)

    adaptive_reuse = machine["adaptive"].get("human_patch_citations", 0)
    adaptive_interventions = machine["adaptive"].get("interventions_total", 0)
    evidence_reuse = {
        "pending": False,
        "adaptive_human_patch_citations": adaptive_reuse,
        "adaptive_interventions_total": adaptive_interventions,
        "reuse_rate": round(adaptive_reuse / adaptive_interventions, 3)
        if adaptive_interventions
        else None,
    }
    static_seed = 0
    adaptive_seed = 0
    static_human = 0
    adaptive_human = 0
    for r in runs_by_mode["static"].values():
        static_seed += sum(1 for e in r["retrieved_evidence"] if e.startswith("seed."))
    for r in runs_by_mode["adaptive"].values():
        adaptive_seed += sum(
            1 for e in r["retrieved_evidence"] if e.startswith("seed.")
        )
        adaptive_human += sum(
            1 for e in r["retrieved_evidence"] if e.startswith("human.experiment.")
        )
    ratio = {
        "pending": False,
        "static": {"seed_citations": static_seed, "human_citations": static_human},
        "adaptive": {
            "seed_citations": adaptive_seed,
            "human_citations": adaptive_human,
        },
        "adaptive_human_patch_share": round(
            adaptive_human / (adaptive_human + adaptive_seed), 3
        )
        if (adaptive_human + adaptive_seed)
        else None,
    }

    manifest_versions = {}
    for mode in MODES:
        manifest_versions[mode] = {
            tid: common.sha256_file(RUNS / mode / f"{tid}_run.json")
            for tid in TASK_IDS
            if (RUNS / mode / f"{tid}_run.json").is_file()
        }

    metrics = {
        "schema_version": "1.0",
        "modes": machine,
        "adaptive_evidence_reuse": evidence_reuse,
        "human_patch_seed_ratio": ratio,
        "judgments": {
            "templates_written": len(judgments),
            "confirmed": sum(1 for j in judgments if j.get("confirm")),
        },
        "human_kpis": hm["kpis"],
        "trend": hm["trend"],
        "promotions": {
            "count": len(list(PROMO_RECEIPTS.glob("T*.json"))),
            "tasks": sorted(p.stem for p in PROMO_RECEIPTS.glob("T*.json")),
        },
        "run_sha256": manifest_versions,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(common.canon(metrics) + "\n", encoding="utf-8")
    print(common.canon(metrics))


if __name__ == "__main__":
    main()
