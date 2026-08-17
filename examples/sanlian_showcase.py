"""Sanlian Host Fixture / Writing Plan Projection v0.1 — showcase runner.

The HOST prepares the workbench; the agent never wanders the repo. This
runner is the host for the first real production input experiment:

    SanlianFixture (examples/sanlian_fixture.py — data entry only)
        -> Host WritingContext (prepare_writing_context: task + writing_plan
           + material + caller-owned sources + techniques + editorial memory)
        -> Writer pass  (production projection, save_artifact only)
        -> Editor pass  (same minimal surface, minimal targeted patches)
        -> showcase/    (raw material / writing plan / writer draft / final,
                         directly openable, no receipt needed to judge)

Layer rules honored here:

- The fixture adapter decides NOTHING about techniques, structure, or style
  and never calls an LLM. The writing plan below is HOST-AUTHORED (explicit,
  hand-written for this experiment — never auto-generated).
- Techniques/editorial memory come from the curated Writing Skill pack
  (curated/techniques.jsonl + compiled/evidence.jsonl records, caller-selected
  verbatim). No benchmark task ids, no sequential_inputs join, no task_inputs.
- examples=[] on purpose: this run tests whether the Skill drives writing
  from the MATERIAL alone, not from exemplar imitation.
- The material projected into request #1 is the EXACT fixture bytes; the run
  receipt records writing_context.source_sha256 so "the file was right but
  the model got something else" can never happen again.

Stop condition (v0.1): exactly this. No database, no memory service, no
retrieval system, no new sensors/actions, no 22-article ingest, no
auto-selection, no auto writing plan, no embeddings, no editor team.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from datetime import date, datetime
from decimal import Decimal
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
    final_artifact_text,
    prepare_writing_context,
    render_writing_context,
    run_production_article,
)
from examples.sanlian_fixture import load_sanlian_fixture
from zuaef_agent.config import AgentSettings

DEFAULT_FIXTURE = (
    Path.home()
    / "docuwiki"
    / "wiki-sanlian-life-weekly-2026-30"
    / "sources"
    / "22-便利店奇妙夜.md"
)
BENCH = REPO / "benchmarks" / "editorial-learning"
DEFAULT_TECHNIQUES = BENCH / "curated" / "techniques.jsonl"
DEFAULT_MEMORY = BENCH / "compiled" / "evidence.jsonl"
DEFAULT_SHOWCASE = (
    REPO / "workspace" / "artifacts" / "showcase" / "sanlian-convenience-night"
)

# --- host-authored task + writing plan (this experiment, hand-written) ----------


TASK: dict[str, str] = {
    "id": "sanlian-22-convenience-night",
    "title": "便利店奇妙夜",
    "audience": "三联生活周刊读者——城市夜间生活观察",
    "assignment": (
        "以《便利店奇妙夜》这篇第一人称现场记录为唯一材料，重新组织成一篇"
        "可独立阅读的城市夜生活观察短文：从材料已有的现场进入，让人物与动作"
        "自己展开，最后回到具体生活，不做宏大总结。全文只使用材料中出现的"
        "场景、人物、对话与细节；材料没有答案的问题不得擅自解释。"
    ),
}

WRITING_PLAN: dict[str, Any] = {
    "angle": ("从便利店夜班中的具体人物和小事件进入，看城市夜生活中被忽略的一层日常。"),
    "questions": [
        "夜里的便利店里什么人在出现？",
        "店员如何理解这些陌生人？",
        "哪些细节能说明城市夜间生活？",
        "哪些东西材料没有答案，不能擅自解释？",
    ],
    "outline": [
        "从一个材料已有的现场进入",
        "人物与动作展开",
        "扩展到便利店夜间角色",
        "最后回到具体生活，不做宏大总结",
    ],
    "target_length": "2500-3500 Chinese chars",
    "release_constraints": [
        "不制造采访",
        "不新增人物经历",
        "不创造原文不存在的现场",
        "不把推测写成事实",
    ],
}

TECHNIQUE_IDS = (
    "T001",
    "T002",
    "T003",
    "T004",
    "T005",
    "T006",
    "T007",
    "T008",
    "T009",
    "T010",
    "T011",
    "T012",
    "T013",
    "T014",
    "T015",
    "T016",
    "T017",
    "T018",
    "T019",
    "T020",
)


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(f"missing jsonl: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_techniques(path: Path) -> list[dict]:
    """The curated Writing Skill pack (caller-owned methodology records)."""
    records = load_jsonl(path)
    wanted = set(TECHNIQUE_IDS)
    selected = [t for t in records if t.get("id") in wanted]
    if len(selected) != len(TECHNIQUE_IDS):
        raise SystemExit(
            f"technique pack incomplete: expected {len(TECHNIQUE_IDS)} ids, "
            f"found {len(selected)} in {path}"
        )
    return selected


def select_memory(path: Path) -> list[dict]:
    """Corpus evidence records as editorial memory (caller-owned)."""
    records = load_jsonl(path)
    wanted = {f"corpus.{tid}" for tid in TECHNIQUE_IDS}
    selected = [e for e in records if e.get("id") in wanted]
    if len(selected) != len(TECHNIQUE_IDS):
        raise SystemExit(
            f"memory pack incomplete: expected {len(TECHNIQUE_IDS)} ids, "
            f"found {len(selected)} in {path}"
        )
    return selected


def source_entry(fixture) -> dict:
    """Caller-owned S1 ledger row carrying the fixture identity metadata."""
    return {
        "id": "S1",
        "kind": "material",
        "label": TASK["title"],
        "material_ids": [fixture.material_id or "M001"],
        "source_ref": fixture.source_ref,
        "sha256": fixture.sha256,
        "rights": fixture.rights,
    }


def project_writer_context(fixture, techniques, memory) -> dict:
    """The exact WritingContext bundle projected into writer request #1."""
    return prepare_writing_context(
        task_id=TASK["id"],
        material=fixture.text,
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=[source_entry(fixture)],
        source_sha256=fixture.sha256,
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
    )


def project_editor_context(fixture, techniques, memory) -> dict:
    """Editor pass sees the same workbench (same task/plan/material/ledger)."""
    return project_writer_context(fixture, techniques, memory)


def writer_prompt(fixture, techniques, memory, writer_run: str) -> str:
    """Host-authored request #1 for the Writer pass.

    The workspace id and the claim format are stated explicitly: round 1
    measured the model substituting the task id for the workspace id and
    resubmitting claims without ``status`` (ACE rejects them as unresolved),
    which burned requests without ever finishing the run.
    """
    bundle = project_writer_context(fixture, techniques, memory)
    return (
        f"Write the article for task {TASK['id']}.\n\n"
        + render_writing_context(bundle)
        + f"\n\nThe ACE article workspace id for THIS task is exactly `{writer_run}` — "
        f"you MUST pass this exact value as article_id to save_artifact. The task id "
        f"`{TASK['id']}` is NOT a workspace id and will fail the save.\n\n"
        "Submit the complete article with save_artifact exactly once, together with "
        "the claim and source ledgers. Every claim MUST include "
        '"status":"resolved" and real source_ids — ACE rejects unresolved claims. '
        f"Once save_artifact returns fact_check_passed: true, return your RunSummary "
        f'immediately with EXACTLY: artifacts=["artifacts/{writer_run}/final.md"], '
        f'evidence=["artifact:artifacts/{writer_run}/final.md"]. Do NOT copy the '
        "canonical_path from the save result (it is outside artifacts/ and fails "
        "verification). ACE's human_final_reviewed flag is a human-only release flag "
        "and is expected to stay pending — never report it as an unknown.\n\n"
        "Write it now and save it via save_artifact."
    )


def editor_prompt(fixture, draft_text: str, techniques, memory, editor_run: str) -> str:
    bundle = project_editor_context(fixture, techniques, memory)
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
        "the draft already meets the bar, save it as-is. Every claim MUST "
        'include "status":"resolved" and real source_ids. Once save_artifact '
        f"returns fact_check_passed: true, return your RunSummary immediately "
        f'with EXACTLY: artifacts=["artifacts/{editor_run}/final.md"], '
        f'evidence=["artifact:artifacts/{editor_run}/final.md"]. Do NOT copy '
        "the canonical_path from the save result (it is outside artifacts/ and "
        "fails verification). ACE's human_final_reviewed flag is a human-only "
        "release flag and is expected to stay pending — never report it as an "
        "unknown, and never use knowledge: refs in evidence.\n\n"
        + render_writing_context(bundle)
    )


# --- showcase files -------------------------------------------------------------


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json_default(obj: Any) -> Any:
    """Run receipts carry Decimal token counts / datetimes — keep JSON-clean."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_showcase_inputs(showcase: Path, fixture) -> None:
    """Raw material + writing plan only (also used by --check)."""
    write_text(
        showcase / "01-raw-material-22-便利店奇妙夜.md",
        fixture.text,
    )
    write_text(
        showcase / "02-writing-plan.md",
        "# 写作计划（host-authored）\n\n"
        f"## task\n\n```json\n{json.dumps(TASK, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## writing_plan\n\n```json\n"
        f"{json.dumps(WRITING_PLAN, ensure_ascii=False, indent=2)}\n```\n",
    )


def write_showcase_results(
    showcase: Path, fixture, *, writer_record, editor_record
) -> None:
    draft_text, _ = final_artifact_text(REPO / "workspace", writer_record["run_id"])
    final_text, _ = final_artifact_text(REPO / "workspace", editor_record["run_id"])
    write_text(showcase / "03-writer-draft.md", draft_text)
    write_text(showcase / "04-editor-final.md", final_text)
    diff = "".join(
        difflib.unified_diff(
            draft_text.splitlines(keepends=True),
            final_text.splitlines(keepends=True),
            fromfile="03-writer-draft.md",
            tofile="04-editor-final.md",
        )
    )
    write_text(
        showcase / "05-diff-writer-to-final.diff",
        diff or "(writer draft and editor final are identical)\n",
    )
    write_text(
        showcase / "receipt.json",
        json.dumps(
            {
                "fixture": fixture.to_record(),
                "task": TASK,
                "writing_plan": WRITING_PLAN,
                "technique_ids": list(TECHNIQUE_IDS),
                "examples_projected": [],
                "writer": writer_record,
                "editor": editor_record,
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        ),
    )


def write_readme(
    showcase: Path,
    fixture,
    *,
    writer_record: dict | None,
    editor_record: dict | None,
) -> None:
    lines = [
        "# Sanlian Host Fixture v0.1 — 《便利店奇妙夜》",
        "",
        "第一次真实生产写作输入实验：原材料 + 写作计划 -> Writer 初稿 -> Editor 成稿。",
        "打开本目录即可判断这个系统值不值得继续，不需要读任何 receipt/schema。",
        "",
        "## 文件",
        "",
        "- `01-raw-material-22-便利店奇妙夜.md` — 原材料（源文件逐字节原文，含 front matter）",
        "- `02-writing-plan.md` — 写作计划（host-authored：task + assignment + writing_plan）",
        "- `03-writer-draft.md` — Writer 初稿（production 投影，save_artifact only）",
        "- `04-editor-final.md` — Editor 成稿（同一稿的最小定向修补）",
        "- `05-diff-writer-to-final.diff` — 初稿 -> 成稿逐行 diff",
        "- `writer-context.md` — 注入 request #1 的完整 WritingContext 原文",
        "- `receipt.json` — 运行记录（fixture 身份 + 两个 pass 的 receipt 证据）",
        "",
        "## 材料身份（hash 绑定，逐字节可验）",
        "",
        f"- source_ref: `{fixture.source_ref}`",
        f"- source_sha256: `{fixture.sha256}`",
        f"- source_byte_length: {fixture.source_byte_length}",
        f"- projected_char_length: {fixture.projected_char_length}",
        f"- rights: `{fixture.rights}`（实验用途，不对外分发）",
        f"- material_id: `{fixture.material_id}`",
        "",
        "验证：`sha256sum <源文件>` 应与上面一致；WritingContext 里的 material 就是该文件",
        "逐字节原文，`writing_context.source_sha256` 记录在 receipt.json 的两次运行里。",
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
            "",
            "## 诚实声明",
            "",
            "- `examples=[]`：本轮刻意不投 exemplar，只测 Skill 能否从材料驱动写作。",
            "- 原材料含 wiki 页面 front matter 与“上一篇/下一篇”脚注，写作约束要求不引用它们。",
            "- 材料只有 1618 字符而 target_length 是 2500-3500：release_constraints 优先，",
            "  成稿短于目标长度不算失败，编造才算。",
            "- 成稿质量需要人工判断；本 README 不下结论。",
            "",
            "## 首轮实测发现（round 1，已在 prompt 层修正）",
            "",
            "- Writer 首轮把同一篇 1396 字符的稿子连存 8 次：claims 缺 `status` 字段，",
            "  ACE 判 unresolved → fact_check=false → 模型在“带 claims/空 claims”间反复",
            "  提交，从不返回 RunSummary（run 以 partial 结束，成稿本身已完整）。",
            "- Editor 首轮把 task id `sanlian-22-convenience-night` 当 article_id 提交，",
            "  ACE 报 Unknown article workspace，成稿未落盘（run 以 blocked 结束）。",
            '- 修正（host prompt 层，不改 runtime/ACE）：约束加 `status:"resolved"` 强制行；',
            "  writer/editor prompt 显式给出 workspace id 并与 task id 对比；save 成功后",
            "  必须立即返回 RunSummary。本轮实际 requests 见上。",
            "- 第二轮抓到第三个问题：模型把 save 结果里的 `canonical_path`（workspaces/…）",
            "  抄进 summary，导致 run 判 partial；第三轮起 prompt 显式要求 summary 引用",
            "  `artifacts/<run>/final.md`，且 `human_final_reviewed` 是人工标记、不报 unknown。",
        ]
    write_text(showcase / "README.md", "\n".join(lines) + "\n")


# --- run ------------------------------------------------------------------------


def run_showcase(
    *,
    fixture_path: Path,
    showcase: Path,
    techniques_path: Path,
    memory_path: Path,
    writer_limit: int,
    editor_limit: int,
    rights: str,
    check_only: bool,
) -> dict:
    fixture = load_sanlian_fixture(fixture_path, rights=rights)
    techniques = select_techniques(techniques_path)
    memory = select_memory(memory_path)
    bundle = project_writer_context(fixture, techniques, memory)
    base = "sanlian-22"
    writer_run, editor_run = f"{base}-w", f"{base}-e"
    write_showcase_inputs(showcase, fixture)
    write_text(
        showcase / "writer-context.md",
        writer_prompt(fixture, techniques, memory, writer_run) + "\n",
    )
    if check_only:
        write_readme(showcase, fixture, writer_record=None, editor_record=None)
        print(
            json.dumps(
                {
                    "status": "check passed (no model calls)",
                    "showcase": str(showcase),
                    "fixture": fixture.to_record(),
                    "technique_ids": [t["id"] for t in techniques],
                    "memory_ids": [e["id"] for e in memory],
                    "examples_projected": [],
                    "writing_plan_sections": list(WRITING_PLAN),
                    "writer_context_chars": len(render_writing_context(bundle)),
                },
                ensure_ascii=False,
                indent=2,
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
        material_path=fixture.source_path,
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=[source_entry(fixture)],
        source_sha256=fixture.sha256,
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=writer_limit,
        run_id=writer_run,
        prompt=writer_prompt(fixture, techniques, memory, writer_run),
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
        task_id=TASK["id"],
        material_path=fixture.source_path,
        title=TASK["title"],
        audience=TASK["audience"],
        assignment=TASK["assignment"],
        writing_plan=WRITING_PLAN,
        sources=[source_entry(fixture)],
        source_sha256=fixture.sha256,
        techniques=techniques,
        editorial_memory=memory,
        examples=[],
        request_limit=editor_limit,
        run_id=editor_run,
        prompt=editor_prompt(fixture, draft_text, techniques, memory, editor_run),
    )
    print(
        f"    editor: status={editor_record.get('status')} "
        f"requests={editor_record.get('model_requests')} "
        f"artifact={'yes' if editor_record.get('artifact_exists') else 'NO'}"
    )
    final_text, final_path = final_artifact_text(REPO / "workspace", editor_run)
    if not final_text:
        raise SystemExit("editor pass produced no artifact — see receipt above")

    # Step 5 of the fixture contract: bind the real ACE material ids.
    fixture = load_sanlian_fixture(
        fixture_path, rights=rights, article_id=writer_run, title=TASK["title"]
    )
    bound_editor = load_sanlian_fixture(
        fixture_path, rights=rights, article_id=editor_run, title=TASK["title"]
    )

    print("[3/3] Writing showcase ...")
    write_showcase_results(
        showcase, fixture, writer_record=writer_record, editor_record=editor_record
    )
    write_readme(
        showcase, fixture, writer_record=writer_record, editor_record=editor_record
    )
    record = {
        "status": "done",
        "showcase": str(showcase),
        "fixture": fixture.to_record(),
        "writer": writer_record,
        "editor": editor_record,
        "material_ids_bound": {
            "writer": fixture.material_id,
            "editor": bound_editor.material_id,
        },
        "writer_draft_path": draft_path,
        "editor_final_path": final_path,
    }
    print(json.dumps(record, ensure_ascii=False, indent=2, default=_json_default))
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help=f"path to the Sanlian wiki page (default: {DEFAULT_FIXTURE})",
    )
    ap.add_argument("--showcase", default=str(DEFAULT_SHOWCASE))
    ap.add_argument("--techniques-jsonl", default=str(DEFAULT_TECHNIQUES))
    ap.add_argument("--memory-jsonl", default=str(DEFAULT_MEMORY))
    ap.add_argument(
        "--rights",
        default="study-only",
        choices=("study-only", "licensed", "user-provided", "unknown"),
    )
    ap.add_argument("--writer-limit", type=int, default=8)
    ap.add_argument("--editor-limit", type=int, default=6)
    ap.add_argument(
        "--check",
        action="store_true",
        help="assemble fixture + plan + projected context ONLY, zero model calls",
    )
    args = ap.parse_args()
    run_showcase(
        fixture_path=Path(args.fixture),
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
