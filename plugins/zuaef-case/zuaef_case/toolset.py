"""Case toolsets — SPEC v0.3 FDE Platform §12 (Stage 2), P3B-3 T008.

Two independently deferred toolsets over one CaseStore, closure-registered
like the other slices:

CASE STATE (``build_case_state_toolset``)
- load_case_context: bounded assembly of durable field memory (goal /
  situation / policy overrides); trajectory audit only on explicit request
- update_situation: host-validated situation write (provenance enforced)
- record_case_step: append-only trajectory entry (decision/action carry run_id)

CUSTOMER DELIVERY (``build_customer_delivery_toolset``)
- save_draft: draft-and-hold outbound draft under drafts/
- send_to_customer: approval-gated marker; on resume it resolves the draft
  text — the Field Interface performs the actual surface send after the run
  settles, so the plugin stays surface-agnostic

The two surfaces are separate so progressive disclosure operates at the
state ≠ delivery boundary: ordinary Case access never exposes customer-
delivery affordances, and the delivery toolset deliberately carries no
toolset-level instructions — its semantics live in the tool docstrings,
which become model-visible only when the domain is actually discovered.

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

STATE_TOOLSET_INSTRUCTIONS = """\
Business Case state tools (FDE Layer 2): durable business context and state
for one customer/project. Tools are capabilities — they record and read Case
state; they do not prescribe a task sequence.

- This run is bound to exactly one Case by the server. Never invent or guess a
  case_id; omit the case_id parameter (or pass the bound one) and the tools
  operate on the bound Case. Any attempt on a different Case is rejected.
- load_case_context reads the case's durable field memory (goal, situation,
  policy overrides) when the bound background you were given is not enough for
  the task.
- update_situation records what you now believe about the customer/business:
  substantive (non-unknown) facts require evidence ids or a supervisor
  override, or the write is refused. The situation holds durable business
  beliefs ONLY — never run status, approval state, tool attempts or delivery
  workflow (those live in receipts and StepPersistence; attempted actions
  belong in record_case_step).
- record_case_step appends one entry to the append-only trajectory audit
  (decision/action entries carry this run's id so every step traces to a
  receipt). Trajectory is evidence for audit, not current world state.
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

    def load_case_context(
        self, case_id: str, limit: int, include_trajectory: bool
    ) -> dict[str, Any]:
        doc = self._store.load_case(case_id)
        situation = self._store.read_situation(case_id)
        overrides_path = self._store.case_dir(case_id) / "policy-overrides.md"
        overrides = (
            overrides_path.read_text(encoding="utf-8")[:4000]
            if overrides_path.is_file()
            else ""
        )
        payload: dict[str, Any] = {
            "case_id": doc.case_id,
            "goal": doc.goal,
            "status": doc.status,
            "stakeholders": doc.stakeholders,
            "situation": situation.model_dump(),
            "policy_overrides": overrides,
        }
        if include_trajectory:
            payload["trajectory_tail"] = [
                entry.model_dump()
                for entry in self._store.read_trajectory(case_id, tail=limit)
            ]
        return payload

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


def build_case_state_toolset(store: CaseStore) -> AbstractToolset[CoreDeps]:
    tools = _CaseTools(store)
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=STATE_TOOLSET_INSTRUCTIONS
    )

    @toolset.tool
    def load_case_context(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        limit: int = 20,
        include_trajectory: bool = False,
    ) -> dict:
        """Load the case's durable field memory: goal, situation, policy
        overrides. Bounded — never the whole corpus. The append-only
        trajectory (audit history of decisions/actions) is included ONLY when
        include_trajectory is true and the task explicitly needs operational
        history. Omit case_id to operate on the server-bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.load_case_context(resolved, limit, include_trajectory)

    @toolset.tool
    def update_situation(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        delta: dict | None = None,
        evidence_ids: list[str] | None = None,
        barry_override: str | None = None,
    ) -> dict:
        """Merge a delta into the case situation: durable customer/business
        beliefs only, never run/approval status or attempted actions.
        Substantive (non-unknown) facts require evidence_ids or
        barry_override; the host refuses unprovenanced writes. Omit case_id to
        operate on the server-bound Case."""
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
        """Append one audit entry to the append-only trajectory (event/
        decision/action/feedback/override/approval). decision/action entries
        carry this run's id. Recording an attempted action is evidence for
        audit — it does not make the action a durable customer belief. Omit
        case_id to operate on the server-bound Case."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.record_case_step(
            resolved, ctx.deps.run_id, kind, summary, refs or {}
        )

    return toolset


def build_customer_delivery_toolset(store: CaseStore) -> AbstractToolset[CoreDeps]:
    """Customer-delivery affordances, separated from Case state (P3B-3 T008).

    Deliberately NO toolset-level instructions: toolset instructions are
    injected into the system prompt even while the tools are deferred, so any
    delivery semantics here would prime outbound behavior during ordinary
    authoring work. The delivery contract lives in the tool docstrings, which
    the model sees only once tool search actually discovers this domain. The
    docstrings also deliberately avoid the generic word "case": a background
    query (case/situation/goal) must not light this domain up — only
    delivery-flavored terms (customer/deliver/发给客户/外发) should.
    """
    tools = _CaseTools(store)
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()

    @toolset.tool
    def save_draft(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        text: str = "",
    ) -> dict:
        """Write a customer-facing OUTBOUND draft under drafts/
        (draft-and-hold; 客户外发草稿). Nothing is sent until send_to_customer
        is approved. A working draft you show the current user is NOT an
        outbound draft — return work-in-progress as your normal reply instead.
        The server-bound business object is targeted automatically; the id
        parameter is only needed for unbound runs."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.save_draft(resolved, text)

    @toolset.tool(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def send_to_customer(
        ctx: RunContext[CoreDeps],
        case_id: str | None = None,
        draft_ref: str = "",
    ) -> dict:
        """Request sending one draft to the customer (发给客户 /
        external delivery 外发). External effect: the run pauses for human
        approval; on approval the Field Interface performs the surface send
        after the run settles. Use it ONLY when the explicit intent is to
        deliver to the customer — replying to the current user is NOT customer
        delivery and needs no delivery tool. The server-bound business object
        is targeted automatically."""
        resolved = _resolve_case_id(case_id, ctx.deps)
        tools._guard_bound(resolved, ctx.deps)
        return tools.send_to_customer(resolved, draft_ref)

    return toolset
