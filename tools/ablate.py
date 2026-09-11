"""Minimal baseline-vs-candidate ablation runner (Method Kernel v0.1 T007).

Runs the SAME task through the SAME model and the default core composition
twice — baseline vs candidate — where the only difference is an instruction
block (with/without a Skill-like guidance, prompt line, or the Method Kernel
itself). Machine diagnostics come from the real run receipts via the shared
``execute_run`` seam; no evaluator, no scalar score, no automatic verdict.

    uv run python tools/ablate.py --case learning/comparisons/MK-ABLATION-1 \
        --candidate-append learning/comparisons/MK-ABLATION-1/kernel-block.txt

A case directory contains ``task.md`` (the exact task prompt; evidence is
carried inside the prompt so both sides see byte-identical input). Optional
``--baseline-append`` / ``--candidate-append`` point at instruction-block
files appended to ``CORE_INSTRUCTIONS`` for that side only — this is the
ablation axis (with/without a prompt line, skill text, or method block).

Outputs (under ``--out``, default the case dir):

    <out>/baseline/output.md    the baseline presentation text
    <out>/baseline/record.json  receipt-derived machine facts
    <out>/candidate/...         same for the candidate side
    <out>/diagnostics.json      both sides' machine facts + the honest note

Machine diagnostics are NEVER a quality verdict (same rule as the WCASE
comparisons): outcome quality, factual errors and which intervention is
smaller are judged by a human and/or the independent reviewer
(``tools/llm_reviewer.py``), not by this tool.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src")]

NOTE = "machine diagnostics only — never a quality verdict"


def load_task(case_dir: Path) -> str:
    task_path = case_dir / "task.md"
    if not task_path.is_file():
        raise SystemExit(f"case task missing: {task_path}")
    return task_path.read_text(encoding="utf-8")


def _side_instructions(append_path: Path | None) -> str:
    from zuaef_agent.core import CORE_INSTRUCTIONS

    if append_path is None:
        return CORE_INSTRUCTIONS
    return CORE_INSTRUCTIONS + "\n\n" + append_path.read_text(encoding="utf-8")


def run_side(
    task: str,
    *,
    side: str,
    append_path: Path | None,
    request_limit: int | None,
    run_id: str,
) -> dict[str, Any]:
    """One side through the shared execute_run seam in an isolated workspace.

    Uses the default core composition (no plugins, no business toolsets) so
    the ONLY difference between sides is the instruction block.
    """
    from zuaef_agent.config import AgentSettings
    from zuaef_agent.core import build_agent
    from zuaef_agent.models import CoreDeps
    from zuaef_agent.runtime import execute_run

    base_settings = AgentSettings.from_env()
    overrides: dict[str, Any] = {"request_limit": request_limit} if request_limit else {}
    with tempfile.TemporaryDirectory(prefix=f"zuaef-ablate-{side}-") as tmp:
        root = Path(tmp)
        settings = base_settings.with_overrides(
            workspace_root=root / "workspace",
            runtime_state_root=root / "state",
            **overrides,
        )
        settings.workspace_root.mkdir(parents=True, exist_ok=True)
        agent = build_agent(settings, run_id=run_id, instructions=_side_instructions(append_path))
        deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
        outcome = execute_run(
            agent, deps, prompt=task, settings=settings, run_id=run_id
        )

    record: dict[str, Any] = {"side": side, "run_id": run_id}
    if hasattr(outcome, "receipt"):  # TerminalRun
        receipt = outcome.receipt
        usage = receipt.usage or {}
        started = receipt.started_at
        finished = receipt.finished_at
        record.update(
            {
                "status": receipt.execution_state,
                "model_requests": usage.get("requests"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "tool_calls": len(receipt.tool_effect_facts),
                "tool_names": [fact.tool_name for fact in receipt.tool_effect_facts],
                "latency_ms": round(
                    (finished - started).total_seconds() * 1000, 3
                )
                if finished and started and finished >= started
                else None,
                "error": receipt.error,
                "paused": False,
            }
        )
        presentation = outcome.presentation
    else:  # PausedRun — bounded eval tasks should not hit approval gates
        record.update(
            {
                "status": "paused",
                "paused": True,
                "pending_approvals": [
                    call.tool_name for call in outcome.requests.approvals
                ],
            }
        )
        presentation = "<paused awaiting approval; no terminal output>"
    record["captured_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return {"record": record, "presentation": presentation}


def ablate(
    case_dir: Path,
    *,
    baseline_append: Path | None = None,
    candidate_append: Path | None = None,
    request_limit: int | None = None,
    out_dir: Path | None = None,
    run_side_fn: Callable[..., dict[str, Any]] = run_side,
) -> dict[str, Any]:
    """Run both sides and write the comparison packet; returns diagnostics."""
    from uuid import uuid4

    task = load_task(case_dir)
    out_dir = out_dir or case_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    sides: dict[str, dict[str, Any]] = {}
    for side, append in (
        ("baseline", baseline_append),
        ("candidate", candidate_append),
    ):
        result = run_side_fn(
            task,
            side=side,
            append_path=append,
            request_limit=request_limit,
            run_id=f"ablate-{case_dir.name}-{side}-{uuid4().hex[:8]}",
        )
        side_dir = out_dir / side
        side_dir.mkdir(parents=True, exist_ok=True)
        (side_dir / "output.md").write_text(
            result["presentation"] + "\n", encoding="utf-8"
        )
        (side_dir / "record.json").write_text(
            json.dumps(result["record"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        sides[side] = result["record"]

    diagnostics = {
        "case_id": case_dir.name,
        "axis": {
            "baseline_append": str(baseline_append) if baseline_append else None,
            "candidate_append": str(candidate_append) if candidate_append else None,
        },
        "order": ["baseline", "candidate"],  # fixed run order, recorded honestly
        "baseline": sides["baseline"],
        "candidate": sides["candidate"],
        "note": NOTE,
    }
    (out_dir / "diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True, type=Path, help="case directory with task.md")
    ap.add_argument("--baseline-append", type=Path, default=None)
    ap.add_argument("--candidate-append", type=Path, default=None)
    ap.add_argument("--request-limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    case_dir = args.case.resolve()
    if not case_dir.is_dir():
        raise SystemExit(f"case directory not found: {case_dir}")
    diagnostics = ablate(
        case_dir,
        baseline_append=args.baseline_append,
        candidate_append=args.candidate_append,
        request_limit=args.request_limit,
        out_dir=args.out.resolve() if args.out else None,
    )
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    print(f"\n{NOTE}. Judge quality with tools/llm_reviewer.py + human review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
