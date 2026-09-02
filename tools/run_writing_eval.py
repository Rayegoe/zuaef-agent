"""Writing field gate — thin runner (Writing SPEC v0.2, Phase 11).

Usage:

    uv run python tools/run_writing_eval.py WCASE-1
    uv run python tools/run_writing_eval.py WCASE-2 --profile ace-writing
    uv run python tools/run_writing_eval.py WCASE-4 --request-limit 40

What this runner does (all MECHANICAL):

- load the case manifest (``benchmarks/writing-cases/<CASE>/case.json``)
  and its raw materials
- ingest bytes -> sha256 -> rights -> ACE workspace -> M-id binding
- invoke the production writing profile once per requested variant
  (``build_profile_agent(profile) -> execute_run``) with ONLY the thin task
  contract (assignment/audience/constraints/article_id)
- collect the outcome and write an evaluation bundle under
  workspace/artifacts/writing-v0.2/eval/<case>/

What it NEVER does (SPEC §29/§31):

- it does not decide material selection, plan, structure, technique choices,
  or revision strategy — those belong to the Writing Agent
- it does not patch or rewrite the article
- fixture data never encodes the expected strategy

A case with a ``feedback`` field runs two passes: the first draft into a
fresh workspace, then a revision pass in the SAME workspace with only the
natural-language feedback appended (WCASE-4 / WRITE-10).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from examples.production_writing import (
    PRODUCTION_PROFILE,
    WritingTask,
    final_artifact_text,
    run_production_task,
)
from zuaef_agent.config import AgentSettings

CASES = REPO / "benchmarks" / "writing-cases"
EVAL_ROOT = REPO / "workspace" / "artifacts" / "writing-v0.2" / "eval"

# T006-B5 benchmark-only candidate: ONE compact synthesis instruction appended
# to the writer instructions. Stays general; encodes no X/Y/Z correction.
SYNTHESIS_BOUNDARY_INSTRUCTION = (
    "When turning evidence into article claims, preserve who owns or states "
    "the evidence, its source/benchmark scope, its modal/logical strength, "
    "and the responsibility subject. Do not strengthen, generalize, or "
    "transfer these boundaries merely to make the thesis cleaner."
)


def load_case(case_dir: Path) -> dict:
    """Case manifest + material paths — mechanical data entry."""
    manifest_path = case_dir / "case.json"
    if not manifest_path.is_file():
        raise SystemExit(f"case manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = case_dir / "raw"
    materials = sorted(p for p in raw.glob("*") if p.is_file())
    if not materials:
        raise SystemExit(f"no materials under {raw}")
    return {"case_dir": case_dir, "manifest": manifest, "materials": materials}


def run_case(
    case: dict,
    *,
    settings: AgentSettings,
    profile: str = PRODUCTION_PROFILE,
    feedback: str | None = None,
    request_limit: int | None = None,
    out_dir: Path | None = None,
    variant: str = "baseline",
    include_technique_guidance: bool = True,
    technique_selection_mode: str = "host",
    synthesis_boundary_instruction: str | None = None,
) -> dict:
    """One case through the production profile; returns the bundle record.

    ``variant`` (T012) only labels the output directory and bundle: "baseline"
    runs happen BEFORE a promoted lesson becomes a repo skill, "learned" runs
    after — the skills surface (``.agents/skills``) is the only difference
    between the two sides."""
    manifest = case["manifest"]
    case_id = manifest["id"]
    article_id = manifest["article_id"]
    out_dir = out_dir or (EVAL_ROOT / case_id / variant)
    out_dir.mkdir(parents=True, exist_ok=True)

    task = WritingTask(
        article_id=article_id,
        assignment=manifest["assignment"],
        audience=manifest.get("audience"),
        constraints=list(manifest.get("constraints") or []),
    )
    rights = str(manifest.get("rights") or "user-provided")
    materials = [str(p) for p in case["materials"]]

    passes: list[dict[str, Any]] = []
    # draft pass (fresh workspace)
    draft = run_production_task(
        settings,
        task=task,
        material_paths=materials,
        rights=rights,
        run_id=article_id,
        clean_workspace=True,
        request_limit=request_limit,
        profile=profile,
        include_technique_guidance=include_technique_guidance,
        technique_selection_mode=technique_selection_mode,
        synthesis_boundary_instruction=synthesis_boundary_instruction,
    )
    passes.append({"pass": "draft", **draft})
    (out_dir / "draft-record.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    draft_text, _draft_path = final_artifact_text(settings.workspace_root, article_id)
    (out_dir / "draft.md").write_text(draft_text, encoding="utf-8")

    # revision pass (same ACE workspace, natural-language feedback only)
    if feedback or manifest.get("feedback"):
        rev_feedback = str(feedback or manifest["feedback"])
        rev_id = f"{article_id}-rev"
        revision = run_production_task(
            settings,
            task=task,
            material_paths=materials,
            rights=rights,
            run_id=rev_id,
            feedback=rev_feedback,
            previous_article=draft_text,
            clean_workspace=False,
            request_limit=request_limit,
            profile=profile,
            include_technique_guidance=include_technique_guidance,
            technique_selection_mode=technique_selection_mode,
            synthesis_boundary_instruction=synthesis_boundary_instruction,
        )
        passes.append({"pass": "revision", "feedback": rev_feedback, **revision})
        (out_dir / "revision-record.json").write_text(
            json.dumps(revision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        rev_text, _rev_path = final_artifact_text(settings.workspace_root, rev_id)
        (out_dir / "revision.md").write_text(rev_text, encoding="utf-8")

    bundle = {
        "case_id": case_id,
        "article_id": article_id,
        "profile": profile,
        "variant": variant,
        "observation_controls": {
            "include_technique_guidance": include_technique_guidance,
            "technique_selection_mode": technique_selection_mode,
            "synthesis_boundary_instruction": (
                synthesis_boundary_instruction is not None
            ),
        },
        "manifest": {k: v for k, v in manifest.items() if k != "feedback"},
        "materials": [str(p) for p in case["materials"]],
        "rights": rights,
        "passes": passes,
    }
    (out_dir / "bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # evaluation note for the human judge
    notes = [
        f"# {case_id} — evaluation bundle",
        "",
        f"- profile: {profile}",
        f"- variant: {variant} (metadata label only)",
        f"- include technique guidance: {include_technique_guidance}",
        f"- technique selection mode: {technique_selection_mode}",
        f"- synthesis boundary instruction: {synthesis_boundary_instruction is not None}",
        f"- assignment: {manifest['assignment']}",
        f"- audience: {manifest.get('audience')}",
        f"- constraints: {json.dumps(manifest.get('constraints') or [], ensure_ascii=False)}",
        f"- materials: {len(case['materials'])} files (host did not select)",
        f"- rights: {rights}",
        "",
        "## DRAFT",
        (
            f"- status: {passes[0].get('status')} "
            f"requests: {passes[0].get('model_requests')} "
            f"chars: {passes[0].get('artifact_chars')}"
        ),
    ]
    if len(passes) > 1:
        notes += [
            "",
            "## REVISION (natural-language feedback only)",
            f"- feedback: {passes[1].get('feedback')}",
            (
                f"- status: {passes[1].get('status')} "
                f"requests: {passes[1].get('model_requests')} "
                f"chars: {passes[1].get('artifact_chars')}"
            ),
        ]
    notes += [
        "",
        (
            "Machine signals are NOT a quality verdict. Human editor judges "
            "output usability (Overall + written editorial notes carry the "
            "most weight)."
        ),
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(notes), encoding="utf-8")
    return bundle


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "case", help="case name, e.g. WCASE-1 (dir under benchmarks/writing-cases/)"
    )
    ap.add_argument("--profile", default=PRODUCTION_PROFILE)
    ap.add_argument("--feedback", default=None)
    ap.add_argument("--request-limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--variant",
        choices=("baseline", "learned"),
        default="baseline",
        help="T012 label only: run 'baseline' BEFORE a promoted lesson "
        "becomes a repo skill, 'learned' after",
    )
    ap.add_argument(
        "--no-technique-guidance",
        action="store_false",
        dest="include_technique_guidance",
        default=True,
        help="T006-B1 candidate: omit host-selected technique shards",
    )
    ap.add_argument(
        "--technique-selection-mode",
        choices=("host", "none", "model"),
        default="host",
        help="T006-B2 experiment seam: host, none, or model-owned technique selection",
    )
    ap.add_argument(
        "--synthesis-boundary",
        action="store_true",
        default=False,
        help=(
            "T006-B5 candidate: append the ONE compact evidence-boundary "
            "synthesis instruction to the writer instructions (desk pack "
            "stays byte-identical)"
        ),
    )
    ap.add_argument(
        "--materials",
        action="append",
        default=None,
        help="optional explicit material list (default: all files under raw/)",
    )
    args = ap.parse_args(argv)

    case_dir = CASES / args.case
    if not case_dir.is_dir():
        raise SystemExit(f"no case dir: {case_dir} (expected directories: WCASE-1..4)")
    case = load_case(case_dir)
    if args.materials:
        case["materials"] = [Path(p) for p in args.materials]

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
    )
    bundle = run_case(
        case,
        settings=settings,
        profile=args.profile,
        feedback=args.feedback,
        request_limit=args.request_limit,
        out_dir=Path(args.out) if args.out else None,
        variant=args.variant,
        include_technique_guidance=args.include_technique_guidance,
        technique_selection_mode=args.technique_selection_mode,
        synthesis_boundary_instruction=(
            SYNTHESIS_BOUNDARY_INSTRUCTION if args.synthesis_boundary else None
        ),
    )
    print(json.dumps(bundle, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
