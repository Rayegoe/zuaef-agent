#!/usr/bin/env python3
"""OLD (proof pull) vs NEW (production projection) writing path comparison.

The same model, the same benchmark task material, the same editorial
capability (seeds + compiled corpus evidence) — the ONLY difference is the
path architecture:

  OLD — proof trajectory (examples/writing_case.py): six ACE tools, no
        context pack, acceptance requires material read + exemplar pull +
        knowledge retrieval + an integration probe. The trajectory that cost
        21–22 model requests per article.

  NEW — production projection (examples/production_writing.py): the host
        assembles the WritingContext bundle once and projects it into
        request #1; the agent has save_artifact only (escape hatch opt-in).
        For benchmark tasks the bundle's techniques/editorial memory come
        from the compiled sequential inputs exact join — that authority is
        benchmark-side ONLY (see note below).

  WRITER_EDITOR — NEW + a second editorial pass: the writer's saved draft is
        handed to an editor pass (same minimal surface) with the same
        techniques/editorial memory as instructions, which makes minimal
        targeted patches and saves the final version.

Seam rule (2026-08-17 review): BOTH paths run through the shared runtime
``execute_run`` — usage limits, exception boundary, receipt settlement and
host artifact verification are the runtime's, never re-implemented here.
Evidence comes from RunReceipt (status, usage.requests, verified tool
effects, verified artifacts), not from message sniffing.

Benchmark authority note: ``compiled/sequential_inputs.jsonl`` serves ONLY
this benchmark A/B. Production context assembly (examples/production_writing)
takes caller-provided techniques/memory/examples and never queries benchmark
assets.

Output: results/compare/{task}_{mode}_r{NN}.json per repeat + a summary json
with the requests list and p50. --check verifies every input with zero model
calls. Real runs need ZUAEF_MODEL / provider env (same as run_benchmark.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from host_projection_legacy import (
    COMPILED_EVIDENCE,
    prepare_writing_context,
    render_writing_context,
    run_production_article,
)
from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai_harness.step_persistence import FileStepStore, StepPersistence
from task_inputs import resolve_task_inputs
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
    reset_run_state,
)
from examples.writing_case import WRITING_AGENT_INSTRUCTIONS, build_prompt
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.providers import resolve_model
from zuaef_agent.runtime import PausedRun, execute_run

RESULTS = BENCH / "results" / "compare"
COMPILED_TECHNIQUES = BENCH / "compiled" / "techniques.jsonl"
COMPILED_SEQUENTIAL = BENCH / "compiled" / "sequential_inputs.jsonl"
HUMAN_PATCHES = BENCH / "evidence" / "human_patches.jsonl"
COMPILED_CORPUS = BENCH / "compiled" / "evidence.jsonl"

OLD_REQUEST_LIMIT = 30  # recorded proof used 22; headroom, not a ceiling
NEW_REQUEST_LIMIT = 12  # production default; SLO alarm is at 8 requests


def _json_default(obj):
    """Receipt usage payloads carry Decimal token counts; datetimes appear in
    tool-effect/artifact records. Keep records JSON-clean."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _dumps(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2, default=_json_default)


# --- benchmark-side selection (NOT production authority) ------------------------


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def candidate_technique_ids_for(task_id: str) -> list[str]:
    """Benchmark tasks: candidates from the compiled sequential inputs join."""
    for record in _load_jsonl(COMPILED_SEQUENTIAL):
        if record["task_id"] == task_id:
            return record["candidate_technique_ids"]
    return []


def benchmark_bundle_inputs(task_id: str) -> tuple[list[dict], list[dict]]:
    """(technique records, editorial memory records) for a benchmark task."""
    ids = candidate_technique_ids_for(task_id)
    techniques = [
        t
        for t in _load_jsonl(COMPILED_TECHNIQUES)
        if t["id"] in ids
    ]
    corpus = {e["id"]: e for e in _load_jsonl(COMPILED_CORPUS)}
    memory = [corpus[f"corpus.{tid}"] for tid in ids if f"corpus.{tid}" in corpus]
    return techniques, memory


# --- task data -------------------------------------------------------------------


def load_full_task(task_id: str) -> dict:
    path = REPO / "data" / "derived" / "tasks_full" / f"{task_id}.json"
    if not path.is_file():
        raise SystemExit(
            f"{path} missing — run scripts/fetch_sources.py && scripts/build_tasks.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def material_file(task_id: str, before_text: str) -> Path:
    """Write the REAL BEFORE body as the ingested material (never the
    assignment prompt — regression: T01's material field is a 144-char
    instruction, not the document)."""
    directory = REPO / "data" / "derived" / "materials"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{task_id}.md"
    path.write_text(before_text, encoding="utf-8")
    return path


# --- OLD: proof trajectory through the shared seam -------------------------------


def build_old_agent(
    settings: AgentSettings, *, run_id: str
) -> Agent[CoreDeps, str | DeferredToolRequests]:
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
        EditorialControlCapability(
            settings=EditorialSettings(),
            store=EditorialEvidenceStore(COMPILED_EVIDENCE),
        ),
    ]
    return Agent(
        resolve_model(settings),
        deps_type=CoreDeps,
        output_type=[str, DeferredToolRequests],
        instructions=WRITING_AGENT_INSTRUCTIONS,
        capabilities=capabilities,
        toolsets=[build_writing_toolset(DEFAULT_ACE_ROOT)],
        name="zuaef",
    )


def run_old(task_id: str, settings: AgentSettings, run_id: str) -> dict:
    full = load_full_task(task_id)
    inputs = resolve_task_inputs(full, task_id)
    material = material_file(task_id, inputs["before_text"])
    ace_prepare(
        run_id, title=task_id, materials=[str(material)], ace_root=DEFAULT_ACE_ROOT
    )
    agent = build_old_agent(settings, run_id=run_id)
    prompt = build_prompt(
        article_id=run_id,
        focus=[full.get("record_id") or task_id],
        account="",
    )
    # the assignment intent rides along even in the pull proof (it is task
    # context, not material); the BEFORE body stays ACE-side for read_material
    prompt += f"\nAssignment: {inputs['assignment']}"
    run_settings = settings.with_overrides(request_limit=OLD_REQUEST_LIMIT)
    reset_run_state(settings, run_id)
    outcome = execute_run(
        agent,
        CoreDeps(workspace_root=run_settings.workspace_root.resolve(), run_id=run_id),
        prompt=prompt,
        settings=run_settings,
        run_id=run_id,
        retries={"tools": 5},
    )
    return _record_from_outcome(outcome, run_id, task_id, mode="old", limit=OLD_REQUEST_LIMIT)


# --- NEW: production projection through the shared seam --------------------------


def run_new(task_id: str, settings: AgentSettings, run_id: str) -> dict:
    full = load_full_task(task_id)
    inputs = resolve_task_inputs(full, task_id)
    material = material_file(task_id, inputs["before_text"])
    techniques, memory = benchmark_bundle_inputs(task_id)
    record = run_production_article(
        settings,
        task_id=task_id,
        material_path=material,
        title=task_id,
        techniques=techniques,
        editorial_memory=memory,
        request_limit=NEW_REQUEST_LIMIT,
        run_id=run_id,
    )
    record["mode"] = "new"
    return record


# --- WRITER_EDITOR: two production passes ----------------------------------------


def run_writer_editor(task_id: str, settings: AgentSettings, base_run_id: str) -> dict:
    full = load_full_task(task_id)
    inputs = resolve_task_inputs(full, task_id)
    material = material_file(task_id, inputs["before_text"])
    techniques, memory = benchmark_bundle_inputs(task_id)
    writer_run = f"{base_run_id}-w"
    editor_run = f"{base_run_id}-e"

    writer = run_production_article(
        settings,
        task_id=task_id,
        material_path=material,
        title=task_id,
        techniques=techniques,
        editorial_memory=memory,
        request_limit=NEW_REQUEST_LIMIT,
        run_id=writer_run,
    )
    draft_text, _ = final_artifact_text(settings.workspace_root, writer_run)
    if not draft_text:
        return {
            "mode": "writer_editor",
            "task_id": task_id,
            "status": "failed",
            "detail": "writer pass produced no artifact",
            "writer": writer,
        }
    editor_prompt = (
        f"You are the editorial pass for task {task_id}.\n\n"
        f"Assignment: {inputs['assignment']}\n\n"
        "The writer produced this draft:\n\n"
        f"<writer-draft>\n{draft_text}\n</writer-draft>\n\n"
        "Apply minimal targeted editorial improvements only, guided by the "
        "techniques and editorial memory below. Preserve every fact, number, "
        "quote and claim; never rewrite the whole article. If the draft "
        "already meets the bar, save it as-is.\n\n"
        + render_writing_context(
            prepare_writing_context(
                task_id=task_id,
                material=inputs["before_text"],
                title=task_id,
                techniques=techniques,
                editorial_memory=memory,
            )
        )
        + f"\n\nThe ACE article workspace id for this pass is `{editor_run}` — "
        "pass it as article_id to save_artifact.\n\n"
        "Save the final version via save_artifact."
    )
    editor = run_production_article(
        settings,
        task_id=task_id,
        material_path=material,
        title=task_id,
        request_limit=NEW_REQUEST_LIMIT,
        run_id=editor_run,
        prompt=editor_prompt,
    )
    return {
        "mode": "writer_editor",
        "task_id": task_id,
        "status": editor.get("status"),
        "writer": writer,
        "editor": editor,
    }


# --- receipt-derived record -------------------------------------------------------


def _record_from_outcome(outcome, run_id: str, task_id: str, *, mode: str, limit: int) -> dict:
    if isinstance(outcome, PausedRun):
        return {
            "mode": mode,
            "task_id": task_id,
            "run_id": run_id,
            "request_limit": limit,
            "status": "paused",
            "pending_approvals": [c.tool_name for c in outcome.requests.approvals],
        }
    receipt = outcome.receipt
    return {
        "mode": mode,
        "task_id": task_id,
        "run_id": run_id,
        "request_limit": limit,
        "status": receipt.execution_state,
        "outcome": receipt.outcome,
        "model_requests": receipt.usage.get("requests"),
        "usage": receipt.usage,
        "verified_artifacts": [v.path for v in receipt.artifact_facts],
        "verified_tool_effects": [
            (v.tool_name, v.status) for v in receipt.tool_effect_facts
        ],
        "unresolved_effects": [
            (v.tool_name, v.status) for v in receipt.unresolved_effects
        ],
        "error": receipt.error,
    }


def _record_with_artifact(record: dict, workspace_root: Path) -> dict:
    """Attach artifact facts + sensors to a receipt-derived record."""
    text, path = final_artifact_text(workspace_root, record["run_id"])
    record["artifact_path"] = path
    record["artifact_exists"] = bool(text)
    record["artifact_chars"] = len(text)
    record["artifact_sha256"] = (
        hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
    )
    record["signals_on_artifact"] = run_trajectory_sensors(text) if text else {}
    return record


# --- driver -----------------------------------------------------------------------


def check() -> None:
    problems: list[str] = []
    tasks = sorted((BENCH / "tasks").glob("T*.json"))
    if len(tasks) != 20:
        problems.append(f"tasks: {len(tasks)}/20")
    if not (REPO / "data" / "derived" / "tasks_full").is_dir():
        problems.append("data/derived/tasks_full missing (run build_tasks.py)")
    for asset, label in (
        (COMPILED_EVIDENCE, "compiled corpus evidence"),
        (COMPILED_TECHNIQUES, "compiled techniques"),
        (COMPILED_SEQUENTIAL, "sequential inputs"),
        (HUMAN_PATCHES, "human patches"),
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


def run_comparison(tasks: list[str], mode: str, repeat: int) -> None:
    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    for task_id in tasks:
        runs: list[dict] = []
        for n in range(1, repeat + 1):
            suffix = f"r{n:02d}"
            if mode in ("old", "new", "both"):
                m = "old" if mode == "old" else "new"
                if mode == "both":
                    for m in ("old", "new"):
                        run_id = f"cmp-{m}-{task_id}"
                        record = _record_with_artifact(
                            run_old(task_id, settings, run_id) if m == "old"
                            else run_new(task_id, settings, run_id),
                            settings.workspace_root,
                        )
                        path = RESULTS / f"{task_id}_{m}_{suffix}.json"
                        path.write_text(
                            _dumps(record),
                            encoding="utf-8",
                        )
                        runs.append(record)
                        _print_record(record)
                else:
                    run_id = f"cmp-{m}-{task_id}"
                    record = _record_with_artifact(
                        run_old(task_id, settings, run_id) if m == "old"
                        else run_new(task_id, settings, run_id),
                        settings.workspace_root,
                    )
                    path = RESULTS / f"{task_id}_{m}_{suffix}.json"
                    path.write_text(
                        _dumps(record),
                        encoding="utf-8",
                    )
                    runs.append(record)
                    _print_record(record)
            elif mode == "writer_editor":
                base = f"cmp-we-{task_id}"
                record = run_writer_editor(task_id, settings, base)
                path = RESULTS / f"{task_id}_writer_editor_{suffix}.json"
                path.write_text(
                    _dumps(record),
                    encoding="utf-8",
                )
                runs.append(record)
                w = record.get("writer", {})
                e = record.get("editor", {})
                print(
                    f"  writer_editor {task_id} {suffix}: writer={w.get('status')} "
                    f"req={w.get('model_requests')} editor={e.get('status')} "
                    f"req={e.get('model_requests')} total={_total_requests(record)}"
                )
        _write_summary(task_id, mode, runs)


def _total_requests(record: dict) -> int | None:
    w = record.get("writer", {}).get("model_requests")
    e = record.get("editor", {}).get("model_requests")
    if w is None or e is None:
        return None
    return int(w) + int(e)


def _print_record(record: dict) -> None:
    print(
        f"  {record['mode']} {record['task_id']}: status={record['status']} "
        f"requests={record['model_requests']} tools={len(record['verified_tool_effects'])} "
        f"artifact={'yes' if record.get('artifact_exists') else 'NO'}"
    )


def _write_summary(task_id: str, mode: str, runs: list[dict]) -> None:
    requests = [
        r.get("model_requests")
        for r in runs
        if r.get("model_requests") is not None
    ] or [r.get("writer", {}).get("model_requests") for r in runs]
    if mode == "writer_editor":
        totals = [t for r in runs if (t := _total_requests(r)) is not None]
        summary = {
            "mode": mode,
            "task_id": task_id,
            "runs": len(runs),
            "writer_requests": [
                r.get("writer", {}).get("model_requests") for r in runs
            ],
            "editor_requests": [
                r.get("editor", {}).get("model_requests") for r in runs
            ],
            "total_requests": totals,
            "p50_total_requests": _p50(totals),
            "artifacts": [
                bool(r.get("editor", {}).get("artifact_exists")) for r in runs
            ],
        }
    else:
        summary = {
            "mode": mode,
            "task_id": task_id,
            "runs": len(runs),
            "requests": requests,
            "p50_requests": _p50(requests),
            "artifacts": [bool(r.get("artifact_exists")) for r in runs],
            "statuses": [r.get("status") for r in runs],
        }
    (RESULTS / f"{task_id}_{mode}_summary.json").write_text(
        _dumps(summary), encoding="utf-8"
    )


def _p50(values: list[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="T01", help="comma-separated task ids")
    ap.add_argument(
        "--mode",
        choices=("old", "new", "both", "writer_editor"),
        default="both",
        help="old=proof; new=production writer; both=old+new; "
        "writer_editor=production 2-pass",
    )
    ap.add_argument("--repeat", type=int, default=1, help="repeats per mode/task")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        check()
        return
    if args.repeat < 1:
        ap.error("--repeat must be >= 1")
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    run_comparison(tasks, mode=args.mode, repeat=args.repeat)


if __name__ == "__main__":
    main()
