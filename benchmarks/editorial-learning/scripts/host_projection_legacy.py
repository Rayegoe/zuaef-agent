"""LEGACY host-projected writing machinery — NOT production.

Writing SPEC v0.2 (§22 "删除/废弃") retires the pre-v0.2 host-projected
production contract:

    prepare_writing_context        host-authored WritingContext bundle
    render_writing_context         one-shot projection into request #1
    writing_plan / techniques      host-selected angle/outline/memory/examples
    run_production_article         one-pass host-projected writer
    build_production_agent         build_agent + extra_toolsets (not profile)

These were the old production path: the host decided angle/questions/outline/
techniques/editorial memory/examples and left the model with a save-only
surface. Under v0.2 the production driver is ``examples/production_writing.py``
(thin mechanical host + ace-writing profile + execute_run) and this module
exists ONLY so the sequential/compare experiments
(``benchmarks/editorial-learning/scripts/compare_paths.py`` and the older
``examples/sanlian_showcase.py``) keep importing the machinery they measure
against. It is neither a production path nor a proof of the v0.2 contract.

Do not use this module in new code.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.messages import ModelResponse, ToolCallPart

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(Path(__file__).resolve().parents[1] / "legacy"),
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from editorial_capability import (
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
You are the ZUAEF production writing agent (LEGACY host-projected path).

Your full writing context (task, audience, material, source ledger, any
relevant techniques, editorial memory and examples) is in the WritingContext
block of your first message. Do not invent, retrieve, or re-assemble context.

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


def prepare_writing_context(
    *,
    task_id: str,
    material: str,
    title: str = "",
    audience: str = "",
    assignment: str = "",
    writing_plan: dict | None = None,
    sources: list[dict] | None = None,
    source_sha256: str | None = None,
    techniques: list[dict] | None = None,
    editorial_memory: list[dict] | None = None,
    examples: list[str] | None = None,
) -> dict:
    """LEGACY: deterministic host-side context bundle (host projection).

    Everything here is passed in by the caller — no model, no benchmark
    lookup. ``techniques``/``editorial_memory``/``examples`` are optional;
    ``writing_plan`` is the host-authored assignment for THIS article
    (angle, questions, outline, target_length, release_constraints).

    Retired from production by Writing SPEC v0.2 — experiments only.
    """
    bundle = {
        "task": {
            "id": task_id,
            "title": title,
            "audience": audience,
            "assignment": assignment,
        },
        "writing_plan": dict(writing_plan or {}),
        "material": material,
        "source_sha256": source_sha256,
        "sources": (
            list(sources)
            if sources is not None
            else [
                {
                    "id": "S1",
                    "kind": "material",
                    "label": title or task_id,
                    "material_ids": ["M001"],
                }
            ]
        ),
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
            (
                "Source ledger: S1..Sn are the projected material files; every claim "
                "source_ids must reference these S ids, never M ids."
            ),
            "Claim ledger: every FACT claim needs existing source_ids; no invented claims.",
            'Every claim must carry "status":"resolved" — ACE rejects unresolved claims.',
            "Write the complete article in one pass, then save_artifact once.",
            "If the editorial gate vetoes, patch the smallest thing and save once more.",
        ],
    }
    return bundle


def render_writing_context(bundle: dict) -> str:
    """LEGACY: project the bundle as the single WritingContext block of request #1."""
    sections = ["## WritingContext"]
    task = bundle["task"]
    sections.append(
        f"- task: {task['id']}"
        + (f" — {task['title']}" if task["title"] else "")
        + (f" (audience: {task['audience']})" if task["audience"] else "")
    )
    if task.get("assignment"):
        sections.append(f"\n### assignment\n{task['assignment']}")
    writing_plan = bundle.get("writing_plan") or {}
    if writing_plan:
        sections.append("\n### writing plan")
        for key in (
            "angle",
            "questions",
            "outline",
            "target_length",
            "release_constraints",
        ):
            value = writing_plan.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                sections.append(f"- {key}:")
                for i, item in enumerate(value, 1):
                    sections.append(f"  {i}. {item}")
            else:
                sections.append(f"- {key}: {value}")
        for key, value in writing_plan.items():
            if key in (
                "angle",
                "questions",
                "outline",
                "target_length",
                "release_constraints",
            ):
                continue
            sections.append(f"- {key}: {value}")
    sections.append("\n### material")
    if bundle.get("source_sha256"):
        sections.append(f"(source sha256: {bundle['source_sha256']})")
    sections.append(bundle["material"])
    sections.append("\n### sources (ledger base)")
    sections.append(json.dumps(bundle["sources"], ensure_ascii=False, indent=2))
    if bundle["techniques"]:
        sections.append("\n### relevant techniques")
        for t in bundle["techniques"]:
            sections.append(
                f"- {t['id']} [{t['action']}]: {t['instruction']}"
                + (
                    f"\n  anti-pattern: {', '.join(t['anti_pattern'])}"
                    if t["anti_pattern"]
                    else ""
                )
            )
    if bundle["editorial_memory"]:
        sections.append("\n### relevant editorial memory")
        for e in bundle["editorial_memory"]:
            sections.append(
                f"- {e['id']} [{e['action']}] (weight {e['weight']}, {e['approved_by']}): {e['directive']}"
            )
    if bundle["examples"]:
        sections.append(
            "\n### examples (language/technique references only, never facts)"
        )
        for i, example in enumerate(bundle["examples"], 1):
            sections.append(f"\n<example {i}>\n{example}\n</example {i}>")
    sections.append("\n### constraints")
    for c in bundle["constraints"]:
        sections.append(f"- {c}")
    return "\n".join(sections)


class ProductionWritingToolset(FunctionToolset[CoreDeps]):
    """LEGACY default surface: save_artifact only; optional escape hatch."""

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
        """Submit the complete article and evidence ledgers to ACE (LEGACY path)."""
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
        """Escape hatch only: fetch context the host bundle did not cover."""
        parts: list[str] = []
        for material_id in material_ids or []:
            parts.append(
                read_material_impl(
                    article_id,
                    material_id,
                    run_id=ctx.deps.run_id,
                    ace_root=toolset._ace_root,
                )
            )
        if query:
            parts.append(
                retrieve_exemplars_impl(
                    article_id,
                    query,
                    run_id=ctx.deps.run_id,
                    ace_root=toolset._ace_root,
                )
            )
            parts.append(
                retrieve_knowledge_impl(
                    article_id,
                    query,
                    run_id=ctx.deps.run_id,
                    ace_root=toolset._ace_root,
                )
            )
        return "\n\n".join(parts) if parts else "NO ADDITIONAL CONTEXT AVAILABLE"

    return toolset


def build_production_agent(
    settings: AgentSettings,
    *,
    run_id: str,
    ace_root: Path = DEFAULT_ACE_ROOT,
    evidence_path: Path | None = COMPILED_EVIDENCE,
) -> Any:
    """LEGACY composition: minimal surface through core.build_agent.

    Retired from production (Writing SPEC v0.2 §21/§22): the production path
    is now ``build_profile_agent("ace-writing")``. Kept for the sequential /
    compare experiments only.
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
    capability = EditorialControlCapability(settings=EditorialSettings(), store=store)
    return build_agent(
        minimal,
        run_id=run_id,
        instructions=PRODUCTION_INSTRUCTIONS,
        extra_toolsets=[build_production_toolset(ace_root)],
        extra_capabilities=[capability],
    )


def reset_run_state(settings: AgentSettings, run_id: str) -> None:
    """LEGACY helper kept for experiment scripts that clean per-run state."""
    import shutil

    for child in (
        settings.step_store_dir.glob(f"{run_id}*")
        if settings.step_store_dir.is_dir()
        else []
    ):
        if child.is_dir() and (
            child.name == run_id or child.name.startswith(f"{run_id}-")
        ):
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
    material_paths: list[Path] | None = None,
    title: str = "",
    audience: str = "",
    assignment: str = "",
    writing_plan: dict | None = None,
    sources: list[dict] | None = None,
    source_sha256: str | None = None,
    techniques: list[dict] | None = None,
    editorial_memory: list[dict] | None = None,
    examples: list[str] | None = None,
    evidence_path: Path | None = COMPILED_EVIDENCE,
    request_limit: int = 12,
    run_id: str | None = None,
    prompt: str | None = None,
) -> dict:
    """LEGACY: one host-projected article through the SHARED runtime seam.

    Retired from production (Writing SPEC v0.2 §22) — experiments only.
    """
    from zuaef_agent.models import RunReceipt
    from zuaef_agent.runtime import PausedRun, execute_run

    run_id = run_id or f"prod-{task_id}"
    reset_run_state(settings, run_id)
    paths = material_paths if material_paths is not None else [material_path]
    ace_prepare(
        run_id,
        title=title or task_id,
        materials=[str(p) for p in paths],
        ace_root=DEFAULT_ACE_ROOT,
    )
    agent = build_production_agent(settings, run_id=run_id, evidence_path=evidence_path)
    if prompt is None:
        material = material_path.read_text(encoding="utf-8")
        bundle = prepare_writing_context(
            task_id=task_id,
            material=material,
            title=title,
            audience=audience,
            assignment=assignment,
            writing_plan=writing_plan,
            sources=sources,
            source_sha256=source_sha256,
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
    record = {
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
    if source_sha256:
        record["writing_context"] = {"source_sha256": source_sha256}
    return record


def resolve_evidence_arg(value: str | None) -> Path | None:
    """--evidence arg -> evidence file; ABSENT -> the default compiled corpus."""
    return Path(value) if value else COMPILED_EVIDENCE


def final_artifact_text(workspace_root: Path, run_id: str) -> tuple[str, str]:
    """The saved article (snapshot final.md), not the run summary.

    Duplicated here so experiment scripts do not need to import the new thin
    driver (which keeps its own copy)."""
    path = Path(workspace_root) / "artifacts" / run_id / "final.md"
    if not path.is_file():
        return "", str(path)
    return path.read_text(encoding="utf-8"), str(path)


def metrics_from_messages(messages) -> dict:
    """Model-request and tool-call counts from real run history (experiment use)."""
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