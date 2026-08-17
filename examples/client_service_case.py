"""Client Service Decision Slice — real model proof driver (SPEC v0.1 §63-65).

Runs one customer message through the ``client-service-beauty`` profile:
Profile -> Plugin Composition -> ClientServiceToolset -> private corpus ->
Customer Assessment -> Decision Policy -> Response Strategy -> Draft ->
Human Approval -> Interaction Receipt + Run Receipt.

The proof case is "有没有什么成功的案例可以分享呀？" (§64): it exercises
context retrieval, repeated-information request, unknown authority, disclosure
control, semantic preference, human approval and historical-judgment alignment
(§65 expects QUALIFY_BEFORE_DISCLOSE / clarify decision authority / R2).

The R2 record_interaction pauses; with --approve the driver resumes approved,
otherwise a human approves on the console.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import PausedRun, TerminalRun, decide, execute_run

DEFAULT_MESSAGE = "有没有什么成功的案例可以分享呀？"


def _has_credentials(settings: AgentSettings) -> bool:
    return bool(settings.openai_base_url and settings.openai_api_key) or bool(
        os.getenv("OPENAI_API_KEY")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="client-service-beauty")
    ap.add_argument("--customer-id", default="CASE-BEAUTY-MATRIX-001")
    ap.add_argument("--message", default=DEFAULT_MESSAGE)
    ap.add_argument("--approve", action="store_true", help="auto-approve an R2 pause")
    args = ap.parse_args()

    settings = AgentSettings.from_env()
    if not _has_credentials(settings):
        print("RESULT: FAIL — no real model credentials (LLM_* / ZUAEF_OPENAI_* / OPENAI_API_KEY)")
        return 2

    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(settings, run_id=run_id, profile=args.profile)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    prompt = (
        f"客户（customer_id={args.customer_id}）发来一条消息：\n{args.message}\n\n"
        "作为 Client Service Decision Slice：先用 retrieve_client_context 取最小上下文，"
        "再用 assess_customer 评估，然后 select_response_strategy 得到决策策略，"
        "依据策略给出售前草稿回复，最后用 record_interaction 记录本轮。"
        "不要发明案例、价格、承诺或策略禁止的动作；R2/R3 决策只是草稿。"
        "不要调用任何知识写入或文件写入工具：业务事实与知识只来自 "
        "retrieve_client_context 返回的私有语料；写完草稿直接 record_interaction。"
    )

    outcome = execute_run(
        agent,
        deps,
        prompt=prompt,
        settings=settings,
        run_id=run_id,
        composition=snapshot,
        retries={"tools": 5},
    )

    if isinstance(outcome, PausedRun):
        print("\n=== PAUSED for approval ===")
        print("approvals:", [c.tool_name for c in outcome.requests.approvals])
        pause_receipt = outcome.pause_receipt
        if args.approve:
            print("auto-approving (--approve)")
        else:
            answer = input("approve? [y/n] ").strip().lower()
            if answer not in ("y", "yes"):
                print("RESULT: FAIL — R2 approval denied")
                return 4
        run_id2 = uuid4().hex
        agent2, _ = build_profile_agent(settings, run_id=run_id2, profile=args.profile)
        deps2 = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id2)
        outcome = execute_run(
            agent2,
            deps2,
            settings=settings,
            run_id=run_id2,
            conversation_id=outcome.conversation_id,
            message_history=outcome.message_history,
            deferred_tool_results=decide(outcome, approve=True),
            prior_pause_receipt=pause_receipt,
            composition=snapshot,
        )

    if not isinstance(outcome, TerminalRun):
        print("RESULT: FAIL — expected TerminalRun")
        return 1

    receipt = outcome.receipt
    print("\n=== RESULT ===")
    print("status:", receipt.status)
    print("run_id:", receipt.run_id)
    print("composition:", receipt.composition.profile if receipt.composition else None,
          "| composition_id:", (receipt.composition.composition_id[:16] + '...') if receipt.composition else None)
    print("summary:", receipt.summary.outcome[:200] if receipt.summary else "")
    print("receipt file:", outcome.summary.receipt)
    print("interactions under ~/.local/share/zuaef/client-service/state/interactions/")
    return 0 if receipt.status == "completed" else 3


if __name__ == "__main__":
    sys.exit(main())
