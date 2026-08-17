"""Validation-case host runner — raw fragments, not a finished article.

Sanlian round 1 proved the projection path but exposed its limit: the
material was a published essay, so Writer/Editor could only reword it
(95%+ overlap). A real production input is raw fragments — interview
transcripts, chat logs, meeting notes, platform notices, sample texts —
where the actual writing act is structuring them into an article.

This runner is the host for such a case (default: ACE validation case
``01-content-team``):

    MaterialCase (examples/host_fixture.py — data entry only, per-file
        bytes/sha256/rights/ACE ingest -> M ids)
        -> Host WritingContext (task + writing_plan + concatenated material
           with per-file sha256 separators + caller-owned S1..Sn ledger)
        -> Writer pass  -> Editor pass  -> showcase/

The case's ``expected-signals/README.md`` is the editorial acceptance
criteria — the host derives release constraints from it and the runner runs
a deterministic zero-model signal gate on the final article. It is NOT
projected as material.

Layer rules are the same as the Sanlian runner: the adapter decides nothing,
the writing plan is host-authored (hand-written, never auto-generated), no
benchmark joins, examples=[].
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_SHOWCASE = REPO / "workspace" / "artifacts" / "showcase" / "content-team-01"

# --- host-authored task + writing plan (hand-written, from the case) -------------


TASK: dict[str, str] = {
    "id": "case-01-content-team",
    "title": "说不清的“像真人”",
    "audience": "内容行业业务案例读者——Field/Case 叙事",
    "assignment": (
        "根据这批原始素材（平台提示、访谈转录、团队聊天、会议速记、文章样本）"
        "写一篇 Field/Case 叙事：一个日产过万的内容团队，被平台提示“同质化/低质”，"
        "却说不清什么是“好”。从具体的人和话进入，呈现矛盾，不做结论。只使用素材"
        "里已有的内容；数字标注为客户报数；不写平台检测机制；不补写现场细节。"
    ),
}

WRITING_PLAN: dict[str, Any] = {
    "angle": (
        "三千个号、日产过万的内容团队，质量判断却只有一句“大概看起来像真人”——"
        "看高产能与不可言说的标准之间的裂缝。"
    ),
    "questions": [
        "谁在判断一篇能不能发？",
        "“像真人”为什么说不清？",
        "换模型、加审核 agent，为什么都接不住这个问题？",
        "是平台变了，还是自己越写越像了？",
    ],
    "outline": [
        "从一条平台提示或一段对话进入",
        "摆出规模与人力（客户报数，标注来源）",
        "编辑的经验判断失效的过程",
        "运营/技术/编辑三个视角对“像真人”的不同理解",
        "回到未解的矛盾，不做结论",
    ],
    "target_length": "1200-1800 Chinese chars",
    "release_constraints": [
        "3000/12000/6 是客户报数，不写成独立核验事实",
        "不写“平台通过指纹/算法识别AI内容”——没有证据",
        "不补写天气、城市、办公室陈设等现场细节",
        "只用素材中已有的对话与人物，不虚构",
        "不把推测写成事实（推测需划线：也许/可能）",
    ],
}

# --- expected-signals gate (deterministic, zero model) ---------------------------

# Derived from the case's expected-signals/README.md. The gate is a heuristic
# tripwire for the human judge, never a substitute for the human verdict.
FORBIDDEN_PHRASES = ("指纹", "识别AI", "AI识别", "算法识别", "算法检测", "模型检测")
REQUIRED_SOFT = ("客户", "同质化", "像真人")
REQUIRED_SOFT_MIN = 2


def check_expected_signals(text: str) -> dict:
    """Zero-model gate over the final article against the case's signals."""
    forbidden_hits = [p for p in FORBIDDEN_PHRASES if p in text]
    required_present = [p for p in REQUIRED_SOFT if p in text]
    required_missing = [p for p in REQUIRED_SOFT if p not in text]
    ok = not forbidden_hits and len(required_present) >= REQUIRED_SOFT_MIN
    return {
        "pass": ok,
        "forbidden_hits": forbidden_hits,
        "required_present": required_present,
        "required_missing": required_missing,
        "required_soft_min": REQUIRED_SOFT_MIN,
    }


# --- workbench assembly ----------------------------------------------------------


def project_case_context(case, techniques, memory) -> dict:
    """The exact WritingContext bundle: concatenated material with per-file
    sha256 separators + caller-owned S1..Sn ledger + one binding hash over
    the projected material text."""
    material = render_case_material(case)
    return prepare_writing_context(
        task_id=TASK["id"],
        material=material,
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=build_case_sources(case),
        source_sha256=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
    )


def writer_prompt(case, techniques, memory, writer_run: str) -> str:
    bundle = project_case_context(case, techniques, memory)
    return (
        f"Write the article for task {TASK['id']}.\n\n"
        + render_writing_context(bundle)
        + f"\n\nThe ACE article workspace id for THIS task is exactly `{writer_run}` — "
        f"you MUST pass this exact value as article_id to save_artifact. The task id "
        f"`{TASK['id']}` is NOT a workspace id and will fail the save.\n\n"
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


def editor_prompt(case, draft_text: str, techniques, memory, editor_run: str) -> str:
    bundle = project_case_context(case, techniques, memory)
    return (
        f"You are the editorial pass for task {TASK['id']}.\n\n"
        f"The ACE article workspace id for THIS pass is exactly `{editor_run}` — "
        f"you MUST pass this exact value as article_id to save_artifact. The task id "
        f"`{TASK['id']}` is NOT a workspace id and will fail the save.\n\n"
        f"Assignment: {TASK['assignment']}\n\n"
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
    *,
    writer_record: dict | None,
    editor_record: dict | None,
    signals: dict | None,
) -> None:
    lines = [
        "# Validation Case 01 — 内容团队的质检困境（说不清的“像真人”）",
        "",
        "生产输入实验：**原始碎片素材**（访谈/聊天/速记/平台提示/样本）-> 写作计划",
        "-> Writer 初稿 -> Editor 成稿。与《便利店奇妙夜》不同，这里没有一篇成熟",
        "文章可以“改字句”——成稿必须从碎片里长出来。",
        "",
        "## 文件",
        "",
        "- `00-expected-signals.md` — 验收标准原文（editorial brief，不是素材）",
    ]
    for f in case.files:
        lines.append(f"- `01-raw-{Path(f.source_ref).name}` — 原材料逐字节原文")
    lines += [
        "- `02-writing-plan.md` — 写作计划（host-authored：task + assignment + writing_plan）",
        "- `03-writer-draft.md` — Writer 初稿（production 投影，save_artifact only）",
        "- `04-editor-final.md` — Editor 成稿（同一稿的最小定向修补）",
        "- `05-diff-writer-to-final.diff` — 初稿 -> 成稿逐行 diff",
        "- `writer-context.md` — 注入 request #1 的完整 WritingContext 原文",
        "- `receipt.json` — 运行记录（材料身份 + 两个 pass 的 receipt 证据）",
        "",
        "## 材料身份（逐文件 hash 绑定）",
        "",
        f"- rights: `{case.rights}`（客户提供的内部素材，实验用途，不对外分发）",
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
            f"- required 命中：{signals['required_present']}（至少 {REQUIRED_SOFT_MIN} 项）",
            f"- 结论：{'PASS（可进入人工判断）' if signals['pass'] else 'FAIL（见上，人工复核）'}",
        ]
    lines += [
        "",
        "## 诚实声明",
        "",
        "- `examples=[]`：不投 exemplar，只测 Skill 能否从碎片素材驱动写作。",
        "- 3000/12000/6 是客户报数：成稿若引用必须标注来源（客户称…），不得写成独立核验事实。",
        "- expected-signals 禁止的断言（平台检测机制等）由信号门做第一道拦截。",
        "- 素材总字符约 1200，target_length 1200-1800：实际成稿偏短（9xx）时，",
        "  不判失败——release_constraints 优先，编造才算。",
        "- 成稿质量需要人工判断；本 README 不下结论。",
    ]
    write_text(showcase / "README.md", "\n".join(lines) + "\n")


# --- run -------------------------------------------------------------------------


def run_case(
    *,
    case_dir: Path,
    showcase: Path,
    techniques_path: Path,
    memory_path: Path,
    writer_limit: int,
    editor_limit: int,
    rights: str,
    check_only: bool,
) -> dict:
    case = load_material_case(case_dir, rights=rights)
    techniques = select_techniques(techniques_path)
    memory = select_memory(memory_path)
    bundle = project_case_context(case, techniques, memory)
    base = "case01"
    writer_run, editor_run = f"{base}-w", f"{base}-e"
    write_showcase_inputs(
        showcase, task=TASK, writing_plan=WRITING_PLAN, files=case.files
    )
    signals_path = case_dir / "expected-signals" / "README.md"
    if signals_path.is_file():
        write_text(
            showcase / "00-expected-signals.md",
            signals_path.read_text(encoding="utf-8"),
        )
    write_text(
        showcase / "writer-context.md",
        writer_prompt(case, techniques, memory, writer_run) + "\n",
    )
    if check_only:
        write_readme(
            showcase, case, writer_record=None, editor_record=None, signals=None
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
                    "writing_plan_sections": list(WRITING_PLAN),
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
        task_id=TASK["id"],
        material_path=case.files[0].source_path,
        material_paths=[f.source_path for f in case.files],
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=build_case_sources(case),
        source_sha256=bundle["source_sha256"],
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=writer_limit,
        run_id=writer_run,
        prompt=writer_prompt(case, techniques, memory, writer_run),
    )
    print(
        f"    writer: status={writer_record.get('status')} "
        f"requests={writer_record.get('model_requests')} "
        f"artifact={'yes' if writer_record.get('artifact_exists') else 'NO'}"
    )
    from examples.production_writing import final_artifact_text

    draft_text, draft_path = final_artifact_text(REPO / "workspace", writer_run)
    if not draft_text:
        raise SystemExit("writer pass produced no artifact — see receipt above")

    print(f"[2/3] Editor pass ({editor_run}, limit {editor_limit}) ...")
    editor_record = run_production_article(
        settings,
        task_id=TASK["id"],
        material_path=case.files[0].source_path,
        material_paths=[f.source_path for f in case.files],
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=build_case_sources(case),
        source_sha256=bundle["source_sha256"],
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=editor_limit,
        run_id=editor_run,
        prompt=editor_prompt(case, draft_text, techniques, memory, editor_run),
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
        case_dir, rights=rights, article_id=writer_run, title=TASK["title"]
    )
    bound_editor = load_material_case(
        case_dir, rights=rights, article_id=editor_run, title=TASK["title"]
    )

    print("[3/3] Writing showcase ...")
    signals = check_expected_signals(final_text)
    identity = {
        "case": bound.to_record(),
        "task": TASK,
        "writing_plan": WRITING_PLAN,
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
    ap.add_argument("--showcase", default=str(DEFAULT_SHOWCASE))
    ap.add_argument("--techniques-jsonl", default=str(DEFAULT_TECHNIQUES))
    ap.add_argument("--memory-jsonl", default=str(DEFAULT_MEMORY))
    ap.add_argument(
        "--rights",
        default="user-provided",
        choices=("study-only", "licensed", "user-provided", "unknown"),
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
        showcase=Path(args.showcase),
        techniques_path=Path(args.techniques_jsonl),
        memory_path=Path(args.memory_jsonl),
        writer_limit=args.writer_limit,
        editor_limit=args.editor_limit,
        rights=args.rights,
        check_only=args.check,
    )


if __name__ == "__main__":
    main()
