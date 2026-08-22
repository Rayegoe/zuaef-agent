#!/usr/bin/env python3
"""Run the editorial-learning benchmark in three modes (Gate E A/B/C).

  base     editorial_control OFF          — what the model does alone
  static   editorial_control ON, seeds + compiled corpus evidence only,
           learning disabled
  adaptive editorial_control ON, seeds + compiled corpus evidence + human
           patches promoted sequentially: run task N with everything promoted
           so far, then promote task N's patches BEFORE task N+1.
           Agent@T01 != Agent@T20 with zero weight changes.

Honest naming (per 2026-08-17 review): the promoted patches come from the
pre-built dataset pool (evidence/human_patches.jsonl, IteraTeR-derived), so
adaptive proves SEQUENTIAL EVIDENCE EXPOSURE — not experiential learning.
Experiential learning (operator-owned judgments on this run's own drafts)
is the experiments/sequential-v1 experiment's contract, not this runner's.

Each task run writes results/<mode>/T##_run.json with the full machine-side
trace. Sensors run on the REAL saved article (the run snapshot
workspace/artifacts/<run_id>/final.md), never on the RunSummary text. Blind
human judgment fields are left null — machines do not grade taste.

The agent is composed through the same seams the Plugin Composition Layer
used (core.build_agent + legacy writing toolset + EditorialControlCapability),
without requiring installed entry points. ACE workspace prep per task
(material ingested via ace_prepare) and the model come from the environment:
  ZUAEF_MODEL / provider env vars   — model (see zuaef_agent.providers)
  ACE_ROOT                          — article-context-engine checkout

--check verifies everything except the model call and exits 0.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
sys.path[:0] = [
    str(Path(__file__).resolve().parents[1] / "legacy"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
from editorial_capability import (
    EditorialControlCapability,
    EditorialEvidenceStore,
    EditorialSettings,
    run_trajectory_sensors,
)
from task_inputs import resolve_task_inputs

from examples.writing_toolset import (
    DEFAULT_ACE_ROOT,
    ace_prepare,
    build_writing_toolset,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps

RESULTS = BENCH / "results"
COMPILED_EVIDENCE = BENCH / "compiled" / "evidence.jsonl"
EVIDENCE_RUN = RESULTS / "adaptive" / "evidence_running.jsonl"
# adaptive store = compiled corpus + promoted patches, merged per task
EVIDENCE_RUN_FULL = RESULTS / "adaptive" / "evidence_running_full.jsonl"
MOVE_RE = re.compile(r"\[editorial move \| (\w+) \| origin: (\w+)\]")
EVIDENCE_LINE_RE = re.compile(r"^evidence: (.+)$", re.MULTILINE)


def load_full_task(task_id: str) -> dict:
    path = REPO / "data" / "derived" / "tasks_full" / f"{task_id}.json"
    if not path.is_file():
        raise SystemExit(
            f"{path} missing — run scripts/fetch_sources.py && scripts/build_tasks.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def merged_evidence_file(mode: str) -> Path | None:
    """Evidence file per mode.

    static:   seeds + compiled corpus (compiled/evidence.jsonl)
    adaptive: seeds + compiled corpus + promoted human patches — the runner
              merges corpus + the running promotion file per task so the
              EditorialEvidenceStore gets ONE extra path (no runtime change).
    base:     no capability, no file.
    """
    if mode == "base":
        return None
    if mode == "static":
        return COMPILED_EVIDENCE
    lines: list[str] = []
    for path in (COMPILED_EVIDENCE, EVIDENCE_RUN):
        if path.is_file():
            lines.extend(
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    EVIDENCE_RUN_FULL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return EVIDENCE_RUN_FULL


def compose(mode: str, settings: AgentSettings, run_id: str):
    """Agent per mode: same toolset always; capability only when ON."""
    toolset = build_writing_toolset(DEFAULT_ACE_ROOT)
    capabilities = []
    evidence_file = merged_evidence_file(mode)
    if evidence_file is not None:
        capabilities.append(
            EditorialControlCapability(
                settings=EditorialSettings(),
                store=EditorialEvidenceStore(evidence_file),
            )
        )
    return build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=[toolset],
        extra_capabilities=capabilities,
    )


def trace_from_messages(messages) -> dict:
    """Recover the editorial trace from real run history (no new hooks needed)."""
    interventions: list[str] = []
    evidence_ids: list[str] = []
    vetoes = 0
    from pydantic_ai.messages import RetryPromptPart

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


async def run_task(mode: str, task: dict, settings: AgentSettings, run_id: str) -> dict:
    full = load_full_task(task["task_id"])
    inputs = resolve_task_inputs(full, task["task_id"])
    # ACE workspace per task: ingest the REAL BEFORE body so save_artifact has
    # a ledger and read_material returns the document, not the assignment.
    ace_prepare(
        run_id,
        title=task["task_id"],
        materials=[str(_material_file(task["task_id"], inputs["before_text"]))],
        ace_root=DEFAULT_ACE_ROOT,
    )
    agent = compose(mode, settings, run_id)
    deps = CoreDeps(workspace_root=settings.workspace_root, run_id=run_id)
    result = await agent.run(
        inputs["assignment"]
        + "\n\n### BEFORE document\n\n"
        + inputs["before_text"]
        + "\n\nWrite the revised article now and save it via save_artifact.",
        deps=deps,
        retries=3,
    )
    # Sensors run on the REAL saved article (the run snapshot final.md), not
    # on result.output — output is a RunSummary, never the article text.
    snapshot = Path(settings.workspace_root) / "artifacts" / run_id / "final.md"
    final_text = (
        snapshot.read_text(encoding="utf-8") if snapshot.is_file() else ""
    )
    trace = trace_from_messages(result.all_messages())
    return {
        "task_id": task["task_id"],
        "mode": mode,
        "signals_on_artifact": run_trajectory_sensors(final_text),
        "artifact_path": str(snapshot),
        "artifact_exists": snapshot.is_file(),
        "artifact_chars": len(final_text),
        **trace,
    }


def _material_file(task_id: str, before_text: str) -> Path:
    """Write the REAL BEFORE body as the ingested material (never the
    assignment prompt — regression: T01's material field is a 144-char
    instruction, not the document)."""
    directory = REPO / "data" / "derived" / "materials"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}.md"
    path.write_text(before_text, encoding="utf-8")
    return path


def check() -> None:
    problems = []
    tasks = sorted((BENCH / "tasks").glob("T*.json"))
    if len(tasks) != 20:
        problems.append(f"tasks: {len(tasks)}/20")
    if not (REPO / "data" / "derived" / "tasks_full").is_dir():
        problems.append("data/derived/tasks_full missing (run build_tasks.py)")
    store = EditorialEvidenceStore(BENCH / "evidence" / "human_patches.jsonl")
    human = [e for e in store._entries if e.source_type == "human_patch"]
    print(f"  tasks: {len(tasks)} | human patches: {len(human)} | store loads clean")
    seed_file = BENCH / "evidence" / "seed_snapshot.jsonl"
    if not seed_file.is_file():
        problems.append("seed_snapshot.jsonl missing")
    if not COMPILED_EVIDENCE.is_file():
        problems.append("compiled/evidence.jsonl missing (run compile_learning_pack.py)")
    if not (DEFAULT_ACE_ROOT / "tools" / "ctx.py").is_file():
        problems.append(f"ACE_ROOT invalid: {DEFAULT_ACE_ROOT}")
    else:
        print(f"  ACE root ok: {DEFAULT_ACE_ROOT}")
    model_env = "ZUAEF_MODEL" in __import__("os").environ
    print(f"  model env (ZUAEF_MODEL): {'set' if model_env else 'NOT set (required for real runs, not for --check)'}")
    if problems:
        raise SystemExit("CHECK FAILED:\n  " + "\n  ".join(problems))
    print("  check passed")


def run_mode(mode: str, limit: int | None) -> None:
    """Sync driver: one asyncio.run per task so inter-task promotion stays sync.

    Each task composes a fresh agent (run_task), so per-task event loops carry
    no shared async state.
    """
    from zuaef_agent.providers import resolve_model  # noqa: F401  (env sanity)

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    out_dir = RESULTS / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode == "adaptive":
        EVIDENCE_RUN.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE_RUN.write_text("", encoding="utf-8")  # seeds only to start
    bench = [
        json.loads(line)
        for line in (BENCH / "benchmark.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if limit:
        bench = bench[:limit]
    import subprocess

    for task in bench:
        tid = task["task_id"]
        record = asyncio.run(run_task(mode, task, settings, run_id=f"{mode}-{tid}"))
        (out_dir / f"{tid}_run.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  {mode} {tid}: interventions={len(record['interventions'])} "
              f"vetoes={record['save_vetoes']} evidence={len(record['evidence_cited'])} "
              f"artifact={'yes' if record['artifact_exists'] else 'NO'} "
              f"signals={len(record['signals_on_artifact'])}")
        if mode == "adaptive":
            # Sequential evidence exposure (dataset-derived patches; not
            # experiential learning — see module docstring): promote THIS
            # task's patches before the next one.
            subprocess.run(
                [sys.executable, str(BENCH / "scripts" / "promote_patch.py"),
                 "--task", tid, "--out", str(EVIDENCE_RUN)],
                check=True,
            )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("base", "static", "adaptive"))
    ap.add_argument("--limit", type=int, help="run only first N tasks (smoke)")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if not args.mode:
        ap.error("--mode or --check required")
    run_mode(args.mode, args.limit)


if __name__ == "__main__":
    main()
