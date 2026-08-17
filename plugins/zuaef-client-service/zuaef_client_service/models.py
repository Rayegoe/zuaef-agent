"""Typed models for the Client Service Decision Slice (SPEC v0.1 §56 Phase 1).

Every domain artifact is a typed Pydantic model: CustomerAssessment,
ResponseStrategy, CustomerState, InteractionReceipt, Policy, SemanticPreference,
KnowledgeItem, EvidenceRef. Models carry no business logic; they are the
vocabulary the store, policy engine and tools share.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Corpus assets (canonical, non-secret references)
# --------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """One private-corpus evidence record (EVD-G-*). Only ids and provenance
    fields ever cross the plugin boundary; original texts stay in slice_root."""

    evidence_id: str
    speaker: str = ""
    context_summary: str = ""
    status: str = "OBSERVED"
    source_pack_id: str = ""


class KnowledgeItem(BaseModel):
    """One canonical knowledge item (KNO-*): what is true in this business."""

    knowledge_id: str
    statement: str
    domain: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class SemanticPreference(BaseModel):
    """One semantic preference (SEM-*): how to express an already-made decision."""

    preference_id: str
    name: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Decision policy (structured form; canonical compile of the private rules)
# --------------------------------------------------------------------------

FeatureValue = bool | str | list[str]
TriggerConditions = dict[str, list[FeatureValue]]

ApprovalLevel = Literal["R0", "R1", "R2", "R3"]
DisclosureLevel = Literal["D0", "D1", "D2", "D3", "D4", "D5"]

# §30 Decision Strategy Vocabulary — closed set; extension is versioned.
ResponseStrategyName = Literal[
    "ANSWER_DIRECTLY",
    "EXPLAIN_GENERAL_DIRECTION",
    "QUALIFY_NEED",
    "QUALIFY_AUTHORITY",
    "QUALIFY_BUDGET",
    "QUALIFY_BEFORE_DISCLOSE",
    "RESTRICT_DISCLOSURE",
    "REQUEST_MORE_CONTEXT",
    "PROPOSE_PAID_DIAGNOSIS",
    "ESCALATE_TO_HUMAN",
    "DECLINE_COMMITMENT",
]

# Preferred/restricted action vocabulary (domain action surface).
ActionName = Literal[
    "clarify_decision_authority",
    "clarify_budget",
    "explain_general_direction",
    "explain_principle",
    "explain_boundary",
    "explain_tradeoff",
    "qualify_before_detail",
    "propose_paid_diagnosis",
    "collect_real_samples",
    "show_tiered_quote",
    "send_detailed_case",
    "full_case_disclosure",
    "full_implementation_plan",
    "complete_workflow",
    "custom_architecture",
    "generate_custom_solution",
    "guarantee_outcomes",
    "commit_to_contract",
    "discount_commitment",
    "promise_delivery",
    "rearchitecture",
    "push_agent_software",
    "accept_software_outsourcing",
    "full_root_cause_in_chat",
    "definitive_prescription",
    "light_due_diligence",
    "async_text_only",
    "schedule_meeting",
    "ask_business_goal",
    "focus_content_standard",
    "refocus_business_outcome",
    "define_L1_scope",
    "define_L2_scope",
    "validate_method_on_samples",
    "shorten_reply",
    "stop_proactive_education",
]


class Policy(BaseModel):
    """One deterministic decision policy (canonical compile).

    ``trigger`` maps feature conditions to a policy: every listed feature key
    must be present in the input features, and its value must be one of the
    allowed list. ``any_trigger`` is a list of alternative condition groups —
    the policy also matches when at least one group fully holds (OR semantics,
    used when several distinct situations share one rule, e.g. paired-evidence
    limits). ``preferred_actions`` / ``restricted_actions`` use the closed
    ActionName vocabulary; ``approval_level`` and ``disclosure_ceiling`` follow
    §32 / §31. ``evidence_ids`` reference the private corpus.
    """

    policy_id: str
    name: str
    rule_summary: str = ""
    trigger: TriggerConditions
    any_trigger: list[TriggerConditions] = Field(default_factory=list)
    judgment: str = ""
    strategy: ResponseStrategyName
    preferred_actions: list[ActionName] = Field(default_factory=list)
    restricted_actions: list[ActionName] = Field(default_factory=list)
    approval_level: ApprovalLevel = "R1"
    disclosure_ceiling: DisclosureLevel = "D5"
    canonical_status: str = "USER_CONFIRMED"
    confidence: str = "high"
    evidence_ids: list[str] = Field(default_factory=list)


class PolicyMatch(BaseModel):
    """Result of matching an input feature set against the policy corpus."""

    matched_policy_ids: list[str] = Field(default_factory=list)
    strategy: ResponseStrategyName
    allowed_actions: list[ActionName] = Field(default_factory=list)
    restricted_actions: list[ActionName] = Field(default_factory=list)
    approval_level: ApprovalLevel = "R0"
    disclosure_ceiling: DisclosureLevel = "D5"
    evidence_ids: list[str] = Field(default_factory=list)

    @property
    def matched_policy_count(self) -> int:
        return len(self.matched_policy_ids)


# --------------------------------------------------------------------------
# Customer state (runtime data — never in the public repo, §14/§18)
# --------------------------------------------------------------------------


class CustomerState(BaseModel):
    """Current customer state (runtime, private). Unknowns are explicit."""

    schema_version: int = 1
    customer_id: str
    stage: str = "qualification"
    authority: Literal["known", "unknown"] = "unknown"
    budget: Literal["known", "unknown"] = "unknown"
    budget_confidence: str = "unknown"
    software_need: Literal["not_now", "yes", "unknown"] = "unknown"
    signals: list[str] = Field(default_factory=list)
    disclosed: list[str] = Field(default_factory=list)
    not_disclosed: list[str] = Field(default_factory=list)
    next_best_action: str = ""
    updated_from: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class CustomerAssessment(BaseModel):
    """Structured assessment of the current message (SPEC §25).

    Non-unknown judgments must trace to at least one evidence id; model
    inference is flagged INFERRED in the caller's evidence status.
    """

    customer_id: str
    stage: str = "qualification"
    signals: list[str] = Field(default_factory=list)
    authority: Literal["known", "unknown"] = "unknown"
    budget_signal: Literal["low", "medium", "high", "unknown"] = "unknown"
    feature: dict[str, FeatureValue] = Field(default_factory=dict)
    uncertainties: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Interaction receipt (domain artifact, §28)
# --------------------------------------------------------------------------


class InteractionReceipt(BaseModel):
    """One business-layer customer interaction record (INT-*).

    Companion to the ZUAEF RunReceipt, never a replacement (§28). Written by
    record_interaction under human approval; written into slice_root/state.
    """

    schema_version: str = "1"
    interaction_id: str
    customer_id: str
    incoming_message: str = ""
    customer_state_before: dict[str, Any] = Field(default_factory=dict)
    assessment: dict[str, Any] = Field(default_factory=dict)
    matched_policies: list[str] = Field(default_factory=list)
    strategy: str = ""
    approval_level: ApprovalLevel = "R0"
    draft_response: str = ""
    human_action: Literal[
        "DRAFTED", "APPROVED", "EDITED", "REJECTED", "NOT_SENT"
    ] = "DRAFTED"
    final_response: str = ""
    preference_learned: list[str] = Field(default_factory=list)
    policy_candidates: list[str] = Field(default_factory=list)
    run_id: str = ""
    composition_id: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
