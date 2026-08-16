"""Harness-neutral Context Engine proof: ZUAEF x article-context-engine (ACE).

The test question is not "can the agent finish an article" but:

    During autonomous writing, does the agent actually pull raw material,
    writing corpus, knowledge/evidence policy, and claim validation from ACE,
    and are those deliveries traceable by receipt?

Completion here is a Harness Integration Test. Human editorial trace is an
optional post-test observation and is NOT a blocking condition.

Run isolation: every machine check reads only receipts stamped with the
current run_id. Historical receipts in the same ACE workspace never count
for this run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4

from pydantic_ai import Agent, DeferredToolRequests
from pydantic_ai_harness.step_persistence import FileStepStore, StepPersistence

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from examples.writing_toolset import (
    DEFAULT_ACE_ROOT,
    ace_prepare,
    build_writing_toolset,
    machine_ready_or_complete,
)
from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps, RunSummary
from zuaef_agent.providers import resolve_model
from zuaef_agent.runtime import (
    PausedRun,
    TerminalRun,
    execute_run,
)

WRITING_AGENT_INSTRUCTIONS = """\
You are the ZUAEF writing agent for one ACE article workspace.

Available ACE capabilities: list_materials, read_material, retrieve_exemplars,
retrieve_knowledge, check_claim, save_artifact. No generic file/knowledge/
planning/style tools exist in this run.

You own the trajectory — this is a bounded autonomous trajectory: the order
and timing of the ACE capabilities are yours (no step1 -> step2 -> step3
pipeline), but the policy constraints below are fixed. Decide when to
list/read raw materials, when to pull writing-technique exemplars for the
exact drafting problem in front of you, when to consult evidence/knowledge
policy, and when to validate claims. Follow the writing need.

Acceptance requires receipts stamped with this run's run_id showing: at
least one raw-material read, one writing-corpus exemplar pull, one
knowledge/evidence retrieval, and one claim-check capability probe.

The claim-check probe is an explicit integration canary, not a natural
writing step: after your FINAL save_artifact, call check_claim exactly once
on one real claim from your ledger with purpose="integration_probe". The
probe is NON-AUTHORITATIVE for the saved artifact: its output must never
trigger another save. Do not pre-check claims before a source ledger exists,
and do not loop on checks.

Evidence workflow: call save_artifact once with your complete draft, claims,
and source ledger; if fact_check_passed=false, fix the ledger and save exactly
once more. Do not loop. After the final save, run the probe.

The run has global request/tool budgets (enforced by ZUAEF) plus per-run
adapter caps: check_claim 8, retrieve_exemplars 6, retrieve_knowledge 4.
When a tool returns budget_exhausted it is also withdrawn from your action
space on the next step — do not attempt it again. Do not repeat the same
retrieval query; retrieve what you need, then draft.

Rules:
1. Facts, numbers, quotes and scenes come only from ingested materials.
2. Exemplars are language/technique references only, never factual sources.
3. Source records look like
   {"id":"S1","kind":"material","label":"...","material_ids":["M001"]}.
   Claim records look like
   {"id":"C1","text":"...","type":"FACT","source_ids":["S1"],"status":"resolved"}.
   source_ids reference S ids, never M ids. material_ids reference M ids.
4. Save once with save_artifact. If fact_check_passed=false, fix sources/claims
   and save exactly once more; do not loop.
5. In RunSummary.evidence put only artifact:<snapshot_rel_path>. Never invent
   tool-effect refs; the host settles completed tool effects automatically.
"""


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except JSONDecodeError:
            # A corrupt line means missing evidence, not invented evidence:
            # the acceptance checks below fail on the shortfall.
            continue
    return rows


def settle_run(
    article_id: str,
    run_id: str,
    workspace_root: Path,
    state_root: Path,
    verified: list[tuple[str, str]],
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> dict:
    """Host settlement: ACE final.md is canonical; the ZUAEF copy is the run
    snapshot. Both must hash equal and match the runtime receipt."""
    ace_root = Path(ace_root).resolve()
    workspace_root = Path(workspace_root).resolve()
    state_root = Path(state_root).resolve()
    canonical = ace_root / "workspaces" / article_id / "article" / "final.md"
    snapshot = workspace_root / "artifacts" / run_id / "final.md"
    problems: list[str] = []
    canonical_sha = None
    snapshot_sha = None
    if not canonical.is_file():
        problems.append(f"canonical artifact missing: {canonical}")
    else:
        canonical_sha = hashlib.sha256(canonical.read_bytes()).hexdigest()
    if not snapshot.is_file():
        problems.append(f"run snapshot missing: {snapshot}")
    else:
        snapshot_sha = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if canonical_sha and snapshot_sha and canonical_sha != snapshot_sha:
        problems.append(
            f"hash mismatch: canonical={canonical_sha} snapshot={snapshot_sha}"
        )
    receipt_shas = {sha for _, sha in verified}
    snapshot_rel = f"artifacts/{run_id}/final.md"
    if snapshot_sha and snapshot_rel not in {path for path, _ in verified}:
        problems.append(f"receipt did not verify snapshot as artifact: {snapshot_rel}")
    if snapshot_sha and snapshot_sha not in receipt_shas:
        problems.append("receipt sha256 for snapshot does not match settlement sha256")
    record = {
        "run_id": run_id,
        "article_id": article_id,
        "canonical_path": str(canonical),
        "snapshot_path": str(snapshot),
        "canonical_sha256": canonical_sha,
        "snapshot_sha256": snapshot_sha,
        "receipt_verified": [{"path": p, "sha256": s} for p, s in verified],
        "ok": not problems,
        "problems": problems,
        "settlement_status": "settlement_ok" if not problems else "settlement_failed",
    }
    settlements = state_root / "settlements"
    settlements.mkdir(parents=True, exist_ok=True)
    (settlements / f"{run_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return record


def build_writing_agent(
    settings: AgentSettings,
    *,
    run_id: str,
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> Agent[CoreDeps, RunSummary | DeferredToolRequests]:
    """Task-local ZUAEF composition: only ACE context tools + StepPersistence.

    Generic FileSystem/Knowledge/Planning/Skills capabilities are intentionally
    absent so the trajectory is generated by the agent's use of Context Engine
    capabilities, not by workspace exploration. ``execute_run`` still owns
    usage limits, step effects, artifact verification, and receipt settlement.
    """
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    settings.state_root.mkdir(parents=True, exist_ok=True)
    capabilities = []
    if settings.enable_step_persistence:
        capabilities.append(
            StepPersistence[CoreDeps](
                store=FileStepStore(
                    settings.step_store_dir,
                    max_snapshots_per_run=settings.max_snapshots_per_run,
                ),
                agent_name="zuaef",
                run_id=run_id,
            )
        )
    return Agent(
        resolve_model(settings),
        deps_type=CoreDeps,
        output_type=[RunSummary, DeferredToolRequests],
        instructions=WRITING_AGENT_INSTRUCTIONS,
        capabilities=capabilities,
        toolsets=[build_writing_toolset(ace_root)],
        name="zuaef",
    )


def build_prompt(article_id: str, focus: list[str], account: str) -> str:
    focus_hint = "、".join(focus) if focus else "自行从素材中判断"
    account_hint = f"账号定位：{account}。" if account else ""
    return (
        f"任务：为 article_id={article_id} 自主写一篇中文公众号技术叙事文章。{account_hint}"
        f"主题线索：{focus_hint}。"
        "ACE 里已 ingest 真实原始素材。没有预先生成的 context pack；这是有界自主轨迹"
        "（bounded autonomous trajectory）——调用时机由你决定，没有 step1→step2 固定流程，"
        "但下面列出的验收与证据规则是硬约束。\n"
        "验收事实（只认本次 run_id 的 receipt）：至少一次 read_material、"
        "一次 retrieve_exemplars、一次 retrieve_knowledge；以及一次显式 capability probe——"
        "在最终 save_artifact 之后，对 ledger 中一个真实 claim 调用 "
        "check_claim(purpose='integration_probe')。probe 是集成测试桩，不是自然写作步骤，"
        "且对已保存 artifact 非权威（non-authoritative）：probe 输出绝不触发再次 save。\n"
        "事实与引用只能来自 raw material；exemplar 只用于写作手法，绝不作为当前事实来源。\n"
        'source 记录示例：{"id":"S1","kind":"material","label":"...","material_ids":["M001"]}；'
        'claim 记录示例：{"id":"C1","text":"...","type":"FACT","source_ids":["S1"],"status":"resolved"}。'
        "source_ids 引用 S 编号，material_ids 引用 M 编号，二者不要混用。\n"
        "证据流程：先把 sources/claims 一次写全并调用 save_artifact；若 fact_check_passed=false，"
        "修复后最多再 save 一次，不要循环；最终 save 之后执行一次 probe，然后直接给最终 RunSummary。"
        "per-run 预算：check_claim 8 次、retrieve_exemplars 6 次、retrieve_knowledge 4 次；"
        "预算耗尽后该工具会从你的工具列表中被移除，不要再次调用；也不要重复同一查询。"
        "最终 RunSummary 的 artifacts/evidence 只写 save_artifact "
        "返回的 snapshot_rel_path（artifact:...），不要写任何 tool-effect 引用。\n"
        "文章标准：先有人、有世界、有时间，再有道理；成稿不应像咨询报告。"
    )


def context_usage(ace_workspace: Path, run_id: str) -> dict:
    """Receipts and claim-checks attributable to THIS run only.

    The same ACE workspace accumulates history across runs; only records
    stamped with ``run_id`` may count toward this run's acceptance."""
    receipts = [
        rec
        for rec in read_jsonl(ace_workspace / "_state" / "retrieval-receipts.jsonl")
        if str(rec.get("run_id")) == run_id
    ]
    by_exec: dict[str, list[dict]] = {}
    for rec in receipts:
        by_exec.setdefault(str(rec.get("execution_id")), []).append(rec)
    claim_checks = [
        rec
        for rec in read_jsonl(ace_workspace / "_state" / "claim-checks.jsonl")
        if str(rec.get("run_id")) == run_id
    ]
    return {
        "receipts": receipts,
        "by_execution_id": by_exec,
        "claim_checks": claim_checks,
    }


def _print_checks(title: str, checks: list[tuple[str, bool, str]]) -> bool:
    print(title)
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--article-id", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--account", default="shizuoweilai")
    ap.add_argument(
        "--materials", nargs="*", default=[], help="real material files to ingest first"
    )
    ap.add_argument(
        "--focus", nargs="*", default=[], help="topic hints for the writing task"
    )
    ap.add_argument(
        "--profile",
        default=None,
        help="compose the agent via a ZUAEF profile (plugin path) instead of "
        "the direct toolset assembly; the frozen snapshot lands in the "
        "receipt (CAP-P4) and resume stays exact",
    )
    ap.add_argument(
        "--request-limit",
        type=int,
        default=None,
        help="override AgentSettings.request_limit (the recorded proof used 22 "
        "requests; default is 12)",
    )
    args = ap.parse_args()

    settings = AgentSettings.from_env()
    if args.request_limit is not None:
        settings = settings.with_overrides(request_limit=args.request_limit)
    has_credentials = bool(
        settings.openai_base_url and settings.openai_api_key
    ) or bool(os.getenv("OPENAI_API_KEY"))
    if not has_credentials:
        print(
            "RESULT: FAIL — no real model credentials (ZUAEF_OPENAI_* / LLM_* / OPENAI_API_KEY)"
        )
        return 2

    ace_root = Path(os.environ.get("ACE_ROOT", str(DEFAULT_ACE_ROOT)))
    prep = ace_prepare(
        args.article_id,
        title=args.title,
        account=args.account,
        materials=args.materials,
        ace_root=ace_root,
    )
    print(
        f"ACE workspace ready: {ace_root}/workspaces/{args.article_id} "
        f"materials={len(prep['materials'])}"
    )

    run_id = uuid4().hex
    composition = None
    if args.profile:
        # Plugin Composition Layer path: resolve -> freeze -> compose. The
        # snapshot is threaded into the receipt so CAP-P4/P5 hold; the
        # direct-toolset path below is unchanged proof evidence (SPEC §33).
        agent, composition = build_profile_agent(
            settings, run_id=run_id, profile=args.profile
        )
    else:
        agent = build_writing_agent(settings, run_id=run_id, ace_root=ace_root)
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    outcome = execute_run(
        agent,
        deps,
        prompt=build_prompt(args.article_id, args.focus, args.account),
        settings=settings,
        run_id=run_id,
        composition=composition,
        retries={"tools": 5},
    )

    if isinstance(outcome, PausedRun):
        print(
            f"RESULT: paused — approvals pending {[c.tool_name for c in outcome.requests.approvals]}"
        )
        print(f"pause receipt: {outcome.pause_receipt.run_id}")
        return 4

    assert isinstance(outcome, TerminalRun)
    receipt = outcome.receipt
    verified = [(v.path, v.sha256) for v in receipt.verified_artifacts]
    settlement = settle_run(
        args.article_id,
        run_id,
        settings.workspace_root.resolve(),
        settings.state_root,
        verified,
        ace_root,
    )

    ace_workspace = ace_root / "workspaces" / args.article_id
    usage = context_usage(ace_workspace, run_id)
    gate_ok, gate_detail = machine_ready_or_complete(args.article_id, ace_root)
    by_exec = usage["by_execution_id"]

    def has_nonempty(execution_id: str) -> bool:
        return any(rec.get("selected_refs") for rec in by_exec.get(execution_id, []))

    material_pulls = by_exec.get("read-material", [])
    exemplar_pulls = by_exec.get("pull-exemplars", [])
    knowledge_pulls = by_exec.get("retrieve-knowledge", [])
    exemplar_hash_ok = all(rec.get("hashes") for rec in exemplar_pulls)
    exemplar_rights_ok = all(rec.get("rights_checked") for rec in exemplar_pulls)
    claim_probes = [
        rec
        for rec in usage["claim_checks"]
        if rec.get("purpose") == "integration_probe"
    ]

    machine_checks = [
        (
            "ZUAEF autonomous execution completed",
            receipt.status == "completed",
            f"receipt status={receipt.status}",
        ),
        (
            "raw material pulled during run",
            has_nonempty("read-material"),
            f"{len(material_pulls)} read-material receipt(s)",
        ),
        (
            "writing corpus pulled during run",
            has_nonempty("pull-exemplars"),
            f"{len(exemplar_pulls)} pull-exemplars receipt(s)",
        ),
        (
            "knowledge/evidence pulled during run",
            has_nonempty("retrieve-knowledge"),
            f"{len(knowledge_pulls)} retrieve-knowledge receipt(s)",
        ),
        (
            "claim-check capability probe during run",
            bool(claim_probes),
            (
                f"{len(usage['claim_checks'])} in-run check(s), "
                f"{len(claim_probes)} with purpose=integration_probe"
            ),
        ),
        (
            "exemplar receipts carry refs + hashes + rights",
            exemplar_hash_ok and exemplar_rights_ok,
            f"hash_ok={exemplar_hash_ok} rights_ok={exemplar_rights_ok}",
        ),
        (
            "ACE canonical artifact",
            settlement["canonical_sha256"] is not None,
            settlement["canonical_path"],
        ),
        (
            "snapshot hash equality + receipt match",
            settlement["ok"],
            "; ".join(settlement["problems"]) or "sha256 match",
        ),
        (
            "ACE evidence gate machine-ready or complete",
            gate_ok,
            gate_detail,
        ),
        (
            "ZUAEF receipt on disk",
            bool(outcome.summary.receipt) and Path(outcome.summary.receipt).is_file(),
            outcome.summary.receipt,
        ),
        (
            "usage recorded",
            bool(receipt.usage),
            str(receipt.usage.get("requests", "?")) + " requests",
        ),
    ]
    checks_ok = _print_checks("\n=== Harness Integration Test ===", machine_checks)
    test_complete = receipt.status == "completed" and checks_ok

    print("\n=== Observed agent trajectory (from ZUAEF tool-effect ledger) ===")
    for effect in receipt.verified_tool_effects:
        print(f"  {effect.tool_name}: {effect.status}")
    print("\n=== Context deliveries observed from ACE receipts ===")
    for rec in usage["receipts"]:
        print(
            f"  {rec.get('execution_id')}: query={rec.get('query')!r} "
            f"refs={rec.get('selected_refs')} hashes={bool(rec.get('hashes'))}"
        )
    print("\n=== Claim-check records (this run) ===")
    for rec in usage["claim_checks"]:
        print(
            f"  purpose={rec.get('purpose')} ok={rec.get('ok')} "
            f"checked={rec.get('checked')}"
        )

    print("\n=== Optional editorial observation (NOT a blocking gate) ===")
    print("  human blind edit / trace: optional; does not change TEST COMPLETE")

    print(f"\nRESULT: {'PASS' if test_complete else 'FAIL'} (run {run_id})")
    print("EVIDENCE:")
    print(f"  canonical  {settlement['canonical_path']}")
    print(f"  snapshot   {settlement['snapshot_path']}")
    print(f"  settlement {settings.state_root}/settlements/{run_id}.json")
    print(f"  receipt    {outcome.summary.receipt}")
    print(f"  ACE receipts {ace_workspace}/_state/retrieval-receipts.jsonl")

    if test_complete:
        return 0
    if receipt.status == "blocked":
        return 1
    return 3


if __name__ == "__main__":
    sys.exit(main())
