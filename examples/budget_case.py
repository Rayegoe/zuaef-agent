"""ZUAEF x EMTB budget: Stage 6A — second plugin generalization proof.

The question is not "can the agent produce a number" but:

    Can a business domain arrive as an installed ``zuaef.plugins`` entry point
    and run through the Plugin Composition Layer — resolve profile -> freeze
    CompositionSnapshot -> compose -> execute — with zero core changes, while
    the host owns artifact verification and receipt settlement?

``zuaef_emtb_budget.budget_lib`` is a faithful extraction of zesenticai's
finance_agent deterministic commands (bilingual CSV parsing + summary /
variance / consistency / health / query / significant-change). The plugin
factory wires one toolset; the profile ``emtb-budget`` enables it.

Two composition paths (both proven, both unchanged in core):

  --profile emtb-budget      plugin path: build_profile_agent resolves the
                             profile, freezes the CompositionSnapshot, and
                             threads it into the receipt (exact resume).
  (no --profile)             direct path: build_agent(extra_toolsets=[...])
                             using the SAME plugin toolset — proof evidence
                             from example2, kept as parity baseline.

Acceptance is the harness contract, not the analysis's business verdict:
  - run completed with a terminal receipt on disk
  - save_budget_report artifact verified by the host (SHA-256 ownership)
  - parse_budget_csv and save_budget_report settled as completed tool effects
  - with --profile: receipt.composition present, plugins include
    zuaef-emtb-budget, composition_id non-empty
  - host-side deterministic expectations over the same CSV are printed for
    cross-check (counts / inconsistency / significant changes / health state)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zuaef_emtb_budget.toolset import build_budget_toolset

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import PausedRun, TerminalRun, execute_run

BUDGET_AGENT_INSTRUCTIONS = """\
You are the ZUAEF EMTB budget analysis agent for one CSV input.

Available tools: parse_budget_csv, budget_summary, budget_variance,
budget_consistency, budget_health, budget_query, significant_changes,
save_budget_report. No generic file/knowledge/planning tools exist in this run.

You own the trajectory: decide which analyses answer the business question
(parse → analyze → report). Policy constraints are fixed:
1. Parse the CSV FIRST with parse_budget_csv; every analysis takes the parsed
   points array. Never hand-compute amounts — the library is deterministic.
2. Run at least TWO different analyses; prefer budget_health plus whichever
   secondary analysis the business question calls for.
3. Produce a Markdown report (Chinese is fine) that states the health state,
   the key numbers, the inconsistencies found, and the significant changes.
   Separate facts computed by the library from any interpretation you add.
4. Save exactly once with save_budget_report(report_markdown, csv_name).
5. RunSummary.artifacts must declare the snapshot_rel_path returned by
   save_budget_report (as artifact:<rel_path>). In RunSummary.evidence put
   ONLY artifact:<rel_path> refs — never write tool-effect: refs; the host
   settles completed tool effects automatically.
6. If the CSV cannot be parsed or an analysis raises, end partial/blocked and
   name the unknown instead of guessing.
"""


def _print_checks(title: str, checks: list[tuple[str, bool, str]]) -> bool:
    print(title)
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    return ok


def host_expectations(csv_path: Path) -> dict:
    """Deterministic expectations computed by the host directly over the CSV.

    These do NOT depend on the model — they are the cross-check the operator
    can verify against the agent's report.
    """
    from zuaef_emtb_budget.budget_lib import (
        budget_health_check,
        detect_significant_changes,
        parse_emtb_budget_csv,
        validate_budget_consistency,
    )
    from zuaef_emtb_budget.budget_lib.models import (
        BudgetConsistencyInput,
        BudgetHealthGoal,
        SignificantChangeDetectionInput,
    )

    text = csv_path.read_text(encoding="utf-8")
    points, missing = parse_emtb_budget_csv(text)
    consistency = validate_budget_consistency(BudgetConsistencyInput(budget_data=points))
    significant = detect_significant_changes(
        SignificantChangeDetectionInput(budget_data=points)
    )
    health = budget_health_check(BudgetHealthGoal(budget_data=points))
    inconsistent = [
        i.line_item for i in consistency.items
        if i.consistency_flag.value == "INCONSISTENT"
    ]
    return {
        "rows": len(points),
        "missing_required_columns": missing,
        "inconsistent_items": inconsistent,
        "significant_increases": len(significant.significant_increases),
        "significant_decreases": len(significant.significant_decreases),
        "overall_health": health.overall_health_state.value,
    }


def main() -> int:
    default_csv = (
        Path(__file__).resolve().parent.parent
        / "plugins"
        / "zuaef-emtb-budget"
        / "zuaef_emtb_budget"
        / "data"
        / "emtb_budget_sample.csv"
    )
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(default_csv),
                    help="path to an EMTB budget CSV (Chinese or English headers)")
    ap.add_argument(
        "--profile",
        default=None,
        help="compose the agent via a ZUAEF profile (plugin path) instead of "
        "the direct toolset assembly; the frozen snapshot lands in the receipt",
    )
    ap.add_argument(
        "--config-root",
        type=Path,
        default=PROJECT_ROOT,
        help="config root whose profiles/ holds <profile>.toml "
        "(default: this repository, where profiles/emtb-budget.toml lives)",
    )
    ap.add_argument(
        "--question",
        default="分析这份 EMTB 预算：总体健康度如何？哪些科目预算生命周期不一致？哪些科目变动显著需要关注？",
    )
    args = ap.parse_args()

    settings = AgentSettings.from_env()
    has_credentials = bool(
        settings.openai_base_url and settings.openai_api_key
    ) or bool(os.getenv("OPENAI_API_KEY"))
    if not has_credentials:
        print(
            "RESULT: FAIL — no real model credentials (ZUAEF_OPENAI_* / LLM_* / OPENAI_API_KEY)"
        )
        return 2

    csv_path = Path(args.csv).resolve()
    if not csv_path.is_file():
        print(f"RESULT: FAIL — csv not found: {csv_path}")
        return 2

    expected = host_expectations(csv_path)
    print(
        f"Host expectations over {csv_path.name}: rows={expected['rows']} "
        f"missing={expected['missing_required_columns']} "
        f"inconsistent={expected['inconsistent_items']} "
        f"sig+={expected['significant_increases']} sig-={expected['significant_decreases']} "
        f"health={expected['overall_health']}"
    )

    run_id = uuid4().hex
    composition = None
    if args.profile:
        # Plugin Composition Layer path: resolve -> freeze -> compose. The
        # snapshot threads into the receipt; resume stays exact.
        agent, composition = build_profile_agent(
            settings,
            run_id=run_id,
            profile=args.profile,
            config_root=args.config_root,
        )
    else:
        # Direct-toolset path (example2 proof evidence, same plugin toolset).
        agent = build_agent(
            settings,
            run_id=run_id,
            extra_toolsets=[build_budget_toolset()],
        )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    prompt = (
        f"任务：分析以下 EMTB 预算 CSV。\n"
        f"业务问题：{args.question}\n"
        f"CSV 内容：\n```csv\n{csv_path.read_text(encoding='utf-8')}\n```\n"
        "验收：必须先用 parse_budget_csv 解析；至少两种分析；"
        "最终 save_budget_report 一次并保存报告；"
        "RunSummary.artifacts 声明返回的 snapshot_rel_path；"
        "RunSummary.evidence 只写 artifact:<相对路径>，绝不写 tool-effect 引用。"
    )

    outcome = execute_run(
        agent,
        deps,
        prompt=prompt,
        settings=settings,
        run_id=run_id,
        retries={"tools": 5},
        composition=composition,
    )

    if isinstance(outcome, PausedRun):
        print(
            f"RESULT: paused — approvals pending {[c.tool_name for c in outcome.requests.approvals]}"
        )
        print(f"pause receipt: {outcome.pause_receipt.run_id}")
        return 4

    assert isinstance(outcome, TerminalRun)
    receipt = outcome.receipt

    effect_names = [e.tool_name for e in receipt.verified_tool_effects]
    parsed_ok = "parse_budget_csv" in effect_names
    saved_ok = "save_budget_report" in effect_names

    artifact_paths = [v.path for v in receipt.verified_artifacts]
    report_artifacts = [p for p in artifact_paths if p.endswith("-report.md")]

    snapshot_ok = False
    snapshot_detail = "composition=None (direct path)"
    if composition is not None:
        comp = receipt.composition
        snapshot_ok = bool(
            comp is not None
            and comp.composition_id
            and any(p.id == "zuaef-emtb-budget" for p in comp.plugins)
        )
        snapshot_detail = (
            f"composition_id={comp.composition_id[:12]}… "
            f"plugins={[p.id for p in comp.plugins]}"
        )

    machine_checks = [
        (
            "ZUAEF autonomous execution completed",
            receipt.status == "completed",
            f"receipt status={receipt.status}",
        ),
        (
            "parse_budget_csv settled as completed effect",
            parsed_ok,
            f"effects={sorted(set(effect_names))}",
        ),
        (
            "save_budget_report settled as completed effect",
            saved_ok,
            f"effects={sorted(set(effect_names))}",
        ),
        (
            "host verified run artifact",
            bool(report_artifacts),
            f"verified={artifact_paths}",
        ),
        (
            "RunSummary declared the saved artifact",
            any(
                a == f"artifacts/{run_id}/emtb_budget-report.md"
                for a in outcome.summary.artifacts
            ),
            f"summary.artifacts={outcome.summary.artifacts}",
        ),
        (
            "CompositionSnapshot present in receipt",
            snapshot_ok,
            snapshot_detail,
        ),
        (
            "ZUAEF receipt on disk",
            bool(outcome.summary.receipt) and Path(outcome.summary.receipt).is_file(),
            outcome.summary.receipt,
        ),
        (
            "usage recorded",
            bool(receipt.usage),
            str(receipt.usage.get("requests", "?")) + " requests",
        ),
    ]
    checks_ok = _print_checks("\n=== EMTB Budget Slice (harness contract) ===", machine_checks)
    test_complete = receipt.status == "completed" and checks_ok

    print("\n=== Host expectations vs agent report ===")
    print(f"  host: {expected}")
    report_text = ""
    for p in report_artifacts:
        rp = settings.workspace_root.resolve() / p
        if rp.is_file():
            report_text = rp.read_text(encoding="utf-8")[:4000]
            break
    if report_text:
        print("  agent report (first 4000 chars):")
        for line in report_text.splitlines()[:60]:
            print(f"    {line}")
    else:
        print("  (no report artifact readable)")

    print(f"\nRESULT: {'PASS' if test_complete else 'FAIL'} (run {run_id})")
    print("EVIDENCE:")
    print(f"  receipt    {outcome.summary.receipt}")
    print(f"  artifacts  {report_artifacts}")
    print(f"  csv        {csv_path}")
    print(f"  composition {snapshot_detail}")
    print(f"  unknown    {receipt.summary.unknowns or 'none'}")

    if test_complete:
        return 0
    if receipt.status == "blocked":
        return 1
    return 3


if __name__ == "__main__":
    sys.exit(main())
