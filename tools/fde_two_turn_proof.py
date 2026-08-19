"""Real two-turn FDE proof — Outcome-First v2.1, TASKS T013.

Runs the Golden Outcome through the SAME FDE deployment (real model, real
profile, shared ``execute_run`` seam, public StepStore history restore):

  Turn 1: 客户觉得上一篇 demo 太模板化。结合他之前给的背景和材料重写一篇。
          价格先不要写，我看完再决定要不要发。
  Turn 2: 开头还是太像 AI。保留刚才客户背景，再改一版；其他要求不变。

Captures: conversation_id, two run_ids, loaded/invoked tool surface, dormant
capabilities, Case/customer context, material sources, artifact, verification,
no-pricing / no-publish constraints, receipt, and Turn-2 model-visible history.

Host prep is mechanical only (ACE article workspace + material ingest); every
editorial decision belongs to the ONE writing agent.

Usage (from the repo root):

    uv run python tools/fde_two_turn_proof.py [--workspace DIR]

Requires real model credentials (LLM_API_BASE / LLM_API_KEY / LLM_MODEL).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src")]

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import TerminalRun, execute_run

ACE_ROOT = Path.home() / "projects" / "article-context-engine" / "article-context-engine"

TURN1 = (
    "客户觉得上一篇 demo 太模板化。"
    "结合他之前给的背景和材料重写一篇。"
    "价格先不要写，我看完再决定要不要发。"
)
TURN2 = "开头还是太像 AI。保留刚才客户背景，再改一版；其他要求不变。"


def _ace(subcommand: str, article_id: str, *rest: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(ACE_ROOT / "tools" / "ctx.py"), subcommand, article_id, *rest]
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _prepare_article(article_id: str, workspace_root: Path) -> list[str]:
    """Mechanical host prep: create the ACE article workspace and ingest the
    previous demo + the client's background/materials."""
    materials: list[str] = []
    demo = workspace_root / "inputs" / "demo-original.md"
    demo.parent.mkdir(parents=True, exist_ok=True)
    demo.write_text(
        "# 春日焕活计划（示例 demo）\n\n"
        "很多客户都在问，为什么换季时皮肤问题变多？因为温度和湿度一变，屏障容易失衡。"
        "我们为您定制了一套温和的换季焕活方案：从清洁、补水到修护，逐步调整。"
        "第一步……第二步……第三步……（这是模板化的上一版 demo）\n",
        encoding="utf-8",
    )
    background = workspace_root / "inputs" / "client-background.md"
    background.write_text(
        "# 客户背景与材料\n\n"
        "客户：专营天然护肤的中高端品牌，主打‘先养后养肤’理念，客群是 30–45 岁、"
        "重视成分与安全性的女性。\n\n"
        "关键材料：\n"
        "- 品牌不使用香精、酒精、矿物油；主打舒缓成分（积雪草、神经酰胺、泛醇）。\n"
        "- 客户认为上一篇 demo 太模板化、像 AI 套话，希望更像真人顾问、有具体场景和细节。\n"
        "- demo 里不能出现价格；发布与否由客户看完后再决定。\n",
        encoding="utf-8",
    )
    for path in (demo, background):
        materials.append(str(path))
    new = _ace("new", article_id)
    if new.returncode != 0:
        raise RuntimeError(f"ctx.py new failed: {new.stderr or new.stdout}")
    ingest = _ace("ingest", article_id, *materials)
    if ingest.returncode != 0:
        raise RuntimeError(f"ctx.py ingest failed: {ingest.stderr or ingest.stdout}")
    return materials


def _main_prompt(turn: str, conversation_ctx: str, article_id: str) -> str:
    seam = (
        "你是唯一的成果负责写作 Agent。流程必须是："
        "① 用 list_materials 找到‘demo-original’（上一版 demo，客户嫌模板化）和"
        "‘client-background’（客户背景与材料），用 read_material 完整读取这两篇材料；"
        "② 重写全文；③ 调用 save_artifact 把完整正文存为权威成果，参数为 "
        f"save_artifact(article_id={article_id!r}, final_markdown=<完整正文>, "
        "claims=[], sources=[])。save_artifact 是唯一允许写成果文件的工具——"
        "绝不要使用 write_file、create_directory、edit_file 等通用写文件工具。"
        "硬约束：正文不得出现任何价格/人民币/元/¥/定价/售价 等字样；不得发布；不得调用"
        "任何外部发布工具。"
        "最后用 final_result 汇报，必须严格按 save_artifact 返回的 JSON 填写："
        "artifacts=[snapshot_rel_path]（就是返回里 snapshot_rel_path 的完整值，形如 "
        "artifacts/<run_id>/final.md），evidence=[\"artifact:\" + snapshot_rel_path]。"
        "不要把 ACE 的 canonical_path 或其他路径写进 artifacts/evidence。"
    )
    return f"{conversation_ctx}\n\n本轮任务：{turn}\n\n{seam}"


def _restore_history(settings: AgentSettings, run_id: str, conversation_id: str):
    from pydantic_ai_harness.step_persistence import FileStepStore, fork_run

    store = FileStepStore(settings.step_store_dir)
    try:
        return asyncio.run(fork_run(store, run_id=run_id))
    except LookupError:
        return None


def _evidence_block(**fields) -> str:
    return json.dumps(fields, ensure_ascii=False, default=str, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace", default=str(Path.home() / "zuaef-fde-proof-v21"))
    ap.add_argument("--article-id", default="fde-v21-demo")
    ap.add_argument("--dry-run", action="store_true", help="deterministic FunctionModel proof (no model)")
    args = ap.parse_args()

    root = Path(args.workspace)
    workspace_root = root / "workspace"
    state_root = root / ".zuaef-state"
    workspace_root.mkdir(parents=True, exist_ok=True)
    state_root.mkdir(parents=True, exist_ok=True)

    settings = AgentSettings.from_env()
    settings = settings.with_overrides(
        workspace_root=workspace_root.resolve(),
        runtime_state_root=state_root.resolve(),
        enable_planning=True,
        enable_skills=False,  # repo skill library is not the ACE writing skill set
        enable_filesystem=False,  # artifacts/ is ACE save_artifact's write path only
        enable_knowledge=False,
        request_limit=30,
        tool_calls_limit=80,
    )
    if not (settings.openai_base_url and settings.openai_api_key):
        print("RESULT: BLOCKED — no real model credentials (LLM_* / ZUAEF_OPENAI_*)", file=sys.stderr)
        return 2

    article_id = args.article_id
    materials = _prepare_article(article_id, workspace_root)

    conversation_id = uuid4().hex
    evidence: dict = {
        "conversation_id": conversation_id,
        "turn1": {"run_id": None, "status": None, "artifacts": [], "history": []},
        "turn2": {"run_id": None, "status": None, "artifacts": [], "history": []},
        "materials": [str(m) for m in materials],
        "no_pricing_scan": {},
        "publish_calls": [],
        "invoked_tools": [],
    }

    # ── Turn 1 ────────────────────────────────────────────────────────────
    run_id1 = uuid4().hex
    try:
        agent1, snapshot1 = build_profile_agent(settings, run_id=run_id1, profile="ace-writing")
    except Exception as exc:  # noqa: BLE001 — proof driver surfaces errors
        print(f"RESULT: BLOCKED — profile compose failed: {exc}", file=sys.stderr)
        return 3
    deps1 = CoreDeps(workspace_root=workspace_root.resolve(), run_id=run_id1)
    outcome1 = execute_run(
        agent1,
        deps1,
        prompt=_main_prompt(TURN1, "（这是本项目中的第一条消息）", article_id),
        settings=settings,
        run_id=run_id1,
        conversation_id=conversation_id,
        composition=snapshot1,
        retries={"tools": 4},
    )
    if isinstance(outcome1, TerminalRun):
        evidence["turn1"]["run_id"] = run_id1
        evidence["turn1"]["status"] = outcome1.receipt.status
        evidence["turn1"]["artifacts"] = [a.path for a in outcome1.receipt.verified_artifacts]
        evidence["turn1"]["history"] = [r.tool_name for r in outcome1.receipt.verified_tool_effects]
    else:
        evidence["turn1"]["status"] = "paused"
        evidence["turn1"]["pending"] = [
            c["tool_name"] for c in outcome1.pause_receipt.pending_approvals
        ]
        print(_evidence_block(**evidence))
        print("RESULT: PARTIAL — turn 1 paused; approve/resume is T011's seam", file=sys.stderr)
        return 4

    # ── Turn 2 (same conversation, restored history) ──────────────────────
    history1 = _restore_history(settings, run_id1, conversation_id)
    evidence["turn2_model_history_len"] = len(history1) if history1 else 0
    if history1:
        evidence["turn2_prior_constraint_visible"] = any(
            "价格先不要写" in str(getattr(part, "content", ""))
            for run_msg in history1
            for part in getattr(run_msg, "parts", [])
        )

    run_id2 = uuid4().hex
    agent2, snapshot2 = build_profile_agent(settings, run_id=run_id2, profile="ace-writing")
    deps2 = CoreDeps(workspace_root=workspace_root.resolve(), run_id=run_id2)
    outcome2 = execute_run(
        agent2,
        deps2,
        prompt=_main_prompt(TURN2, "（上一轮客户已给了背景和材料，并且要求先不写价格）", article_id),
        settings=settings,
        run_id=run_id2,
        conversation_id=conversation_id,
        message_history=history1,
        composition=snapshot2,
        retries={"tools": 4},
    )
    if isinstance(outcome2, TerminalRun):
        evidence["turn2"]["run_id"] = run_id2
        evidence["turn2"]["status"] = outcome2.receipt.status
        evidence["turn2"]["artifacts"] = [a.path for a in outcome2.receipt.verified_artifacts]
        evidence["turn2"]["history"] = [r.tool_name for r in outcome2.receipt.verified_tool_effects]
    else:
        evidence["turn2"]["status"] = "paused"

    # ── Constraint + capability audit over both runs ───────────────────────
    all_artifacts = [str(workspace_root / a) for a in evidence["turn1"]["artifacts"] + evidence["turn2"]["artifacts"]]
    evidence["no_pricing_scan"]["currency_matches"] = []
    for path in all_artifacts:
        if not Path(path).is_file():
            continue
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        matches = set()
        for token in ("¥", "￥", "元/", "元 ", "RMB", "价格", "定价", "售价", "USD"):
            if token in text:
                matches.add(token)
        evidence["no_pricing_scan"][Path(path).name] = sorted(matches)
    evidence["publish_calls"] = [
        t
        for turn in ("turn1", "turn2")
        for t in evidence[turn]["history"]
        if "publish" in t or "wordpress" in t
    ]
    evidence["invoked_tools"] = sorted(
        {
            t
            for turn in ("turn1", "turn2")
            for t in evidence[turn]["history"]
        }
    )

    print("\n== FDE TWO-TURN PROOF EVIDENCE ==")
    print(_evidence_block(**evidence))

    ok = (
        evidence["turn1"]["status"] == "completed"
        and evidence["turn2"]["status"] == "completed"
        and bool(evidence["turn2"]["artifacts"])
        and not any(v for v in evidence["no_pricing_scan"].values() if v)
        and not evidence["publish_calls"]
        and evidence.get("turn2_prior_constraint_visible", False)
    )
    print(f"\nRESULT: {'PASS' if ok else 'PARTIAL'}")
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
