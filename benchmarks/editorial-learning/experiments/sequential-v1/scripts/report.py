"""Render metrics.json into the sequential-v1 REPORT.md.

Deterministic in the metrics input. Human KPIs render as PENDING with a clear
"what to do next" note; machine KPIs render as tables. The trend table shows
tasks with confirmed judgments, else marks them awaiting operator judgment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent)]

import common
from common import PROMO_RECEIPTS, TASK_IDS

MODES = ("base", "static", "adaptive")


def _kpi_line(label: str, pending: bool, summary: str) -> str:
    mark = "PENDING" if pending else "ok"
    return f"| {label} | **{mark}** | {summary} |\n"


def render(metrics: dict) -> str:
    lines: list[str] = []
    lines.append("# ZUAEF Editorial Sequential Learning Experiment — REPORT\n")
    lines.append(
        "Claim under test: the same model + Writing Agent improves across "
        "T01→T20 from sequentially promoted human patches, versus a static "
        "corpus-only agent. B>A ⇒ control works; C>B ⇒ learning works.\n"
    )
    lines.append("## Current state\n")
    modes = metrics["modes"]
    lines.append(
        "| mode | tasks | interventions | per-task | vetoes | evidence cited |\n"
    )
    lines.append("|---|---|---|---|---|---|\n")
    for m in MODES:
        row = modes[m]
        per = (
            "-"
            if row["interventions_per_task"] is None
            else row["interventions_per_task"]
        )
        lines.append(
            f"| {m} | {row['tasks']} | {row['interventions_total']} | {per} | "
            f"{row['save_vetoes']} | {row['evidence_cited']} |\n"
        )
    promo = metrics["promotions"]
    lines.append(
        f"\nPromotions: {promo['count']} "
        f"({', '.join(promo['tasks']) if promo['tasks'] else 'none'})\n"
    )

    lines.append("\n## KPIs\n")
    lines.append("| KPI | state | value |\n|---|---|---|\n")
    k = metrics["human_kpis"]
    bp = k["blind_preference"]
    if bp["pending"]:
        lines.append(_kpi_line("Blind preference", True, "awaiting judgments"))
    else:
        v = bp["value"]
        lines.append(
            _kpi_line(
                "Blind preference",
                False,
                f"adaptive wins {v['adaptive_wins']} · static {v['static_wins']} · "
                f"base {v['base_wins']} · ties {v['ties']}",
            )
        )
    ip = k["intervention_precision"]
    lines.append(
        _kpi_line(
            "Intervention precision",
            ip["pending"],
            "-"
            if ip["value"]["rate"] is None
            else f"{ip['value']['rate']} "
            f"({ip['value']['useful_total']}/{ip['value']['interventions_judged']})",
        )
    )
    fi = k["false_intervention_rate"]
    lines.append(
        _kpi_line(
            "False intervention rate",
            fi["pending"],
            "-" if fi["value"]["rate"] is None else f"{fi['value']['rate']}",
        )
    )
    eb = k["human_edit_burden"]
    lines.append(
        _kpi_line(
            "Human edit burden",
            eb["pending"],
            "-"
            if eb["value"]["mean_proportion"] is None
            else f"mean {eb['value']['mean_proportion']} of draft edited "
            f"({eb['value']['tasks_judged']} tasks)",
        )
    )
    cp = k["claim_preservation"]
    lines.append(
        _kpi_line(
            "Claim preservation",
            cp["pending"],
            "-" if cp["value"]["rate"] is None else f"{cp['value']['rate']} preserved",
        )
    )
    fr = k["full_rewrite_rate"]
    lines.append(
        _kpi_line(
            "Full rewrite rate",
            fr["pending"],
            "-" if fr["value"]["rate"] is None else f"{fr['value']['rate']}",
        )
    )
    reuse = metrics["adaptive_evidence_reuse"]
    lines.append(
        _kpi_line(
            "Evidence reuse rate",
            False,
            "-"
            if reuse["reuse_rate"] is None
            else f"{reuse['reuse_rate']} "
            f"({reuse['adaptive_human_patch_citations']} human-patch citations / "
            f"{reuse['adaptive_interventions_total']} adaptive interventions)",
        )
    )
    ratio = metrics["human_patch_seed_ratio"]
    share = ratio["adaptive_human_patch_share"]
    lines.append(
        _kpi_line(
            "Human-patch / seed ratio",
            False,
            "-"
            if share is None
            else f"adaptive human share {share} "
            f"(human {ratio['adaptive']['human_citations']} / "
            f"seed {ratio['adaptive']['seed_citations']})",
        )
    )

    lines.append("\n## Trend (T01 → T20)\n")
    trend = metrics["trend"]
    if not trend:
        lines.append(
            "No confirmed judgments yet — the table appears once "
            "operator judgments are recorded.\n"
        )
    else:
        lines.append(
            "| task | mode | preferred | edit proportion | claim preserved | full rewrite |\n"
        )
        lines.append("|---|---|---|---|---|---|\n")
        for tid in TASK_IDS:
            if tid not in trend:
                continue
            t = trend[tid]
            lines.append(
                f"| {tid} | {t['mode']} | {t['preferred'] or '-'} | "
                f"{t['human_edit_proportion'] or '-'} | {t['claim_preserved'] or '-'} | "
                f"{t['full_rewrite'] or '-'} |\n"
            )
    lines.append("\n## How to read this\n")
    lines.append(
        "The success trajectory we are looking for is not a drift number: seed "
        "use 高→低, human-patch dominance 0→主导, interventions 多→少 **while** "
        "precision rises, edit burden falls, and claims stay intact. "
        "Interventions down + usefulness up is the strongest signal that the "
        "editor is forming judgment, not pattern-matching.\n"
    )
    lines.append("\n## Next operator steps\n")
    next_pending = sorted(p.stem for p in common.JUDGMENTS.glob("T*.yaml"))
    if not next_pending:
        lines.append(
            "- Run `run_experiment.py --mode adaptive` to produce the "
            "first judgment template.\n"
        )
    else:
        for tid in next_pending:
            if tid not in {p.stem for p in PROMO_RECEIPTS.glob("T*.json")}:
                lines.append(
                    f"- Fill `judgments/{tid}.yaml` and set "
                    "`status: confirmed` + `confirm: true`.\n"
                )
                break
    lines.append(
        "- After each confirmation: `run_experiment.py --mode adaptive "
        "--resume`, then `metrics.py` + `report.py`.\n"
    )
    return "".join(lines)


def main() -> None:
    metrics_path = common.EXP / "metrics.json"
    if not metrics_path.is_file():
        raise SystemExit("metrics.json missing — run scripts/metrics.py first")
    metrics = common.load_json(metrics_path)
    out = common.EXP / "REPORT.md"
    out.write_text(render(metrics), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
