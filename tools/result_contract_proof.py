"""T014A real-model proof — three domains, one Kernel (v1.2 SPEC §14).

Runs the REAL model through the REAL plugin toolsets (ace-writing,
zuaef-emtb-budget, zuaef-client-service) and settles every run through the
same generic ``execute_run`` terminal. The deliverables are materially
different (article / budget analysis / customer reply); the runtime contract
is identical (``str | DeferredToolRequests``, one receipt schema, zero domain
fields).

Mechanical only: prompts are thin task contracts, outputs land under
``workspace/artifacts/result-contract-proof/<domain>/``. No editorial
decisions, no scoring — the proof is the shape of what comes back.

Usage (from the repo root, real model credentials required):

    uv run python tools/result_contract_proof.py [--request-limit N] [--only writing|budget|client]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "plugins" / "zuaef-emtb-budget"),
    str(REPO / "plugins" / "zuaef-client-service"),
]

from zuaef_ace_writing.writing_toolset import build_writing_toolset
from zuaef_client_service.store import ClientServiceStore
from zuaef_client_service.toolset import build_client_service_toolset
from zuaef_emtb_budget.toolset import build_budget_toolset

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.providers import resolve_model
from zuaef_agent.runtime import TerminalRun, execute_run

OUT_ROOT = REPO / "workspace" / "artifacts" / "result-contract-proof"

WRITING_PROMPT = """\
客户素材（李姐提供的旧文节选，平价美甲品牌「云朵盘」）：

「今年我把美甲的标准改了：不抢眼就行。杏仁奶白、灰调豆沙、淡茶褐，这三个颜色
挂在店里最久。有客人做完水钻美甲，两周后来卸，说天天打字嫌吵。我们做平价彩妆，
对“热闹”两个字最有体会。满 99 减 20 的活动这个月还有。」

任务：把这段素材改写成一篇约 300 字的公众号短文，面向普通消费者。要求：
结论放开头；价格不要写；不虚构场景和用户评价。直接把改写好的短文作为你的
最终回复返回。"""

BUDGET_CSV = """\
科目,分类,期初预算,本期变动,期末预算,实际,币种,部门
广告投放,revenue,50000,15000,65000,62000,USD,北美
物流仓储,cogs,30000,-5000,25000,25500,USD,北美
平台佣金,revenue,12000,3000,15000,14800,USD,欧洲
售后客服,opex,8000,1000,9000,11200,USD,北美
"""

BUDGET_PROMPT = f"""\
以下是本季度 EMTB 预算 CSV：

{BUDGET_CSV}
任务：解析这份预算并给出业务分析：先列观察到的数字，再指出最重要的偏差，
最后给出含义和需要追问的问题。用你自己的话解读，金额计算交给工具。直接把
分析作为你的最终回复返回。"""

CLIENT_PROMPT = """\
当前客户消息（李姐，bound customer CASE-BEAUTY-MATRIX-001）：

「上一篇还是太像 AI 写的了，开头尤其明显。保留我之前给的背景和要求，再改一版。」

任务：先检索该客户的业务上下文，然后用中文起草一条面向客户的回复：
说明这版会怎么改、哪些约束保持不变；不要报价、不要承诺政策之外的东西。
直接把回复文本作为你的最终回复返回。"""


def _receipt_summary(outcome: TerminalRun) -> dict:
    r = outcome.receipt
    return {
        "execution_state": r.execution_state,
        "outcome": r.outcome,
        "model": r.model,
        "usage": r.usage,
        "tool_calls": [f.tool_name for f in r.tool_effect_facts],
        "bindings": r.bindings,
        "receipt_schema": type(r).__name__,
    }


def _run_domain(
    name: str,
    settings: AgentSettings,
    toolset,
    prompt: str,
) -> dict:
    run_id = uuid4().hex
    agent = build_agent(settings, run_id=run_id, extra_toolsets=[toolset])
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    outcome = execute_run(agent, deps, prompt=prompt, settings=settings, run_id=run_id)
    if not isinstance(outcome, TerminalRun):
        raise SystemExit(f"{name}: expected a terminal run, got {type(outcome).__name__}")
    out_dir = OUT_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "deliverable.md").write_text(outcome.presentation, encoding="utf-8")
    (out_dir / "receipt-summary.json").write_text(
        json.dumps(_receipt_summary(outcome), ensure_ascii=False, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    return _receipt_summary(outcome)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--request-limit", type=int, default=25)
    ap.add_argument("--only", choices=("writing", "budget", "client"), default=None)
    args = ap.parse_args()

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        request_limit=args.request_limit,
        enable_planning=False,
        enable_skills=False,
        enable_filesystem=False,
        enable_knowledge=False,
    )
    if not (settings.openai_base_url and settings.openai_api_key):
        print("PROOF: no real model credentials — refusing to fabricate evidence")
        return 1
    print(f"model: {resolve_model(settings)!r}")

    def writing() -> dict:
        return _run_domain(
            "writing", settings, build_writing_toolset(), WRITING_PROMPT
        )

    def budget() -> dict:
        return _run_domain("budget", settings, build_budget_toolset(), BUDGET_PROMPT)

    def client() -> dict:
        slice_root = Path(
            __import__("os").environ.get(
                "ZUAEF_CLIENT_SERVICE_ROOT",
                Path.home() / ".local/share/zuaef/client-service",
            )
        ).expanduser()
        store = ClientServiceStore(slice_root)
        toolset = build_client_service_toolset(
            store, plugin_id="client-service", plugin_version="0.1.0"
        )
        return _run_domain("client", settings, toolset, CLIENT_PROMPT)

    domains = {"writing": writing, "budget": budget, "client": client}
    selected = [args.only] if args.only else list(domains)
    results = {}
    for name in selected:
        print(f"--- {name} ---")
        results[name] = domains[name]()
        print(json.dumps(results[name], ensure_ascii=False, indent=2, default=str))

    schemas = {r["receipt_schema"] for r in results.values()}
    print(f"\nreceipt schemas across domains: {schemas}")
    if len(schemas) != 1:
        raise SystemExit("domains settled through DIFFERENT receipt schemas")
    print("ALL DOMAINS SETTLED THROUGH ONE GENERIC TERMINAL (str) / ONE RECEIPT SCHEMA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
