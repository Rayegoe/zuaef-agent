"""Generic validation-case host runner — data-driven, no case specifics in code.

Sanlian round 1 proved the projection path but exposed its limit: the
material was a published essay, so Writer/Editor could only reword it
(95%+ overlap). A real production input is raw fragments — interview
transcripts, chat logs, meeting notes, platform notices, sample texts —
where the actual writing act is structuring them into an article.

This runner is the generic host for such cases. EVERYTHING case-specific is
data, not code: it lives in ``<case_dir>/case.json`` (host-authored brief:
task + assignment + writing_plan + signal gate rules + run/showcase names)
next to the case's own ``raw/`` materials and ``expected-signals/`` brief.
The runner itself only contains mechanisms:

    MaterialCase (examples/host_fixture.py — data entry only, per-file
        bytes/sha256/rights/ACE ingest -> M ids)
        + case.json brief (host-authored data, loaded from disk)
        -> Host WritingContext (task + writing_plan + concatenated material
           with per-file sha256 separators + caller-owned S1..Sn ledger)
        -> Writer pass  -> Editor pass  -> showcase/

The case's ``expected-signals/README.md`` is the editorial acceptance
criteria; the brief's ``signal_gate`` rules drive a deterministic zero-model
gate over the final article. Neither is projected as material.

Layer rules are the same as the Sanlian runner: the adapter decides nothing,
the writing plan is host-authored data (never auto-generated), no benchmark
joins, examples=[].
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from examples.host_fixture import (
    build_case_sources,
    load_material_case,
    render_case_material,
)
from examples.host_runner import (
    DEFAULT_MEMORY,
    DEFAULT_TECHNIQUES,
    TECHNIQUE_IDS,
    json_default,
    select_memory,
    select_techniques,
    write_showcase_inputs,
    write_showcase_results,
    write_text,
)
from examples.production_writing import (
    final_artifact_text,
    prepare_writing_context,
    render_writing_context,
    run_production_article,
)
from zuaef_agent.config import AgentSettings

DEFAULT_CASE = (
    Path.home()
    / "projects"
    / "article-context-engine"
    / "article-validation-materials"
    / "cases"
    / "01-content-team"
)
BRIEF_FILENAME = "case.json"
BRIEF_REQUIRED = ("id", "title", "assignment", "writing_plan")
PLAN_REQUIRED = (
    "angle",
    "questions",
    "outline",
    "target_length",
    "release_constraints",
)

# --- case brief: host-authored data, loaded from the case directory --------------


def load_case_brief(case_dir: Path) -> dict:
    """The host-authored brief for a case: task + writing_plan + signal gate
    + run/showcase names. Lives next to the raw materials, never in code."""
    path = case_dir / BRIEF_FILENAME
    if not path.is_file():
        raise SystemExit(
            f"case brief missing: {path} — the host authors {BRIEF_FILENAME} "
            f"(task + assignment + writing_plan + signal_gate) next to raw/"
        )
    brief = json.loads(path.read_text(encoding="utf-8"))
    for key in BRIEF_REQUIRED:
        if not brief.get(key):
            raise SystemExit(f"case brief {path} missing required key: {key}")
    plan = brief["writing_plan"]
    for key in PLAN_REQUIRED:
        if key not in plan:
            raise SystemExit(f"case brief {path} writing_plan missing key: {key}")
    return brief


def task_from_brief(brief: dict) -> dict:
    """The task block projected into the WritingContext."""
    return {
        "id": brief["id"],
        "title": brief["title"],
        "audience": brief.get("audience", ""),
        "assignment": brief["assignment"],
    }


def signal_rules_from_brief(brief: dict) -> dict:
    """Signal gate rules are case data (editorial choices), not code."""
    return brief.get("signal_gate") or {}


# --- expected-signals gate (deterministic, zero model) ---------------------------


def check_expected_signals(text: str, rules: dict) -> dict:
    """Zero-model gate over the final article, driven by the brief's rules.

    A heuristic tripwire for the human judge, never a substitute for the
    human verdict.
    """
    forbidden = tuple(rules.get("forbidden") or ())
    required = tuple(rules.get("required") or ())
    required_min = int(rules.get("required_min", 2))
    forbidden_hits = [p for p in forbidden if p in text]
    required_present = [p for p in required if p in text]
    required_missing = [p for p in required if p not in text]
    ok = not forbidden_hits and (not required or len(required_present) >= required_min)
    return {
        "pass": ok,
        "forbidden_hits": forbidden_hits,
        "required_present": required_present,
        "required_missing": required_missing,
        "required_min": required_min,
    }


# --- workbench assembly ----------------------------------------------------------


def project_case_context(case, brief: dict, techniques, memory) -> dict:
    """The exact WritingContext bundle: concatenated material with per-file
    sha256 separators + caller-owned S1..Sn ledger + one binding hash over
    the projected material text. Task/plan come from the brief (data)."""
    material = render_case_material(case)
    task = task_from_brief(brief)
    return prepare_writing_context(
        task_id=task["id"],
        material=material,
        title=task["title"],
        audience=task["audience"],
        assignment=task["assignment"],
        writing_plan=brief["writing_plan"],
        sources=build_case_sources(case),
        source_sha256=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
    )


def writer_prompt(case, brief: dict, techniques, memory, writer_run: str) -> str:
    task = task_from_brief(brief)
    bundle = project_case_context(case, brief, techniques, memory)
    return (
        f"Write the article for task {task['id']}.\n\n"
        + render_writing_context(bundle)
        + f"\n\nThe ACE article workspace id for THIS task is exactly `{writer_run}` — "
        f"you MUST pass this exact value as article_id to save_artifact. The task id "
        f"`{task['id']}` is NOT a workspace id and will fail the save.\n\n"
        "Submit the complete article with save_artifact exactly once, together with "
        "the claim and source ledgers. Pass the COMPLETE projected source ledger "
        "(every S row shown under '### sources (ledger base)') — a save that drops "
        "sources breaks ACE's validation. Every claim MUST include "
        '"status":"resolved" and source_ids referencing only those S ids. '
        f"Once save_artifact returns fact_check_passed: true, return your RunSummary "
        f'immediately with EXACTLY: artifacts=["artifacts/{writer_run}/final.md"], '
        f'evidence=["artifact:artifacts/{writer_run}/final.md"]. Do NOT copy the '
        "canonical_path from the save result (it is outside artifacts/ and fails "
        "verification). ACE's human_final_reviewed flag is a human-only release flag "
        "and is expected to stay pending — never report it as an unknown.\n\n"
        "Write it now and save it via save_artifact."
    )


def editor_prompt(
    case, brief: dict, draft_text: str, techniques, memory, editor_run: str
) -> str:
    task = task_from_brief(brief)
    bundle = project_case_context(case, brief, techniques, memory)
    return (
        f"You are the editorial pass for task {task['id']}.\n\n"
        f"The ACE article workspace id for THIS pass is exactly `{editor_run}` — "
        f"you MUST pass this exact value as article_id to save_artifact. The task id "
        f"`{task['id']}` is NOT a workspace id and will fail the save.\n\n"
        f"Assignment: {task['assignment']}\n\n"
        "The writer produced this draft:\n\n"
        f"<writer-draft>\n{draft_text}\n</writer-draft>\n\n"
        "Apply minimal targeted editorial improvements only, guided by the "
        "writing plan, techniques and editorial memory below. Preserve every "
        "fact, number, quote and claim; never rewrite the whole article. If "
        "the draft already meets the bar, save it as-is. Pass the COMPLETE "
        "projected source ledger with the save; every claim MUST include "
        '"status":"resolved" and source_ids referencing only the projected S ids. '
        f"Once save_artifact returns fact_check_passed: true, return your RunSummary "
        f'immediately with EXACTLY: artifacts=["artifacts/{editor_run}/final.md"], '
        f'evidence=["artifact:artifacts/{editor_run}/final.md"]. Do NOT copy '
        "the canonical_path from the save result (it is outside artifacts/ and "
        "fails verification). ACE's human_final_reviewed flag is a human-only "
        "release flag and is expected to stay pending — never report it as an "
        "unknown, and never use knowledge: refs in evidence.\n\n"
        + render_writing_context(bundle)
    )


# --- showcase files --------------------------------------------------------------


def write_readme(
    showcase: Path,
    case,
    brief: dict,
    *,
    writer_record: dict | None,
    editor_record: dict | None,
    signals: dict | None,
) -> None:
    lines = [
        f"# Validation Case — {brief['title']}",
        "",
        "生产输入实验：**原始碎片素材** -> 写作计划（host-authored，case.json）",
        "-> Writer 初稿 -> Editor 成稿。这里没有一篇成熟文章可以“改字句”——",
        "成稿必须从碎片里长出来。",
        "",
        "## 文件",
        "",
        "- `00-expected-signals.md` — 验收标准原文（editorial brief，不是素材）",
    ]
    for f in case.files:
        lines.append(f"- `01-raw-{Path(f.source_ref).name}` — 原材料逐字节原文")
    lines += [
        "- `02-writing-plan.md` — 写作计划（case.json：task + assignment + writing_plan）",
        "- `03-writer-draft.md` — Writer 初稿（production 投影，save_artifact only）",
        "- `04-editor-final.md` — Editor 成稿（同一稿的最小定向修补）",
        "- `05-diff-writer-to-final.diff` — 初稿 -> 成稿逐行 diff",
        "- `writer-context.md` — 注入 request #1 的完整 WritingContext 原文",
        "- `receipt.json` — 运行记录（材料身份 + 两个 pass 的 receipt 证据）",
        "",
        "## 材料身份（逐文件 hash 绑定）",
        "",
        f"- rights: `{case.rights}`（实验用途，不对外分发）",
        "",
    ]
    for f in case.files:
        lines.append(
            f"- `{f.source_ref}` — sha256 `{f.sha256}` · {f.source_byte_length} B · "
            f"{f.projected_char_length} chars · M{f.material_id[-3:] if f.material_id else '???'}"
        )
    lines += [
        "",
        "验证：对每个源文件重算 sha256 应与上表一致；WritingContext 里每个 `<file>`",
        "分隔块就是该文件逐字节原文，`writing_context.source_sha256` 是整段投影文本",
        "的 hash，记录在 receipt.json 的两次运行里。",
    ]
    if writer_record and editor_record:
        w, e = writer_record, editor_record
        lines += [
            "",
            "## 运行（requests 是次要指标，可读性是首要指标）",
            "",
            (
                f"- Writer: status=`{w.get('status')}` requests={w.get('model_requests')} "
                f"chars={w.get('artifact_chars')} sha256=`{w.get('artifact_sha256')}`"
            ),
            (
                f"- Editor: status=`{e.get('status')}` requests={e.get('model_requests')} "
                f"chars={e.get('artifact_chars')} sha256=`{e.get('artifact_sha256')}`"
            ),
            "- 目标：Writer ≤3 / Editor ≤2~3 / 合计 ≤5~6（实际见上）",
        ]
    if signals:
        lines += [
            "",
            "## 信号门（零模型启发式，最终判断靠人）",
            "",
            f"- forbidden 命中：{signals['forbidden_hits'] or '无'}",
            (
                f"- required 命中：{signals['required_present']}（至少 "
                f"{signals['required_min']} 项）"
            ),
            f"- 结论：{'PASS（可进入人工判断）' if signals['pass'] else 'FAIL（见上，人工复核）'}",
        ]
    lines += [
        "",
        "## 诚实声明",
        "",
        "- `examples=[]`：不投 exemplar，只测 Skill 能否从碎片素材驱动写作。",
        "- 素材总字符远小于 target_length 时，成稿偏短不判失败——",
        "  release_constraints 优先，编造才算。",
        "- 成稿质量需要人工判断；本 README 不下结论。",
    ]
    for note in brief.get("notes") or []:
        lines.append(f"- {note}")
    write_text(showcase / "README.md", "\n".join(lines) + "\n")


# --- run -------------------------------------------------------------------------


def run_case(
    *,
    case_dir: Path,
    showcase: Path | None,
    techniques_path: Path,
    memory_path: Path,
    writer_limit: int,
    editor_limit: int,
    rights: str | None,
    check_only: bool,
) -> dict:
    brief = load_case_brief(case_dir)
    rights = rights or brief.get("rights", "user-provided")
    showcase = showcase or (
        REPO
        / "workspace"
        / "artifacts"
        / "showcase"
        / brief.get("showcase_name", case_dir.name)
    )
    case = load_material_case(case_dir, rights=rights)
    techniques = select_techniques(techniques_path)
    memory = select_memory(memory_path)
    bundle = project_case_context(case, brief, techniques, memory)
    task = task_from_brief(brief)
    base = brief.get("run_base", "case")
    writer_run, editor_run = f"{base}-w", f"{base}-e"
    write_showcase_inputs(
        showcase, task=task, writing_plan=brief["writing_plan"], files=case.files
    )
    signals_path = case_dir / "expected-signals" / "README.md"
    if signals_path.is_file():
        write_text(
            showcase / "00-expected-signals.md",
            signals_path.read_text(encoding="utf-8"),
        )
    write_text(
        showcase / "writer-context.md",
        writer_prompt(case, brief, techniques, memory, writer_run) + "\n",
    )
    if check_only:
        write_readme(
            showcase, case, brief, writer_record=None, editor_record=None, signals=None
        )
        print(
            json.dumps(
                {
                    "status": "check passed (no model calls)",
                    "showcase": str(showcase),
                    "case": case.to_record(),
                    "technique_ids": [t["id"] for t in techniques],
                    "memory_ids": [e["id"] for e in memory],
                    "examples_projected": [],
                    "writing_plan_sections": list(brief["writing_plan"]),
                    "writer_context_chars": len(render_writing_context(bundle)),
                },
                ensure_ascii=False,
                indent=2,
                default=json_default,
            )
        )
        return {"status": "check"}

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )

    print(f"[1/3] Writer pass ({writer_run}, limit {writer_limit}) ...")
    writer_record = run_production_article(
        settings,
        task_id=task["id"],
        material_path=case.files[0].source_path,
        material_paths=[f.source_path for f in case.files],
        title=task["title"],
        audience=task["audience"],
        assignment=task["assignment"],
        writing_plan=brief["writing_plan"],
        sources=build_case_sources(case),
        source_sha256=bundle["source_sha256"],
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=writer_limit,
        run_id=writer_run,
        prompt=writer_prompt(case, brief, techniques, memory, writer_run),
    )
    print(
        f"    writer: status={writer_record.get('status')} "
        f"requests={writer_record.get('model_requests')} "
        f"artifact={'yes' if writer_record.get('artifact_exists') else 'NO'}"
    )
    draft_text, draft_path = final_artifact_text(REPO / "workspace", writer_run)
    if not draft_text:
        raise SystemExit("writer pass produced no artifact — see receipt above")

    print(f"[2/3] Editor pass ({editor_run}, limit {editor_limit}) ...")
    editor_record = run_production_article(
        settings,
        task_id=task["id"],
        material_path=case.files[0].source_path,
        material_paths=[f.source_path for f in case.files],
        title=task["title"],
        audience=task["audience"],
        assignment=task["assignment"],
        writing_plan=brief["writing_plan"],
        sources=build_case_sources(case),
        source_sha256=bundle["source_sha256"],
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=editor_limit,
        run_id=editor_run,
        prompt=editor_prompt(case, brief, draft_text, techniques, memory, editor_run),
    )
    print(
        f"    editor: status={editor_record.get('status')} "
        f"requests={editor_record.get('model_requests')} "
        f"artifact={'yes' if editor_record.get('artifact_exists') else 'NO'}"
    )
    final_text, final_path = final_artifact_text(REPO / "workspace", editor_run)
    if not final_text:
        raise SystemExit("editor pass produced no artifact — see receipt above")

    # Step 5 of the fixture contract: bind the real ACE material ids per file.
    bound = load_material_case(
        case_dir, rights=rights, article_id=writer_run, title=task["title"]
    )
    bound_editor = load_material_case(
        case_dir, rights=rights, article_id=editor_run, title=task["title"]
    )

    print("[3/3] Writing showcase ...")
    signals = check_expected_signals(final_text, signal_rules_from_brief(brief))
    identity = {
        "case": bound.to_record(),
        "task": task,
        "writing_plan": brief["writing_plan"],
        "signal_gate": signal_rules_from_brief(brief),
        "technique_ids": list(TECHNIQUE_IDS),
        "examples_projected": [],
        "expected_signals_gate": signals,
    }
    write_showcase_results(
        showcase,
        identity=identity,
        writer_record=writer_record,
        editor_record=editor_record,
        workspace_root=REPO / "workspace",
    )
    write_readme(
        showcase,
        bound,
        brief,
        writer_record=writer_record,
        editor_record=editor_record,
        signals=signals,
    )
    record = {
        "status": "done",
        "showcase": str(showcase),
        "case": bound.to_record(),
        "writer": writer_record,
        "editor": editor_record,
        "expected_signals_gate": signals,
        "material_ids_bound": {
            "writer": [f.material_id for f in bound.files],
            "editor": [f.material_id for f in bound_editor.files],
        },
        "writer_draft_path": draft_path,
        "editor_final_path": final_path,
    }
    print(json.dumps(record, ensure_ascii=False, indent=2, default=json_default))
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", default=str(DEFAULT_CASE))
    ap.add_argument(
        "--showcase",
        default=None,
        help="output dir (default: workspace/artifacts/showcase/<case.json showcase_name>)",
    )
    ap.add_argument("--techniques-jsonl", default=str(DEFAULT_TECHNIQUES))
    ap.add_argument("--memory-jsonl", default=str(DEFAULT_MEMORY))
    ap.add_argument(
        "--rights",
        default=None,
        choices=("study-only", "licensed", "user-provided", "unknown"),
        help="override the brief's rights",
    )
    ap.add_argument("--writer-limit", type=int, default=8)
    ap.add_argument("--editor-limit", type=int, default=6)
    ap.add_argument(
        "--check",
        action="store_true",
        help="assemble case + plan + projected context ONLY, zero model calls",
    )
    args = ap.parse_args()
    run_case(
        case_dir=Path(args.case_dir),
        showcase=Path(args.showcase) if args.showcase else None,
        techniques_path=Path(args.techniques_jsonl),
        memory_path=Path(args.memory_jsonl),
        writer_limit=args.writer_limit,
        editor_limit=args.editor_limit,
        rights=args.rights,
        check_only=args.check,
    )


if __name__ == "__main__":
    main()
