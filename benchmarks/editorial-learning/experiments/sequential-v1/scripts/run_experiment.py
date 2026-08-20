"""ZUAEF Editorial Sequential Learning Experiment — orchestrator (v1).

Modes (same model, same Writing Agent, same tasks — only evidence visibility
and the capability differ):

    base     capability OFF
    static   capability ON:  EditorialEvidenceStore(compiled corpus)  → seeds+corpus
    adaptive capability ON:  EditorialEvidenceStore(runtime evidence) → seeds+corpus
                               + ONLY confirmed-promoted T01..T(n-1) human patches

Adaptive is a strict sequential loop with an operator gate:

    run Tn  →  write runs/adaptive/Tn_run.json  →  write judgments/Tn.yaml template
    →  STOP until the operator confirms the judgment
    →  derive_patches (candidate formation, separate step)
    →  promote: move candidates into promotions/receipts/Tn.json, rebuild
       runtime-evidence.jsonl, backfill the run receipt, run T(n+1) …

`--stub` swaps the model for a deterministic stub so the MACHINERY (gates,
loop, receipts, derive, metrics) is exercised with zero API cost. Stub
receipts carry `model: "stub"` and are never promotion-inputs (judgments are
still operator-confirmed).

Anti-fabrication: the judgment template is written with every operator field
`null`; there is no code path in this repository that fills them.
"""

# pyright: reportMissingImports=false
# (deliberate sys.path-bootstrapped seam imports)

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[3] / "legacy")]

import common
from common import (
    finalize_run_receipt,
    new_run_receipt,
    rebuild_runtime_evidence,
    trace_from_messages,
)

EXP = common.EXP
REPO = common.REPO
TASK_IDS = common.TASK_IDS


def utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def REPO_rel(path: Path) -> str:
    return os.path.relpath(path, REPO)


# --- judgment template (operator-owned fields are null) -------------------------


def judgment_template(task_id: str, run_path: Path, mode: str) -> Path:
    path = common.JUDGMENTS / f"{task_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return path  # do not overwrite operator edits
    run_rel = os.path.relpath(run_path, EXP)
    common.write_yaml_like(
        path,
        [
            "# Sequential-v1 judgment record — operator-owned, machine-written template.\n",
            "# Fill the null fields below for the run whose receipt is listed, then set\n",
            "#   status: confirmed   and   confirm: true\n",
            "# to allow derive_patches + promotion. preference compares base/static/\n",
            "# adaptive outputs of the same task (blind: judge the drafts, not the modes).\n",
            "schema_version: '1.0'\n",
            f"task_id: {task_id}\n",
            f"mode: {mode}\n",
            f"run_receipt: {run_rel}\n",
            "judge: null  # human | reference\n",
            "# --- blind preference over the three drafts of this task ---\n",
            "preferred: null  # base | static | adaptive | tie\n",
            "preference_note: ''\n",
            "# --- intervention usefulness (one entry per intervention serial) ---\n",
            "interventions_useful: []  # e.g. [true, false, true]\n",
            "# --- operator revision of THIS task's draft (minimal patch) ---\n",
            "patch_before: ''\n",
            "patch_after: ''\n",
            "human_edit_proportion: null  # 0..1 (= edited chars / draft length)\n",
            "claim_preserved: null  # true | false\n",
            "full_rewrite: null  # true | false — was the revision a full rewrite?\n",
            "# --- candidate patch mapping (consistency-checked by derive_patches) ---\n",
            "action: ''  # one of: return_to_observation | delay_interpretation |\n",
            "            # shift_perspective | retrieve_concrete_memory | break_trajectory\n",
            "trigger_signals: ''  # comma-separated subset of the five frozen sensors\n",
            "situation_tags: drafting,nonfiction\n",
            "directive: ''\n",
            "rationale: ''\n",
            "confirm: false\n",
        ],
    )
    return path


# --- model / stub runner ---------------------------------------------------------


class StubModel:
    """Deterministic stand-in: fixed draft + canned signal-agnostic text."""

    name = "stub"

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id

    def prompt_text(self) -> str:
        return (
            f"# {self.task_id} stub draft\n"
            "This is a deterministic stub paragraph for machinery validation. "
            "Several companies just looked the vision of WiMAX but ignore its "
            "threats; the draft repeats connector phrases and abstract nouns on "
            "purpose so the editorial sensors stay exercised.\n"
            f"[stub: {self.task_id}]"
        )


async def run_task_stub(task_id: str, mode: str) -> tuple[dict, str]:
    draft = StubModel(task_id).prompt_text()
    trace = {"interventions": [], "evidence_cited": [], "save_vetoes": 0}
    return trace, draft


async def run_task_real(task_id: str, mode: str) -> tuple[dict, str]:
    """Real agent run through the production composition seams.

    Same build_agent + writing toolset + capability hooks as run_benchmark.py,
    with the experiment's evidence seam. The sandbox FileSystem capability is
    disabled (enable_filesystem=False) because the model must route all file
    writes through save_artifact inside the ACE workspace, and planning/skills
    are off for the same reason run_benchmark disables them.
    """
    from editorial_capability import (
        EditorialControlCapability,
        EditorialEvidenceStore,
        EditorialSettings,
    )
    from zuaef_ace_writing.writing_toolset import (
        DEFAULT_ACE_ROOT,
        ace_prepare,
        build_writing_toolset,
    )

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.core import build_agent
    from zuaef_agent.models import CoreDeps

    base_settings = AgentSettings.from_env()

    def _env_int(name: str, default: int) -> int:
        try:
            return int(os.environ.get(name, str(default)))
        except ValueError:
            print(f"  warn: bad {name}={os.environ.get(name)!r}; using {default}")
            return default

    settings = dataclasses.replace(
        base_settings,
        # experiment runs pull materials/exemplars/claim-checks heavily; default
        # budgets (12 requests / 40 tool calls) are too tight for a full article
        # write + save cycle. Override via ZUAEF_EXPERIMENT_REQUEST_LIMIT.
        request_limit=_env_int("ZUAEF_EXPERIMENT_REQUEST_LIMIT", 200),
        tool_calls_limit=_env_int("ZUAEF_EXPERIMENT_TOOL_CALLS_LIMIT", 200),
        enable_planning=False,
        enable_skills=False,
        enable_filesystem=False,
    )

    full = common.full_task(task_id)
    # Benchmark input seam: material=assignment, before=real body. The model
    # must receive the BEFORE document as material and the assignment as
    # intent — never the assignment alone (regression: T01's material field
    # is a 144-char instruction, not the document).
    sys.path.append(str(common.BENCH / "scripts"))
    from task_inputs import resolve_task_inputs

    inputs = resolve_task_inputs(full, task_id)
    run_id = f"sqv1-{mode}-{task_id}-{datetime.now(UTC).strftime('%H%M%S%f')}"
    material = (
        inputs["assignment"]
        + "\n\n### BEFORE document\n\n"
        + inputs["before_text"]
        + "\n\nWrite the revised article now and save it via save_artifact."
        + "\nThe article workspace id is "
        + run_id
        + " — use it as article_id "
        "for the context-engine tools (list_materials, read_material, "
        "retrieve_exemplars, check_claim). Do not create files outside the "
        "article workspace."
    )
    material_path = REPO / "data" / "derived" / "materials" / f"{task_id}.md"
    material_path.parent.mkdir(parents=True, exist_ok=True)
    material_path.write_text(inputs["before_text"], encoding="utf-8")
    ace_prepare(
        run_id,
        title=task_id,
        materials=[str(material_path)],
        ace_root=DEFAULT_ACE_ROOT,
    )

    if mode == "base":
        store = None
    elif mode in ("static", "adaptive"):
        rebuild_runtime_evidence()
        evidence_path = (
            common.RUNTIME_EVIDENCE if mode == "adaptive" else common.COMPILED_EVIDENCE
        )
        store = EditorialEvidenceStore(evidence_path)
    else:
        raise SystemExit(f"unknown mode {mode}")

    toolset = build_writing_toolset(DEFAULT_ACE_ROOT)
    capabilities = []
    if store is not None:
        capabilities.append(
            EditorialControlCapability(settings=EditorialSettings(), store=store)
        )
    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=[toolset],
        extra_capabilities=capabilities,
    )
    deps = CoreDeps(workspace_root=settings.workspace_root, run_id=run_id)
    from pydantic_ai.usage import UsageLimits

    result = await agent.run(
        material,
        deps=deps,
        usage_limits=UsageLimits(
            request_limit=settings.request_limit,
            tool_calls_limit=settings.tool_calls_limit,
            total_tokens_limit=settings.total_tokens_limit,
        ),
    )
    draft = result.output
    trace = trace_from_messages(result.all_messages())
    return trace, draft if isinstance(draft, str) else str(draft)


# --- gating logic (pure, unit-tested) -------------------------------------------


def _task_seq(task_id: str) -> int:
    try:
        return int(task_id[1:])
    except ValueError:
        raise SystemExit(f"bad task id {task_id!r}") from None


def expected_adaptive_promotions(up_to_task: str) -> list[str]:
    """Task ids whose promotions must ALREADY exist for a clean adaptive Tn run."""
    idx = TASK_IDS.index(up_to_task)
    return TASK_IDS[:idx]


def check_adaptive_leak(task_id: str) -> list[str]:
    """Return violations of the required promotion prefix, else [].

    For adaptive Tn the promoted set must be EXACTLY the tasks before n:
    a future promotion or a gap (earlier task missing) both break the strict
    sequential-learning contract and are reported.
    """
    idx = TASK_IDS.index(task_id)
    legal = set(TASK_IDS[:idx])
    promoted = {r.stem for r in common.PROMO_RECEIPTS.glob("T*.json")}
    return sorted(legal ^ promoted)


def judgment_confirmations(task_id: str) -> bool:
    path = common.JUDGMENTS / f"{task_id}.yaml"
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("confirm:"):
            return line.strip().endswith("true")
    return False


def _load_judgment_parsers():
    from derive_patches import (
        derive,
        parse_judgment,
    )

    return derive, parse_judgment


# --- one task ---------------------------------------------------------------------


def run_one(task_id: str, mode: str, *, stub: bool) -> Path:
    seq = _task_seq(task_id)
    if mode == "adaptive":
        illegal = check_adaptive_leak(task_id)
        if illegal:
            raise SystemExit(
                f"leak guard: promotions exist for tasks not before {task_id}: "
                f"{illegal} — refusing to run adaptive {task_id}"
            )
    receipt = new_run_receipt(
        task_id=task_id,
        mode=mode,
        evidence_snapshot=common.available_evidence_snapshot(seq)
        if mode == "adaptive"
        else None,
    )
    started = utcnow()
    if stub:
        trace, draft = asyncio.run(run_task_stub(task_id, mode))
        model = "stub"
    else:
        trace, draft = asyncio.run(run_task_real(task_id, mode))
        model = "real"
    from editorial_capability import run_trajectory_sensors

    signals = run_trajectory_sensors(draft) if mode != "base" else {}
    finished = utcnow()
    finalize_run_receipt(
        receipt,
        trace=trace,
        signals=signals,
        draft=draft,
        draft_sha256=common.sha256_text(draft),
        model=model,
        started_at=started,
        finished_at=finished,
        run_id=f"sqv1-{mode}-{task_id}",
    )
    out = common.RUNS / mode / f"{task_id}_run.json"
    common.write_json(out, receipt)
    # stable textual draft: runs/<mode>/T##_draft.json (sha256 in the receipt)
    common.write_json(
        common.RUNS / mode / f"{task_id}_draft.json",
        {"task_id": task_id, "mode": mode, "draft": draft},
    )
    print(
        f"  [{mode}] {task_id}: interventions={receipt['intervention']['count']} "
        f"vetoes={receipt['save']['veto_count']} "
        f"evidence={len(receipt['retrieved_evidence'])} model={model}"
    )
    return out


# --- mode loops -------------------------------------------------------------------


def run_mode(
    mode: str, *, limit: int | None, task_start: str | None, stub: bool, resume: bool
) -> None:
    tasks = TASK_IDS
    if task_start:
        tasks = tasks[tasks.index(task_start) :]
    if limit:
        tasks = tasks[:limit]

    if mode in ("base", "static"):
        for tid in tasks:
            run_one(tid, mode, stub=stub)
        print(f"  {mode}: {len(tasks)} task(s) complete")
        return

    # adaptive: strictly sequential with an operator gate
    for tid in tasks:
        # 1) legal prefix must be exactly what's promoted
        illegal = check_adaptive_leak(tid)
        if illegal:
            raise SystemExit(
                f"leak guard: unexpected promotions {illegal} before {tid}"
            )
        run_path = run_one(tid, "adaptive", stub=stub)
        # 2) write / refresh the judgment template
        template = judgment_template(tid, run_path, "adaptive")
        if not judgment_confirmations(tid):
            print(
                f"  adaptive STOP at {tid}: operator judgment required -> {REPO_rel(template)}"
            )
            print(
                "    fill the fields, set status: confirmed + confirm: true, "
                "then re-run with --resume"
            )
            return
        # 3) confirmed: derive candidate patches, then promote
        derive, parse_judgment = _load_judgment_parsers()
        judgment = parse_judgment(template)
        run_receipt = common.load_json(run_path) if run_path.is_file() else None
        patches = derive(judgment, run_receipt)
        promo = common.PROMO_RECEIPTS / f"{tid}.json"
        if not promo.is_file():
            common.write_json(
                promo,
                {
                    "schema_version": "1.0",
                    "task_id": tid,
                    "source_task": tid,
                    "promoted_at": utcnow(),
                    "source_judgment": os.path.relpath(template, EXP),
                    "source_run": os.path.relpath(run_path, EXP),
                    "mode": "adaptive",
                    "patches": patches,
                },
            )
            human_now = rebuild_runtime_evidence()
            # close the traceability loop: the run receipt records the promotion
            run_rec = common.load_json(run_path)
            run_rec["promotion"] = {
                "promoted": True,
                "patch_id": patches[0]["id"] if patches else None,
                "receipt_path": os.path.relpath(promo, EXP),
            }
            common.write_json(run_path, run_rec)
            print(
                f"  promoted {tid}: {len(patches)} patch(es); runtime human patches: {human_now}"
            )
        else:
            print(f"  {tid}: already promoted (resume)")
    print(
        f"  adaptive: reached the end of the run window (judgments up to {tasks[-1]})"
    )


def check() -> None:
    """Verify everything except the model call (mirrors run_benchmark --check)."""
    import os as _os

    from dotenv import load_dotenv

    load_dotenv(REPO / ".env", override=False)
    problems = []
    tasks = sorted(common.TASKS_DIR.glob("T*.json"))
    if len(tasks) != 20:
        problems.append(f"tasks: {len(tasks)}/20")
    if not common.FULL_TASKS_DIR.is_dir():
        problems.append("data/derived/tasks_full missing (run scripts/build_tasks.py)")
    n_corpus = len(common.corpus_entries())
    if n_corpus != 20:
        problems.append(f"compiled corpus: {n_corpus}/20")
    from editorial_capability import EditorialEvidenceStore

    EditorialEvidenceStore(common.COMPILED_EVIDENCE)
    if common.RUNTIME_EVIDENCE.is_file():
        EditorialEvidenceStore(common.RUNTIME_EVIDENCE)
    if not _os.getenv("LLM_API_KEY") or not _os.getenv("LLM_MODEL"):
        problems.append("LLM_API_KEY / LLM_MODEL not set (needed for real runs)")
    from zuaef_ace_writing.writing_toolset import DEFAULT_ACE_ROOT

    if not (DEFAULT_ACE_ROOT / "tools" / "ctx.py").is_file():
        problems.append(f"ACE_ROOT invalid: {DEFAULT_ACE_ROOT}")
    else:
        print(f"  ACE root ok: {DEFAULT_ACE_ROOT}")
    human = len(
        [
            e
            for e in common.promoted_human_entries()
            if e.get("source_type") == "human_patch"
        ]
    )
    print(f"  tasks: {len(tasks)} | corpus: {n_corpus} | runtime human: {human}")
    promo = sorted(p.stem for p in common.PROMO_RECEIPTS.glob("T*.json"))
    print(f"  promotions: {promo or 'none'}")
    for tid in promo:
        idx = TASK_IDS.index(tid)
        legal = TASK_IDS[:idx]
        if any(p not in legal for p in promo):
            problems.append(f"promotion order violated around {tid}")
            break
    if problems:
        raise SystemExit("CHECK FAILED:\n  " + "\n  ".join(problems))
    print("  check passed")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=common.MODES)
    ap.add_argument("--task", help="start at this task, e.g. T05")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--check", action="store_true")
    ap.add_argument(
        "--resume",
        action="store_true",
        help="adaptive: continue if judgments confirmed",
    )
    ap.add_argument(
        "--stub", action="store_true", help="deterministic stub model (machinery only)"
    )
    args = ap.parse_args()
    if args.check:
        check()
        return
    if not args.mode:
        ap.error("--mode or --check required")
    if args.mode == "adaptive" and not (args.resume or args.task):
        print(
            "hint: adaptive runs stop after each task awaiting operator judgment; "
            "use --resume to continue past already-confirmed tasks."
        )
    run_mode(
        args.mode,
        limit=args.limit,
        task_start=args.task,
        stub=args.stub,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
