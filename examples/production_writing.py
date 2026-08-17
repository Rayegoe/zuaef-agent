"""Production writing path: Host-projected context, not agent pull.

The proof path (``writing_toolset.py``) lets the agent assemble its own
context by pulling materials/exemplars/knowledge/claims — a capability proof
that costs 20+ model requests per article. This module is the production
path: the HOST does deterministic context assembly ONCE, projects a single
``WritingContext`` bundle into the first request, and the agent is left with
exactly two tools:

  save_artifact          submit the complete draft + claim/source ledgers
  retrieve_more_context  optional escape hatch when the bundle is insufficient

Editorial control stays: ``EditorialControlCapability`` with the compiled
corpus evidence (seeds + ``compiled/evidence.jsonl``) may veto one save and
inject at most ``max_injections`` cognitive moves.

Nothing here invents context: materials, technique records, corpus evidence
and curated human patches come from committed assets (``curated/``,
``compiled/``, ``evidence/``) or the caller — deterministic, receipted by ACE
at save time. No new capability, no new schema, no new memory subsystem.
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

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.messages import ModelResponse, ToolCallPart
from zuaef_ace_writing.editorial import (
    EditorialControlCapability,
    EditorialEvidenceStore,
    EditorialSettings,
    run_trajectory_sensors,
)

from examples.writing_toolset import (  # reuse ACE adapters, do not duplicate
    DEFAULT_ACE_ROOT,
    ace_prepare,
    read_material_impl,
    retrieve_exemplars_impl,
    retrieve_knowledge_impl,
    save_artifact_impl,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps

BENCH = REPO / "benchmarks" / "editorial-learning"
COMPILED_EVIDENCE = BENCH / "compiled" / "evidence.jsonl"

PRODUCTION_INSTRUCTIONS = """\
You are the ZUAEF production writing agent.

Your full writing context (task, audience, material, source ledger, any
relevant techniques, editorial memory and examples) has already been
assembled by the host and is in the WritingContext block of your first
message. Do not invent, retrieve, or re-assemble context: it is all there.

Write the complete article in ONE pass, then submit it with save_artifact
along with the claim and source ledgers. If the editorial gate vetoes the
save, make the smallest useful patch and save once more — never rewrite the
whole article.

Rules:
1. Facts, numbers, quotes and scenes come only from the provided material.
2. Sources look like {"id":"S1","kind":"material","label":"...","material_ids":["M001"]}.
   Claims look like {"id":"C1","text":"...","type":"FACT","source_ids":["S1"],"status":"resolved"}.
   source_ids reference S ids, never M ids; material_ids reference M ids.
3. Never use M00x placeholders; never invent claims or sources.
4. After save_artifact, return your RunSummary with artifacts=[final.md path].
"""

# --- host-side context assembly (deterministic, no model calls) ---------------
#
# The production projection is caller-composed: Customer Context + Material +
# Writing Skill + a few Examples + optional history preference. It does NOT
# query benchmark assets — compiled/sequential_inputs.jsonl is benchmark
# authority only (see compare_paths.py for the benchmark-side join).


def prepare_writing_context(
    *,
    task_id: str,
    material: str,
    title: str = "",
    audience: str = "",
    techniques: list[dict] | None = None,
    editorial_memory: list[dict] | None = None,
    examples: list[str] | None = None,
) -> dict:
    """Deterministic host-side context bundle (the production projection).

    Everything here is passed in by the caller — no model, no benchmark
    lookup, no guessing. ``techniques``/``editorial_memory``/``examples`` are
    optional (e.g. a writing skill pack for the customer's domain); when
    absent the bundle is just task + material + ledger + constraints.
    Sources/ledger start as the single material source S1; the agent may
    extend the ledger at save time.
    """
    bundle = {
        "task": {"id": task_id, "title": title, "audience": audience},
        "material": material,
        "sources": [{"id": "S1", "kind": "material", "label": title or task_id, "material_ids": ["M001"]}],
        "techniques": [
            {
                "id": t["id"],
                "action": t["action"],
                "instruction": t["instruction"],
                "preserve": t.get("preserve", []),
                "anti_pattern": t.get("anti_pattern", []),
                "rationale": t.get("rationale", ""),
            }
            for t in (techniques or [])
        ],
        "editorial_memory": [
            {
                "id": e["id"],
                "action": e["action"],
                "directive": e["directive"],
                "rationale": e.get("rationale", ""),
                "weight": e.get("weight"),
                "approved_by": e.get("approved_by"),
                "source_ref": e.get("source_ref"),
            }
            for e in (editorial_memory or [])
        ],
        "examples": list(examples or []),
        "constraints": [
            "Facts, numbers, quotes and scenes come only from the material below.",
            "Source ledger: S1 = the material file; add S2..Sn only for other cited sources.",
            "Claim ledger: every FACT claim needs existing source_ids; no invented claims.",
            "Write the complete article in one pass, then save_artifact once.",
            "If the editorial gate vetoes, patch the smallest thing and save once more.",
        ],
    }
    return bundle


def render_writing_context(bundle: dict) -> str:
    """Project the bundle as the single WritingContext block of request #1."""
    sections = ["## WritingContext"]
    task = bundle["task"]
    sections.append(
        f"- task: {task['id']}"
        + (f" — {task['title']}" if task["title"] else "")
        + (f" (audience: {task['audience']})" if task["audience"] else "")
    )
    sections.append("\n### material")
    sections.append(bundle["material"])
    sections.append("\n### sources (ledger base)")
    sections.append(json.dumps(bundle["sources"], ensure_ascii=False, indent=2))
    if bundle["techniques"]:
        sections.append("\n### relevant techniques")
        for t in bundle["techniques"]:
            sections.append(
                f"- {t['id']} [{t['action']}]: {t['instruction']}"
                + (f"\n  anti-pattern: {', '.join(t['anti_pattern'])}" if t["anti_pattern"] else "")
            )
    if bundle["editorial_memory"]:
        sections.append("\n### relevant editorial memory")
        for e in bundle["editorial_memory"]:
            sections.append(
                f"- {e['id']} [{e['action']}] (weight {e['weight']}, {e['approved_by']}): {e['directive']}"
            )
    if bundle["examples"]:
        sections.append("\n### examples (language/technique references only, never facts)")
        for i, example in enumerate(bundle["examples"], 1):
            sections.append(f"\n<example {i}>\n{example}\n</example {i}>")
    sections.append("\n### constraints")
    for c in bundle["constraints"]:
        sections.append(f"- {c}")
    return "\n".join(sections)


# --- minimal production toolset -------------------------------------------------


class ProductionWritingToolset(FunctionToolset[CoreDeps]):
    """Default surface: save_artifact only; optional escape hatch on request.

    Deliberately NO per-tool quotas/withdrawal machinery: the host projection
    removes the need for the model to budget its own pulls (proof-path
    mechanics stay in ``BudgetedWritingToolset`` for the integration tests).

    The escape hatch (``retrieve_more_context``) is OFF by default: measured
    on deepseek-v4-flash, a model offered a fetch tool used it ~10x instead of
    writing (12 requests wasted). Material-sufficient tasks get exactly one
    tool; opt in per task only when the host bundle is genuinely thin.
    """

    def __init__(
        self,
        *,
        ace_root: Path = DEFAULT_ACE_ROOT,
        escape_hatch: bool = False,
        instructions: str = PRODUCTION_INSTRUCTIONS,
    ) -> None:
        super().__init__(instructions=instructions)
        self._ace_root = ace_root
        self._escape_hatch = escape_hatch


def build_production_toolset(
    ace_root: Path = DEFAULT_ACE_ROOT,
    *,
    escape_hatch: bool = False,
) -> ProductionWritingToolset:
    toolset = ProductionWritingToolset(ace_root=ace_root, escape_hatch=escape_hatch)

    @toolset.tool
    def save_artifact(
        ctx: RunContext[CoreDeps],
        article_id: str,
        final_markdown: str,
        claims: list[dict] | None = None,
        sources: list[dict] | None = None,
    ) -> dict:
        """Submit the complete article and evidence ledgers to ACE.

        The host projection already establishes the ledger base: when `claims`
        is omitted it is empty, and when `sources` is omitted ACE receives the
        bundle's single material source S1. ACE validates links, writes the
        canonical final.md/release.json, runs the gate, and returns hashes.
        A run snapshot is written under the ZUAEF workspace. The editorial
        gate may veto this call before it executes (bounded, see
        EditorialControlCapability)."""
        if claims is None:
            claims = []
        if sources is None:
            sources = [
                {
                    "id": "S1",
                    "kind": "material",
                    "label": article_id,
                    "material_ids": ["M001"],
                }
            ]
        result, _snapshot = save_artifact_impl(
            article_id,
            final_markdown,
            claims,
            sources,
            snapshot_dir=ctx.deps.workspace_root / "artifacts" / ctx.deps.run_id,
            run_id=ctx.deps.run_id,
            ace_root=toolset._ace_root,
        )
        return result

    if not toolset._escape_hatch:
        return toolset

    @toolset.tool
    def retrieve_more_context(
        ctx: RunContext[CoreDeps],
        article_id: str,
        material_ids: list[str] | None = None,
        query: str | None = None,
    ) -> str:
        """Escape hatch only: fetch context the host bundle did not cover.

        `material_ids` reads the raw material rows (e.g. ["M001"]); `query`
        pulls writing-technique exemplars and knowledge/evidence assets by
        lexical terms. Using this more than once per article is a design
        smell — the host projection is supposed to be sufficient."""
        parts: list[str] = []
        for material_id in material_ids or []:
            parts.append(
                read_material_impl(
                    article_id, material_id, run_id=ctx.deps.run_id, ace_root=toolset._ace_root
                )
            )
        if query:
            parts.append(
                retrieve_exemplars_impl(
                    article_id, query, run_id=ctx.deps.run_id, ace_root=toolset._ace_root
                )
            )
            parts.append(
                retrieve_knowledge_impl(
                    article_id, query, run_id=ctx.deps.run_id, ace_root=toolset._ace_root
                )
            )
        return "\n\n".join(parts) if parts else "NO ADDITIONAL CONTEXT AVAILABLE"

    return toolset


# --- agent composition -----------------------------------------------------------


def build_production_agent(
    settings: AgentSettings,
    *,
    run_id: str,
    ace_root: Path = DEFAULT_ACE_ROOT,
    evidence_path: Path | None = COMPILED_EVIDENCE,
) -> Any:
    """Production composition: minimal surface THROUGH the shared seam.

    Uses ``core.build_agent`` (the same seam as every other ZUAEF agent) with
    the generic surfaces disabled — filesystem/knowledge/planning/skills OFF,
    receipts (StepPersistence/ToolOutputLimits) ON — plus the production
    toolset and the editorial capability. Measured: a model offered
    list_directory/find_files wasted 12 requests wandering instead of writing.

    ``evidence_path`` defaults to the compiled corpus (seeds + 20
    corpus_observation records). Pass a merged file for experiments that add
    promoted human patches.
    """
    minimal = settings.with_overrides(
        enable_filesystem=False,
        enable_knowledge=False,
        enable_planning=False,
        enable_skills=False,
        enable_tool_output_limits=False,
    )
    store = (
        EditorialEvidenceStore(evidence_path)
        if evidence_path is not None
        else EditorialEvidenceStore()
    )
    capability = EditorialControlCapability(
        settings=EditorialSettings(), store=store
    )
    return build_agent(
        minimal,
        run_id=run_id,
        instructions=PRODUCTION_INSTRUCTIONS,
        extra_toolsets=[build_production_toolset(ace_root)],
        extra_capabilities=[capability],
    )


# --- run + metrics ---------------------------------------------------------------


def metrics_from_messages(messages) -> dict:
    """Model-request and tool-call counts from real run history."""
    requests = 0
    tool_calls: list[str] = []
    for message in messages:
        if isinstance(message, ModelResponse):
            requests += 1
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                tool_calls.append(getattr(part, "tool_name", "?"))
    return {
        "model_requests": requests,
        "tool_calls": len(tool_calls),
        "tool_names": tool_calls,
    }


def final_artifact_text(workspace_root: Path, run_id: str) -> tuple[str, str]:
    """The saved article (snapshot final.md), not the run summary."""
    path = Path(workspace_root) / "artifacts" / run_id / "final.md"
    if not path.is_file():
        return "", str(path)
    return path.read_text(encoding="utf-8"), str(path)


def reset_run_state(settings: AgentSettings, run_id: str) -> None:
    """Re-runnable: drop this run_id's step-store dirs, settlement receipts,
    the ACE workspace and stale snapshots so budgets/receipts start empty."""
    import shutil

    for child in settings.step_store_dir.glob(f"{run_id}*") if settings.step_store_dir.is_dir() else []:
        if child.is_dir() and (child.name == run_id or child.name.startswith(f"{run_id}-")):
            shutil.rmtree(child, ignore_errors=True)
    for root in (settings.receipt_dir, settings.state_root / "settlements"):
        for child in root.glob(f"{run_id}*") if root.is_dir() else []:
            if child.is_file():
                child.unlink()
    ace_workspace = DEFAULT_ACE_ROOT / "workspaces" / run_id
    if ace_workspace.is_dir():
        shutil.rmtree(ace_workspace)
    artifact_dir = settings.workspace_root / "artifacts" / run_id
    if artifact_dir.is_dir():
        shutil.rmtree(artifact_dir, ignore_errors=True)


def run_production_article(
    settings: AgentSettings,
    *,
    task_id: str,
    material_path: Path,
    title: str = "",
    techniques: list[dict] | None = None,
    editorial_memory: list[dict] | None = None,
    examples: list[str] | None = None,
    evidence_path: Path | None = COMPILED_EVIDENCE,
    request_limit: int = 12,
    run_id: str | None = None,
    prompt: str | None = None,
) -> dict:
    """One production article through the SHARED runtime seam (execute_run).

    Host: ingest material -> assemble WritingContext -> compose the minimal
    agent (build_agent, generic surfaces off) -> execute_run (usage limits,
    exception boundary, receipt settlement, host artifact verification).
    Returns receipt-derived evidence: status, model requests, tool effects,
    verified artifacts, signals on the real final.md.

    ``run_id``/``prompt`` overrides support multi-pass flows (e.g. the
    writer -> editor experiment in compare_paths.py).
    """
    from zuaef_agent.models import RunReceipt
    from zuaef_agent.runtime import PausedRun, execute_run

    run_id = run_id or f"prod-{task_id}"
    reset_run_state(settings, run_id)
    material = material_path.read_text(encoding="utf-8")
    # Ingest the material so save_artifact has a real source ledger (the
    # bundle's S1 must resolve to an ingested M001, or ACE rejects the save).
    ace_prepare(
        run_id,
        title=title or task_id,
        materials=[str(material_path)],
        ace_root=DEFAULT_ACE_ROOT,
    )
    agent = build_production_agent(
        settings, run_id=run_id, evidence_path=evidence_path
    )
    if prompt is None:
        bundle = prepare_writing_context(
            task_id=task_id,
            material=material,
            title=title,
            techniques=techniques,
            editorial_memory=editorial_memory,
            examples=examples,
        )
        prompt = (
            f"Write the article for task {task_id}.\n\n"
            + render_writing_context(bundle)
            + f"\n\nThe ACE article workspace id for this task is `{run_id}` — "
            "pass it as article_id to save_artifact.\n\n"
            "Write it now and save it via save_artifact."
        )
    run_settings = settings.with_overrides(request_limit=request_limit)
    outcome = execute_run(
        agent,
        CoreDeps(workspace_root=run_settings.workspace_root.resolve(), run_id=run_id),
        prompt=prompt,
        settings=run_settings,
        run_id=run_id,
        retries={"tools": 5},
    )
    if isinstance(outcome, PausedRun):
        return {
            "run_id": run_id,
            "task_id": task_id,
            "status": "paused",
            "pending_approvals": [c.tool_name for c in outcome.requests.approvals],
        }
    receipt: RunReceipt = outcome.receipt
    text, path = final_artifact_text(settings.workspace_root, run_id)
    return {
        "run_id": run_id,
        "task_id": task_id,
        "status": receipt.status,
        "summary_outcome": receipt.summary.outcome,
        "model_requests": receipt.usage.get("requests"),
        "usage": receipt.usage,
        "verified_artifacts": [v.path for v in receipt.verified_artifacts],
        "verified_tool_effects": [
            (v.tool_name, v.status) for v in receipt.verified_tool_effects
        ],
        "unresolved_effects": [
            (v.tool_name, v.status) for v in receipt.unresolved_effects
        ],
        "artifact_path": path,
        "artifact_exists": bool(text),
        "artifact_chars": len(text),
        "artifact_sha256": (
            hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
        ),
        "signals_on_artifact": run_trajectory_sensors(text) if text else {},
    }


def resolve_evidence_arg(value: str | None) -> Path | None:
    """--evidence arg -> evidence file; ABSENT -> the default compiled corpus.

    Regression: passing None through used to silently downgrade the editorial
    store to builtin seeds only, contradicting the documented default
    (seeds + compiled/evidence.jsonl).
    """
    return Path(value) if value else COMPILED_EVIDENCE


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--material", required=True, help="path to the material markdown file")
    ap.add_argument("--title", default="")
    ap.add_argument("--evidence", help="evidence jsonl path (default: compiled/evidence.jsonl)")
    args = ap.parse_args()

    settings = AgentSettings.from_env().with_overrides(
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    record = run_production_article(
        settings,
        task_id=args.task,
        material_path=Path(args.material),
        title=args.title,
        evidence_path=resolve_evidence_arg(args.evidence),
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
