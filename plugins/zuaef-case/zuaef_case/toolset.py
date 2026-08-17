"""Case toolset — SPEC v0.3 FDE Platform §12 (Stage 2).

Five tools over one CaseStore, closure-registered like the other slices:

- load_case_context: bounded assembly of the FDE field memory (goal /
  situation / policy overrides / trajectory tail)
- update_situation: host-validated situation write (provenance enforced)
- record_case_step: append-only trajectory entry (decision/action carry run_id)
- save_draft: draft-and-hold outbound draft under drafts/
- send_to_customer: approval-gated marker; on resume it resolves the draft
  text — the Field Interface performs the actual surface send after the run
  settles, so the plugin stays surface-agnostic

The tools never touch receipts, private corpus contents, or credentials.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.effects import EffectClass, requires_approval
from zuaef_agent.models import CoreDeps

from .models import TrajectoryEntry
from .store import CaseStore

TOOLSET_INSTRUCTIONS = """\
Business Case tools (FDE Layer 2). You are the FDE agent for this case, not a
per-message reply generator: the case goal drives every run.

- load_case_context first: goal, situation, policy overrides and recent
  trajectory are the field memory; act on them, do not re-ask what is known.
- update_situation records what you now believe; substantive (non-unknown)
  facts require evidence ids or a Barry override, or the write is refused.
- record_case_step keeps the decision trace; decision/action entries must
  carry this run's id so every step traces to a receipt.
- Customer-facing messages are draft-and-hold: save_draft, then
  send_to_customer pauses for human approval. Never invent facts, cases,
  prices, guarantees or actions the policy restricts.
"""


def _deep_merge(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class _CaseTools:
    """Logic holder: store + run identity, used by the closure-registered tools."""

    def __init__(self, store: CaseStore) -> None:
        self._store = store

    def load_case_context(self, case_id: str, limit: int) -> dict[str, Any]:
        doc = self._store.load_case(case_id)
        situation = self._store.read_situation(case_id)
        trajectory = self._store.read_trajectory(case_id, tail=limit)
        overrides_path = self._store.case_dir(case_id) / "policy-overrides.md"
        overrides = (
            overrides_path.read_text(encoding="utf-8")[:4000]
            if overrides_path.is_file()
            else ""
        )
        return {
            "case_id": doc.case_id,
            "goal": doc.goal,
            "status": doc.status,
            "stakeholders": doc.stakeholders,
            "situation": situation.model_dump(),
            "policy_overrides": overrides,
            "trajectory_tail": [entry.model_dump() for entry in trajectory],
        }

    def update_situation(
        self,
        case_id: str,
        run_id: str,
        delta: dict[str, Any],
        evidence_ids: list[str] | None,
        barry_override: str | None,
    ) -> dict[str, Any]:
        current = self._store.read_situation(case_id)
        merged_state = _deep_merge(current.state, delta)
        situation = current.model_copy(
            update={
                "state": merged_state,
                "updated_by": "barry" if barry_override else f"run:{run_id}",
                "evidence_ids": sorted(
                    set(current.evidence_ids) | set(evidence_ids or [])
                ),
                "barry_override": barry_override or current.barry_override,
            }
        )
        # Host validation: substantive facts without provenance raise here.
        stored = self._store.write_situation(situation)
        return stored.model_dump()

    def record_case_step(
        self,
        case_id: str,
        run_id: str,
        kind: str,
        summary: str,
        refs: dict[str, Any],
    ) -> dict[str, Any]:
        entry = TrajectoryEntry(
            kind=kind,  # type: ignore[arg-type] — validated by pydantic
            role="agent",
            run_id=run_id,
            summary=summary,
            refs=refs,
        )
        stored = self._store.append_trajectory_for_case(case_id, entry)
        return stored.model_dump()

    def save_draft(self, case_id: str, text: str) -> dict[str, Any]:
        target = self._store.write_draft(case_id, text)
        return {"case_id": case_id, "draft_ref": target.name, "path": str(target)}

    def send_to_customer(self, case_id: str, draft_ref: str) -> dict[str, Any]:
        name = Path(draft_ref).name
        if name != draft_ref or not name.startswith("msg-") or not name.endswith(".md"):
            raise ValueError(f"invalid draft_ref: {draft_ref!r}")
        matches = [
            path
            for path in self._store.list_drafts(case_id)
            if path.name == draft_ref
        ]
        if not matches:
            raise FileNotFoundError(
                f"draft {draft_ref!r} not found for case {case_id!r}"
            )
        text = matches[0].read_text(encoding="utf-8")
        return {"case_id": case_id, "draft_ref": draft_ref, "text": text}


def build_case_toolset(store: CaseStore) -> AbstractToolset[CoreDeps]:
    tools = _CaseTools(store)
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=TOOLSET_INSTRUCTIONS
    )

    @toolset.tool
    def load_case_context(
        ctx: RunContext[CoreDeps],
        case_id: str,
        limit: int = 20,
    ) -> dict:
        """Load the case's field memory: goal, situation, policy overrides and
        the recent trajectory tail. Bounded — never the whole corpus."""
        return tools.load_case_context(case_id, limit)

    @toolset.tool
    def update_situation(
        ctx: RunContext[CoreDeps],
        case_id: str,
        delta: dict,
        evidence_ids: list[str] | None = None,
        barry_override: str | None = None,
    ) -> dict:
        """Merge a delta into the case situation. Substantive (non-unknown)
        facts require evidence_ids or barry_override; the host refuses
        unprovenanced writes."""
        return tools.update_situation(
            case_id, ctx.deps.run_id, delta, evidence_ids, barry_override
        )

    @toolset.tool
    def record_case_step(
        ctx: RunContext[CoreDeps],
        case_id: str,
        kind: str,
        summary: str,
        refs: dict | None = None,
    ) -> dict:
        """Append one trajectory entry (event/decision/action/feedback/
        override/approval). decision/action entries carry this run's id."""
        return tools.record_case_step(
            case_id, ctx.deps.run_id, kind, summary, refs or {}
        )

    @toolset.tool
    def save_draft(
        ctx: RunContext[CoreDeps],
        case_id: str,
        text: str,
    ) -> dict:
        """Write a customer-facing draft under drafts/ (draft-and-hold).
        Nothing is sent until send_to_customer is approved."""
        return tools.save_draft(case_id, text)

    @toolset.tool(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def send_to_customer(
        ctx: RunContext[CoreDeps],
        case_id: str,
        draft_ref: str,
    ) -> dict:
        """Request sending one draft to the customer. External effect: the run
        pauses for human approval; on approval the Field Interface performs
        the surface send after the run settles."""
        return tools.send_to_customer(case_id, draft_ref)

    return toolset
