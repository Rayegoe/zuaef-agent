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

from .models import CaseError, TrajectoryEntry
from .store import CaseStore

TOOLSET_INSTRUCTIONS = """\
Business Case tools (FDE Layer 2). You are the FDE agent for this case, not a
per-message reply generator: the case goal drives every run.

- This run is bound to exactly one Case by the server. Never invent or guess
  a case_id; omit the case_id parameter (or pass the bound one) and the tools
  operate on the bound Case. Any attempt on a different Case is rejected.
- load_case_context first: goal, situation, policy overrides and recent
  trajectory are the field memory; act on them, do not re-ask what is known.
- update_situation records what you now believe; substantive (non-unknown)
  facts require evidence ids or a Barry override, or the write is refused.
- record_case_step keeps the decision trace; decision/action entries must
  carry this run's id so every step traces to a receipt.

Supervisor vs customer (identity rule):
- The user you are talking to is the SUPERVISOR (Barry), never the customer.
  Showing work to the supervisor is a normal reply, not an external effect.
- Authoring tasks (write / rewrite / revise / analyze / draft) end by
  PRESENTING the result: put the full final text in the final_result
  ``deliverable`` field and persist it with the writing domain's save_artifact.
  Do NOT call save_draft or send_to_customer for them — the supervisor asked
  to SEE the result, not to deliver it to the customer.
- save_draft prepares an OUTBOUND draft for customer delivery only. A working
  draft ≠ an outbound draft. Call save_draft / send_to_customer ONLY when the
  user's intent is explicitly to deliver to the customer ("发给客户", "把这版
  发出去", "给他看", "发到群里"); send_to_customer then pauses for human
  approval. Never invent facts, cases, prices, guarantees or actions the
  policy restricts.

Deployment capability loading (progressive disclosure — this deployment):
- Business domains beyond Case are DEFERRED: the ACE writing domain, client
  service, budget and WordPress keep their real tool schemas hidden until you
  discover them. Reveal a domain's tools by calling the ToolSearch discovery
  tool (search_tools) with task-relevant queries; load only the domain the
  task needs. Do not leave the writing domain unloaded on a writing task.
- The real customer material for a writing task lives in the ACE article named
  by situation.state.resources.ace_article_id. Once you discover the writing
  domain, read that material through its grounded tools (list_materials /
  read_material on the ace_article_id — every read is receipted) instead of
  reconstructing the article from generic file reads.
- Persist the finished article through the writing domain's save_artifact
  (host-verified artifact) and present it to the supervisor in the
  final_result ``deliverable``. Do not load WordPress (publish), budget or
  client-service unless the task explicitly needs them.

RunSummary evidence crafting (host-verified, rejects unverifiable claims):
- Claim ``artifact:<path>`` refs ONLY for the verified save_artifact snapshot
  paths (they live under ``artifacts/<run_id>/...``). Customer drafts under
  ``cases/*/drafts/*.md`` are Case state, not artifacts — do not claim them
  as artifact refs.
- ``evidence`` tool-effect ids must be the tool_call_id returned with the
  tool result (e.g. ``tool-effect:call_xxx``), never the bare tool name.
"""


def _resolve_case_id(case_id: str | None, deps: CoreDeps) -> str:
    """The bound Case is the identity anchor: when the caller omits
    ``case_id`` (or passes an explicit one), the tool operates on the bound
    Case. Unbound runs require an explicit case_id (legacy CLI behavior)."""
    resolved = case_id or deps.case_id
    if resolved is None:
        raise CaseError(
            "no case_id given and this run is not bound to a Case — pass "
            "case_id explicitly for unbound runs"
        )
    return resolved


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

    @staticmethod
    def _guard_bound(case_id: str, deps: CoreDeps) -> None:
        """Business authorization boundary (SPEC v1.0 §5.6), not prompt
        guidance: when the run is bound to a Case, every Case operation must
        target exactly that Case. Unbound CLI/test runs keep the legacy
        behavior (any case the caller names)."""
        if deps.case_id is not None and case_id != deps.case_id:
            raise CaseError(
                f"case {case_id!r} is not the bound case {deps.case_id!r} "
                "for this run — Case operations are isolated to the bound Case"
            )

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
        case_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        """Load the case's field memory: goal, situation, policy overrides and
        the recent trajectory tail. Bounded — never the whole corpus. Omit
        case_id to operate on the server-bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.load_case_context(resolved, limit)

    @toolset.tool
    def update_situation(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        delta: dict | None = None,
        evidence_ids: list[str] | None = None,
        barry_override: str | None = None,
    ) -> dict:
        """Merge a delta into the case situation. Substantive (non-unknown)
        facts require evidence_ids or barry_override; the host refuses
        unprovenanced writes. Omit case_id to operate on the bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.update_situation(
            resolved, ctx.deps.run_id, delta or {}, evidence_ids, barry_override
        )

    @toolset.tool
    def record_case_step(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        kind: str = "event",
        summary: str = "",
        refs: dict | None = None,
    ) -> dict:
        """Append one trajectory entry (event/decision/action/feedback/
        override/approval). decision/action entries carry this run's id. Omit
        case_id to operate on the bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.record_case_step(
            resolved, ctx.deps.run_id, kind, summary, refs or {}
        )

    @toolset.tool
    def save_draft(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        text: str = "",
    ) -> dict:
        """Write a customer-facing draft under drafts/ (draft-and-hold).
        Nothing is sent until send_to_customer is approved. Omit case_id to
        operate on the bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.save_draft(resolved, text)

    @toolset.tool(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def send_to_customer(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        draft_ref: str = "",
    ) -> dict:
        """Request sending one draft to the customer. External effect: the run
        pauses for human approval; on approval the Field Interface performs
        the surface send after the run settles. Omit case_id to operate on
        the bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.send_to_customer(resolved, draft_ref)

    return toolset
