"""v1.1 Capability Proof Gate driver (spec/capability-proof-gate.md).

Runs the single acceptance slice against a REAL model:
  A. research -> report artifact + evidence-backed knowledge -> approval pause -> approve continuation
  B. approval pause -> deny continuation (no side effect)
  C. controlled failure through the public runtime -> receipt (usage boundary)
  D. constructed `started`-without-settled effect -> blocked + unresolved_effect

TestModel/FunctionModel are never used here. Missing real credentials make the
Gate fail explicitly (Assumptions in spec/SPEC.md).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from examples.research_toolset import (
    DEFAULT_MARKER_ROOT,
    DEFAULT_SOURCE,
    build_research_toolset,
    build_state_proof_toolset,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps, RunSummary
from zuaef_agent.runtime import (
    PausedRun,
    TerminalRun,
    decide,
    execute_run,
    finalize_terminal,
)

GATE_WORKSPACE = PROJECT_ROOT / "workspace"
REPORT = GATE_WORKSPACE / "artifacts" / "report.md"
KNOWLEDGE_HINT = "concepts/outcome-lock"


def _compose(settings: AgentSettings, run_id: str):
    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=[build_research_toolset(DEFAULT_SOURCE), build_state_proof_toolset(DEFAULT_MARKER_ROOT)],
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    return agent, deps


def _check(results: list[tuple[str, bool, str]]) -> bool:
    ok = True
    for name, passed, detail in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        ok = ok and passed
    return ok


def scenario_a_approve(settings: AgentSettings) -> list[tuple[str, bool, str]]:
    print("\n=== Scenario A: research -> pause -> approve -> verified terminal ===")
    if REPORT.exists():
        REPORT.unlink()
    for stale in (GATE_WORKSPACE / "knowledge").rglob("*.md"):
        if stale.name != "index.md" and KNOWLEDGE_HINT in str(stale):
            stale.unlink()

    run_id = uuid4().hex
    agent, deps = _compose(settings, run_id)
    prompt = (
        "Research the local engineering guide with the research tools. First list sections, then read exactly "
        "these two sections and no others: '3. 第一原则：先设计 Outcome，而不是 Agent' and "
        "'7. 一个 Tool 必须满足“模型决策必要性”'. After those two reads, stop researching and write. "
        "You may call list_knowledge once to satisfy the knowledge pre-write check. Do not call read_file, "
        "list_directory, search_knowledge, or any other read tool. The exact source locator is "
        f"'{DEFAULT_SOURCE}'. "
        "Produce artifacts/report.md summarizing 5 real findings with section references. "
        f"Write one evidence-backed knowledge node (doc_type=concept, id like {KNOWLEDGE_HINT}, sources pointing at the guide file). "
        "Finish by calling publish_digest with a one-line digest. "
        "In your final summary, claim artifact and knowledge evidence refs. The host settles publish_digest "
        "from its effect ledger; do not invent or copy a tool-effect id into the summary."
    )
    outcome = execute_run(agent, deps, prompt=prompt, settings=settings, run_id=run_id)

    if not isinstance(outcome, PausedRun):
        return [("A pause", False, f"expected PausedRun, got {type(outcome).__name__}")]
    pause_receipt_path = settings.state_root / "receipts" / f"{outcome.pause_receipt.run_id}.json"
    expected_marker = DEFAULT_MARKER_ROOT / f"external-effect-{outcome.conversation_id}.marker"
    results = [
        ("A paused with requests", bool(outcome.requests.approvals), f"approvals={[c.tool_name for c in outcome.requests.approvals]}"),
        ("A pause receipt state", outcome.pause_receipt.state == "paused", f"state={outcome.pause_receipt.state}"),
        ("A pause receipt written", pause_receipt_path.is_file(), str(pause_receipt_path)),
        ("A marker not yet written", not expected_marker.exists(), str(expected_marker)),
    ]

    run_id2 = uuid4().hex
    agent2, deps2 = _compose(settings, run_id2)
    outcome2 = execute_run(
        agent2,
        deps2,
        settings=settings,
        run_id=run_id2,
        conversation_id=outcome.conversation_id,
        message_history=outcome.message_history,
        deferred_tool_results=decide(outcome, approve=True),
        prior_pause_receipt=outcome.pause_receipt,
    )
    if not isinstance(outcome2, TerminalRun):
        return results + [("A terminal", False, f"expected TerminalRun, got {type(outcome2).__name__}")]

    receipt = outcome2.receipt
    results += [
        ("A report verified", bool(receipt.verified_artifacts), f"artifacts={[a.path for a in receipt.verified_artifacts]}"),
        ("A report on disk", REPORT.is_file(), str(REPORT)),
        ("A knowledge verified", bool(receipt.verified_knowledge), f"knowledge={receipt.verified_knowledge}"),
        ("A settled tool-effect", any(e.tool_name == "publish_digest" and e.status == "completed" for e in receipt.verified_tool_effects), f"effects={[ (e.tool_name, e.status) for e in receipt.verified_tool_effects]}"),
        ("A marker exists", expected_marker.is_file(), str(expected_marker)),
        ("A conversation preserved", receipt.conversation_id == outcome.conversation_id, f"conv={receipt.conversation_id}"),
        ("A new run id", receipt.run_id != outcome.pause_receipt.run_id, f"{outcome.pause_receipt.run_id} -> {receipt.run_id}"),
        ("A status terminal", receipt.status == "completed", f"status={receipt.status} degraded={receipt.degraded}"),
        ("A no unresolved effects", not receipt.unresolved_effects, f"unresolved={receipt.unresolved_effects}"),
        ("A receipt usage complete", receipt.usage_complete, f"usage={receipt.usage}"),
    ]
    return results


def scenario_b_deny(settings: AgentSettings) -> list[tuple[str, bool, str]]:
    print("\n=== Scenario B: pause -> deny (no side effect) ===")
    run_id = uuid4().hex
    agent, deps = _compose(settings, run_id)
    prompt = "Call publish_digest with digest 'should-be-denied' and then finish."
    outcome = execute_run(agent, deps, prompt=prompt, settings=settings, run_id=run_id)
    if not isinstance(outcome, PausedRun):
        return [("B pause", False, f"expected PausedRun, got {type(outcome).__name__}")]

    before = {p.name for p in DEFAULT_MARKER_ROOT.glob("*.marker")}
    run_id2 = uuid4().hex
    agent2, deps2 = _compose(settings, run_id2)
    outcome2 = execute_run(
        agent2,
        deps2,
        settings=settings,
        run_id=run_id2,
        conversation_id=outcome.conversation_id,
        message_history=outcome.message_history,
        deferred_tool_results=decide(outcome, approve=False, message="operator denied this digest"),
        prior_pause_receipt=outcome.pause_receipt,
    )
    if not isinstance(outcome2, TerminalRun):
        return [("B terminal", False, f"expected TerminalRun, got {type(outcome2).__name__}")]
    after = {p.name for p in DEFAULT_MARKER_ROOT.glob("*.marker")}
    return [
        ("B denied: no new marker", after == before, f"before={sorted(before)} after={sorted(after)}"),
        ("B receipt written", Path(outcome2.summary.receipt).is_file(), str(outcome2.summary.receipt)),
        ("B conversation preserved", outcome2.receipt.conversation_id == outcome.conversation_id, outcome2.receipt.conversation_id),
    ]


def scenario_c_failure_receipt(settings: AgentSettings) -> list[tuple[str, bool, str]]:
    print("\n=== Scenario C: controlled failure through the public runtime ===")
    tight = settings.with_overrides(total_tokens_limit=1)
    run_id = uuid4().hex
    agent, deps = _compose(tight, run_id)
    outcome = execute_run(agent, deps, prompt="Research the guide and write report.md", settings=tight, run_id=run_id)
    if not isinstance(outcome, TerminalRun):
        return [("C terminal", False, f"expected TerminalRun, got {type(outcome).__name__}")]
    receipt = outcome.receipt
    return [
        ("C failure receipt status", receipt.status in ("partial", "blocked"), f"status={receipt.status}"),
        ("C identity recorded", bool(receipt.run_id and receipt.conversation_id), f"run={receipt.run_id}"),
        ("C error summary present", bool(receipt.error or receipt.summary.unknowns), f"error={(receipt.error or '')[:80]}"),
        ("C settled usage retained", bool(receipt.usage) and receipt.usage.get("requests", 0) >= 1, f"usage={receipt.usage}"),
        ("C receipt on disk", Path(outcome.summary.receipt).is_file(), str(outcome.summary.receipt)),
    ]


def scenario_d_unresolved(settings: AgentSettings) -> list[tuple[str, bool, str]]:
    print("\n=== Scenario D: constructed started-without-settled effect ===")
    run_id = uuid4().hex
    ledger_dir = settings.step_store_dir / run_id
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "tool_effects.jsonl").write_text(
        json.dumps(
            {
                "tool_call_id": "gate_unresolved",
                "tool_name": "publish_digest",
                "run_id": run_id,
                "status": "started",
                "started_at": datetime.now(UTC).isoformat(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcome = finalize_terminal(
        RunSummary(status="completed", outcome="claims success", artifacts=[], evidence=[]),
        settings=settings,
        run_id=run_id,
        conversation_id=f"gate-{run_id}",
        model_label="gate-construct",
        started_at=datetime.now(UTC),
        usage={},
        snapshot={},
    )
    receipt = outcome.receipt
    return [
        ("D blocked", receipt.status == "blocked", f"status={receipt.status}"),
        ("D unresolved_effect recorded", any(e.tool_call_id == "gate_unresolved" for e in receipt.unresolved_effects), f"unresolved={[e.tool_call_id for e in receipt.unresolved_effects]}"),
    ]


def main() -> int:
    print("v1.1 Capability Proof Gate")
    print(f"source: {DEFAULT_SOURCE}")
    print(f"marker root: {DEFAULT_MARKER_ROOT}")

    settings = AgentSettings.from_env()
    model_label = settings.compat_model if settings.openai_base_url else settings.model
    has_credentials = bool(settings.openai_base_url and settings.openai_api_key) or bool(
        os.getenv("OPENAI_API_KEY")
    )
    if not has_credentials:
        print("\nRESULT: FAIL — no real model credentials (OPENAI_API_KEY or ZUAEF_OPENAI_*)")
        print("Per spec/SPEC.md Assumptions the Gate fails explicitly rather than faking with TestModel.")
        return 2

    print(f"model: {model_label}")
    all_results: list[tuple[str, bool, str]] = []
    all_results += scenario_a_approve(settings)
    all_results += scenario_b_deny(settings)
    all_results += scenario_c_failure_receipt(settings)
    all_results += scenario_d_unresolved(settings)

    print("\n=== Gate verdict ===")
    ok = _check(all_results)
    print("RESULT:", "PASS — Stage A complete, stop here" if ok else "FAIL")
    print("EVIDENCE: receipts under", settings.state_root / "receipts")
    print("NEXT: inspect report/knowledge/receipts manually (pass/stop rule)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
