#!/usr/bin/env python3
"""OLD (proof pull) vs NEW (production projection) writing path comparison.

The same model, the same benchmark task material, the same editorial
capability (seeds + compiled corpus evidence) — the ONLY difference is the
path architecture:

  OLD — proof trajectory (examples/writing_case.py): six ACE tools, no
        context pack, acceptance requires material read + exemplar pull +
        knowledge retrieval + an integration probe. This is the trajectory
        that cost 21–22 model requests per article.

  NEW — production projection (examples/production_writing.py): the host
        assembles the WritingContext bundle once (material, source ledger,
        candidate techniques from compiled/sequential_inputs.jsonl, corpus
        evidence + curated human patches), projects it into request #1, and
        the agent has exactly save_artifact + retrieve_more_context.

Editorial control is ON in both modes with the same evidence store, so the
delta isolates the context-assembly architecture.

Output: results/compare/{task}_{mode}.json, plus a printed summary table.

--check verifies every input (ACE, tasks, compiled assets, model env) with
zero model calls. Real runs need ZUAEF_MODEL / provider env (same as
run_benchmark.py).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from pydantic_ai import Agent, UsageLimits
from pydantic_ai.messages import RetryPromptPart
from pydantic_ai_harness.step_persistence import FileStepStore, StepPersistence
from zuaef_ace_writing.editorial import (
    EditorialControlCapability,
    EditorialEvidenceStore,
    EditorialSettings,
    run_trajectory_sensors,
)
from zuaef_ace_writing.writing_toolset import (
    DEFAULT_ACE_ROOT,
    ace_prepare,
    build_writing_toolset,
)

from examples.production_writing import (
    final_artifact_text,
    metrics_from_messages,
    prepare_writing_context,
    render_writing_context,
)
from examples.writing_case import WRITING_AGENT_INSTRUCTIONS, build_prompt
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps, RunSummary
from zuaef_agent.providers import resolve_model

RESULTS = BENCH / "results" / "compare"
COMPILED_EVIDENCE = BENCH / "compiled" / "evidence.jsonl"
MOVE_RE = re.compile(r"\[editorial move \| (\w+) \| origin: (\w+)\]")
EVIDENCE_LINE_RE = re.compile(r"^evidence: (.+)$", re.MULTILINE)

OLD_REQUEST_LIMIT = 30  # recorded proof used 22; leave headroom, not a ceiling
NEW_REQUEST_LIMIT = 12  # production default; SLO alarm is at 8 requests


def load_full_task(task_id: str) -> dict:
    path = REPO / "data" / "derived" / "tasks_full" / f"{task_id}.json"
    if not path.is_file():
        raise SystemExit(
            f"{path} missing — run scripts/fetch_sources.py && scripts/build_tasks.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def material_file(task_id: str, full: dict) -> Path:
    directory = REPO / "data" / "derived" / "materials"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}.md"
    path.write_text(full["material"], encoding="utf-8")
    return path


def trace_from_messages(messages) -> dict:
    interventions: list[str] = []
    evidence_ids: list[str] = []
    vetoes = 0
    for message in messages:
        for part in getattr(message, "parts", []):
            content = getattr(part, "content", "")
            if isinstance(content, str):
                interventions.extend(MOVE_RE.findall(content))
                for line in EVIDENCE_LINE_RE.findall(content):
                    evidence_ids.extend(
                        e.strip() for e in line.split(",") if e.strip()
                    )
            if isinstance(part, RetryPromptPart) and "EDITORIAL SAVE VETO" in str(
                getattr(part, "content", "")
            ):
                vetoes += 1
    return {
        "interventions": interventions,
        "evidence_cited": sorted(set(evidence_ids)),
        "save_vetoes": vetoes,
    }


def _editorial_capability() -> EditorialControlCapability:
    return EditorialControlCapability(
        settings=EditorialSettings(), store=EditorialEvidenceStore(COMPILED_EVIDENCE)
    )


def reset_run(run_id: str, settings: AgentSettings) -> None:
    """Make a comparison run re-runnable: drop this run_id's step-store dirs,
    settlement receipts, and ACE workspace so budgets/receipts start empty."""
    import shutil

    for directory in (settings.step_store_dir,):
        if not directory.is_dir():
            continue
        for child in directory.glob(f"{run_id}*"):
            if child.is_dir() and (child.name == run_id or child.name.startswith(f"{run_id}-")):
                shutil.rmtree(child, ignore_errors=True)
    for root in (settings.receipt_dir, settings.state_root / "settlements"):
        for child in root.glob(f"{run_id}*") if root.is_dir() else []:
            if child.is_file():
                child.unlink()
    ace_workspace = DEFAULT_ACE_ROOT / "workspaces" / run_id
    if ace_workspace.is_dir():
        shutil.rmtree(ace_workspace)
    # stale run snapshots must not masquerade as this run's artifact
    artifact_dir = settings.workspace_root / "artifacts" / run_id
    if artifact_dir.is_dir():
        shutil.rmtree(artifact_dir, ignore_errors=True)


def build_old_agent(
    settings: AgentSettings, *, run_id: str
) -> Agent[CoreDeps, RunSummary]:
    """Proof trajectory composition (mirrors examples/writing_case.py) plus
    the same editorial capability both modes share."""
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.state_root.mkdir(parents=True, exist_ok=True)
    capabilities = [
        StepPersistence[CoreDeps](
            store=FileStepStore(
                settings.step_store_dir,
                max_snapshots_per_run=settings.max_snapshots_per_run,
            ),
            agent_name="zuaef",
            run_id=run_id,
        ),
        _editorial_capability(),
    ]
    return Agent(
        resolve_model(settings),
        deps_type=CoreDeps,
        output_type=[RunSummary],
        instructions=WRITING_AGENT_INSTRUCTIONS,
        capabilities=capabilities,
        toolsets=[build_writing_toolset(DEFAULT_ACE_ROOT)],
        name="zuaef",
    )


def build_new_agent(settings: AgentSettings, *, run_id: str):
    """Production projection composition (examples/production_writing.py)."""
    from examples.production_writing import build_production_agent

    return build_production_agent(settings, run_id=run_id)


async def run_old(task_id: str, settings: AgentSettings, run_id: str) -> dict:
    full = load_full_task(task_id)
    material = material_file(task_id, full)
    ace_prepare(
        run_id, title=task_id, materials=[str(material)], ace_root=DEFAULT_ACE_ROOT
    )
    agent = build_old_agent(settings, run_id=run_id)
    prompt = build_prompt(
        article_id=run_id,
        focus=[full.get("record_id", task_id)],
        account="",
    )
    return await _run_and_record(
        agent, prompt, settings, run_id, mode="old", task_id=task_id
    )


async def run_new(task_id: str, settings: AgentSettings, run_id: str) -> dict:
    full = load_full_task(task_id)
    material = material_file(task_id, full)
    ace_prepare(
        run_id, title=task_id, materials=[str(material)], ace_root=DEFAULT_ACE_ROOT
    )
    agent = build_new_agent(settings, run_id=run_id)
    bundle = prepare_writing_context(task_id=task_id, material=full["material"], title=task_id)
    prompt = (
        f"Write the article for task {task_id}.\n\n"
        + render_writing_context(bundle)
        + f"\n\nThe ACE article workspace id for this task is `{run_id}` — "
        "pass it as article_id to save_artifact.\n\n"
        "Write it now and save it via save_artifact."
    )
    return await _run_and_record(
        agent, prompt, settings, run_id, mode="new", task_id=task_id
    )


async def _run_and_record(
    agent, prompt: str, settings: AgentSettings, run_id: str, *, mode: str, task_id: str
) -> dict:
    """Run with the mode's usage limit; record the outcome honestly even when
    the limit is hit or the run raises (no fabricated artifacts)."""
    limit = OLD_REQUEST_LIMIT if mode == "old" else NEW_REQUEST_LIMIT
    try:
        result = await agent.run(
            prompt,
            deps=CoreDeps(workspace_root=settings.workspace_root, run_id=run_id),
            usage_limits=UsageLimits(request_limit=limit),
            retries=3,
        )
        text, path = final_artifact_text(settings.workspace_root, run_id)
        status = getattr(result.output, "status", str(result.output))
        outcome = getattr(result.output, "outcome", None)
        metrics = metrics_from_messages(result.all_messages())
        trace = trace_from_messages(result.all_messages())
    except Exception as exc:  # noqa: BLE001 — record the failure, never fake it
        text, path = final_artifact_text(settings.workspace_root, run_id)
        status = f"raised: {type(exc).__name__}"
        outcome = None
        metrics = {"model_requests": None, "tool_calls": None, "tool_names": []}
        trace = {"interventions": [], "evidence_cited": [], "save_vetoes": None}
        print(f"    [run failed: {type(exc).__name__}: {exc}]")
    return {
        "mode": mode,
        "task_id": task_id,
        "run_id": run_id,
        "request_limit": limit,
        "status": status,
        "outcome": outcome,
        "artifact_path": path,
        "artifact_exists": bool(text),
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
        "signals_on_artifact": run_trajectory_sensors(text) if text else {},
        **metrics,
        **trace,
    }


def check() -> None:
    problems: list[str] = []
    tasks = sorted((BENCH / "tasks").glob("T*.json"))
    if len(tasks) != 20:
        problems.append(f"tasks: {len(tasks)}/20")
    if not (REPO / "data" / "derived" / "tasks_full").is_dir():
        problems.append("data/derived/tasks_full missing (run build_tasks.py)")
    for asset, label in (
        (COMPILED_EVIDENCE, "compiled corpus evidence"),
        (BENCH / "compiled" / "techniques.jsonl", "compiled techniques"),
        (BENCH / "compiled" / "sequential_inputs.jsonl", "sequential inputs"),
        (BENCH / "evidence" / "human_patches.jsonl", "human patches"),
    ):
        if not asset.is_file():
            problems.append(f"{label} missing: {asset}")
    if not (DEFAULT_ACE_ROOT / "tools" / "ctx.py").is_file():
        problems.append(f"ACE_ROOT invalid: {DEFAULT_ACE_ROOT}")
    if "ZUAEF_MODEL" not in os.environ:
        problems.append("ZUAEF_MODEL not set (required for real runs, not for --check)")
    if problems:
        raise SystemExit("CHECK FAILED:\n  " + "\n  ".join(problems))
    print("  check passed (inputs ready for real runs)")


def run_comparison(tasks: list[str], mode: str) -> None:
    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    modes = ["old", "new"] if mode == "both" else [mode]
    for task_id in tasks:
        for m in modes:
            settings = settings.with_overrides(
                request_limit=OLD_REQUEST_LIMIT if m == "old" else NEW_REQUEST_LIMIT
            )
            run_id = f"cmp-{m}-{task_id}"
            reset_run(run_id, settings)
            record = asyncio.run(
                (run_old if m == "old" else run_new)(task_id, settings, run_id)
            )
            (RESULTS / f"{task_id}_{m}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            rows.append(record)
            print(
                f"  {m} {task_id}: requests={record['model_requests']} "
                f"tools={record['tool_calls']} vetoes={record['save_vetoes']} "
                f"interventions={len(record['interventions'])} artifact={'yes' if record['artifact_exists'] else 'NO'}"
            )
    if len(rows) == 2:
        a, b = rows
        delta = {
            "model_requests": {"old": a["model_requests"], "new": b["model_requests"]},
            "tool_calls": {"old": a["tool_calls"], "new": b["tool_calls"]},
            "tool_names_old": a["tool_names"],
            "tool_names_new": b["tool_names"],
            "save_vetoes": {"old": a["save_vetoes"], "new": b["save_vetoes"]},
            "interventions": {"old": len(a["interventions"]), "new": len(b["interventions"])},
            "evidence_cited": {"old": a["evidence_cited"], "new": b["evidence_cited"]},
            "artifact_sha256_match": a["artifact_sha256"] == b["artifact_sha256"],
        }
        (RESULTS / f"{rows[0]['task_id']}_summary.json").write_text(
            json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("\nSUMMARY (requests old -> new):")
        for key in ("model_requests", "tool_calls", "save_vetoes", "interventions"):
            print(f"  {key}: {delta[key]['old']} -> {delta[key]['new']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="T01", help="comma-separated task ids")
    ap.add_argument("--mode", choices=("old", "new", "both"), default="both")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        check()
        return
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    run_comparison(tasks, mode=args.mode)


if __name__ == "__main__":
    main()
