"""ClientServiceToolset: the four domain tools (SPEC v0.1 §24-27).

- retrieve_client_context: bounded context assembly for one customer message
- assess_customer: deterministic structured assessment (state + evidence)
- select_response_strategy: deterministic policy decision (§30/§31/§32)
- record_interaction: human-approved interaction receipt + state update

Tools emit structured data only; the model composes natural language from the
judgment (§9: Tool -> Judgment, Model -> Expression). record_interaction is
approval-gated so a pause/resume cycle exercises the frozen-composition path
(§33 shadow flow, Gate F). Tool registration follows the shared ZUAEF pattern
(build_*_toolset factory registering closures), the same as the writing slice.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps

from .models import CustomerAssessment, CustomerState, InteractionReceipt
from .policy import decide
from .store import ClientServiceStore

_REQUEST_PATTERNS: dict[str, list[str]] = {
    "case": ["案例", "成功案例", "案例分享", "case"],
    "price": ["多少钱", "价格", "报价", "费用", "收费", "预算"],
    "platform_guarantee": ["封号", "套路化", "保证", "流量恢复", "检测率", "被判"],
    "implementation_details": ["方案", "prompt", "workflow", "怎么做", "细节", "具体", "流程", "方法"],
    "full_solution": ["整套", "完整方案", "全部流程", "整个系统", "系统搭建"],
    "technical_debate": ["模型", "工具", "agent", "技术选型", "参数"],
    "real_failure_sample": ["问题稿", "被判套路", "这篇文章", "样本", "投稿"],
    "root_cause_analysis": ["根因", "为什么", "分析原因", "原因分析", "诊断"],
    "software_outsourcing": ["外包", "开发软件", "写代码", "定制系统"],
}

_SIGNAL_PATTERNS: list[tuple[str, list[str]]] = [
    ("repeated_case_request", ["案例", "有没有", "分享"]),
    ("case_request", ["案例"]),
    ("price_sensitive", ["多少钱", "费用", "贵", "预算不高"]),
    ("long_decision_cycle", ["考虑", "想想", "研究一下"]),
    ("existing_stack_mentioned", ["软件", "系统", "自研", "poe", "llm"]),
    ("scale_disclosure", ["3000", "12000", "账号", "每日", "团队"]),
]


def _extract_requests(message: str) -> list[str]:
    matched: list[str] = []
    for request, patterns in _REQUEST_PATTERNS.items():
        if any(p.lower() in message.lower() for p in patterns):
            matched.append(request)
    return matched


def _extract_signals(message: str, state: CustomerState) -> list[str]:
    signals: list[str] = []
    for signal, patterns in _SIGNAL_PATTERNS:
        if signal in state.signals:
            continue
        if any(p.lower() in message.lower() for p in patterns):
            signals.append(signal)
    for s in state.signals:
        if s not in signals:
            signals.append(s)
    return signals


def _features(
    message: str,
    assessment: CustomerAssessment,
    state: CustomerState,
) -> dict[str, Any]:
    """Assemble the deterministic policy feature set (§13 trigger vocabulary).

    Assessment-derived request/signal features win; state-derived authority /
    budget / software_need fill in; v0.1 has no paid signal so paid=False.
    """
    features: dict[str, Any] = dict(assessment.feature)
    features.setdefault("paid", False)
    features.setdefault("authority", state.authority)
    features.setdefault("software_need", state.software_need)
    budget = state.budget if state.budget != "unknown" else assessment.budget_signal
    features.setdefault("budget", budget)
    # prior_disclosure from what the customer state records as already
    # disclosed (canonical_case.information_already_disclosed is compiled
    # into the state at install time).
    if "prior_disclosure" not in features:
        disclosed = state.disclosed
        if len(disclosed) >= 3:
            features["prior_disclosure"] = "high"
        elif len(disclosed) >= 1:
            features["prior_disclosure"] = "medium"
        else:
            features["prior_disclosure"] = "low"
    if "repeat_consulting" not in features:
        features["repeat_consulting"] = bool(
            "repeated_case_request" in assessment.signals
            or "repeated_case_request" in state.signals
        )
    if "goal" not in features:
        features["goal"] = "clear" if any(
            k in message for k in ("目标", "效果", "结果", "标准")
        ) else "unclear"
    if "asks_case" not in features:
        features["asks_case"] = "case" in assessment.signals
    if "asks_price" not in features:
        features["asks_price"] = "price_sensitive" in assessment.signals
    if "asks_full_solution" not in features:
        features["asks_full_solution"] = "full_solution" in features.get("request", [])
    if "scale_signal" not in features:
        features["scale_signal"] = (
            "very_large" if "scale_disclosure" in assessment.signals else "normal"
        )
    return features


def _next_best_action(strategy: str) -> str:
    if strategy == "QUALIFY_BEFORE_DISCLOSE":
        return "继续资格审查：确认决策链、预算与服务层级后再决定披露范围。"
    if strategy == "REQUEST_MORE_CONTEXT":
        return "先请客户描述业务目标、预期效果与当前约束，再进入建议。"
    if strategy == "PROPOSE_PAID_DIAGNOSIS":
        return "以真实样本定义小范围付费诊断，验证方法后再谈实施。"
    if strategy == "DECLINE_COMMITMENT":
        return "保持边界：不承诺平台结果、外包承接或无法兑现的交付。"
    if strategy == "QUALIFY_AUTHORITY":
        return "确认联系人权限、公司主体与预算，再做高成本售前投入。"
    if strategy == "EXPLAIN_GENERAL_DIRECTION":
        return "解释通用方向与边界，不交付完整可执行方案。"
    return strategy or "继续推进当前阶段。"


class ClientServiceToolset(FunctionToolset[CoreDeps]):
    """Run-scoped client service tools over one private slice root."""


class _ClientServiceTools:
    """Logic holder: store + plugin identity, used by the closure-registered
    tools in build_client_service_toolset."""

    def __init__(
        self,
        store: ClientServiceStore,
        *,
        plugin_id: str,
        plugin_version: str,
        domain: str,
    ) -> None:
        self._store = store
        self._plugin_id = plugin_id
        self._plugin_version = plugin_version
        self._domain = domain

    def retrieve_client_context(
        self, customer_id: str, query: str, limit: int
    ) -> dict:
        state = self._store.load_customer_state(customer_id)
        knowledge = self._store.knowledge_items()
        semantics = self._store.semantic_preferences()
        evidence = self._store.search_evidence(query, limit=limit)
        requests = _extract_requests(query)
        from .canonical import CANONICAL_POLICIES

        candidates = [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "rule_summary": p.rule_summary,
            }
            for p in CANONICAL_POLICIES
            if any(req in _policy_request_tokens(p) for req in requests)
        ]
        return {
            "customer_id": customer_id,
            "customer_state": state.model_dump(),
            "knowledge": [
                {"knowledge_id": k.knowledge_id, "statement": k.statement}
                for k in knowledge
            ],
            "semantic_refs": [
                {"preference_id": s.preference_id, "name": s.name}
                for s in semantics
            ],
            "policy_candidates": candidates,
            "evidence_refs": [
                {
                    "evidence_id": e.evidence_id,
                    "context_summary": e.context_summary,
                    "speaker": e.speaker,
                }
                for e in evidence
            ],
        }

    def assess_customer(self, customer_id: str, message: str) -> dict:
        state = self._store.load_customer_state(customer_id)
        requests = _extract_requests(message)
        signals = _extract_signals(message, state)
        if "case" in requests:
            signals.append("case_request")
        budget_signal: str = state.budget
        if any(p in message for p in ("多少钱", "费用", "贵", "预算")):
            budget_signal = (
                "low"
                if any(p in message for p in ("不高", "便宜", "预算少"))
                else "medium"
            )
        uncertainties: list[str] = []
        if state.authority == "unknown":
            uncertainties.append("decision_authority_unknown")
        if state.budget == "unknown":
            uncertainties.append("budget_unknown")
        evidence = self._store.search_evidence(message, limit=5)
        assessment = CustomerAssessment(
            customer_id=customer_id,
            stage=state.stage,
            signals=[s for s in dict.fromkeys(signals)],
            authority=state.authority,
            budget_signal=budget_signal,
            feature={
                "request": [r for r in dict.fromkeys(requests)],
                "asks_case": "case" in requests,
                "asks_price": "price" in requests,
                "asks_full_solution": "full_solution" in requests,
                "prompt_changes_failed": "prompt" in message
                and ("改" in message or "无效" in message),
                "existing_stack": any(
                    p in message.lower()
                    for p in ("软件", "系统", "自研", "poe", "llm")
                ),
                "real_failure_sample": "real_failure_sample" in requests,
                "corpus_reuse": "high" if ("母稿" in message or "复用" in message) else "low",
                "scale_signal": "very_large" if "scale_disclosure" in signals else "normal",
                "meeting_request": "线下" in message or "见面" in message or "会议" in message,
                "root_cause_unclear": "root_cause_analysis" in requests,
                "method_validated": False,
            },
            uncertainties=uncertainties,
            evidence_ids=[e.evidence_id for e in evidence],
        )
        return assessment.model_dump()

    def select_response_strategy(self, customer_id: str, assessment: dict) -> dict:
        # Strict-parse preferred; on any drift in the model's assessment dict
        # (type/extra fields), fall back to a tolerant construction so one
        # bad field cannot fail the whole deterministic decision (§26 — the
        # engine must never be blocked by cosmetic model output drift).
        try:
            parsed = CustomerAssessment.model_validate(assessment)
        except ValidationError:
            parsed = CustomerAssessment(
                customer_id=customer_id,
                signals=[str(s) for s in assessment.get("signals", [])],
                authority=(
                    assessment.get("authority")
                    if assessment.get("authority") in ("known", "unknown")
                    else "unknown"
                ),
                budget_signal=(
                    assessment.get("budget_signal", "unknown")
                    if assessment.get("budget_signal")
                    in ("low", "medium", "high", "unknown")
                    else "unknown"
                ),
                feature=dict(assessment.get("feature") or {}),
                uncertainties=[],
                evidence_ids=[str(i) for i in assessment.get("evidence_ids", [])],
            )
        state = self._store.load_customer_state(customer_id)
        features = _features("", parsed, state)
        match = decide(features)
        result = match.model_dump()
        result["customer_id"] = customer_id
        return result

    def record_interaction(
        self,
        run_id: str,
        customer_id: str,
        incoming_message: str,
        assessment: dict,
        strategy: dict,
        draft_response: str,
        final_response: str,
        human_action: str,
    ) -> dict:
        customer_state_before = self._store.load_customer_state(customer_id)
        interaction_id = f"INT-{uuid4().hex[:8]}"
        receipt = InteractionReceipt(
            interaction_id=interaction_id,
            customer_id=customer_id,
            incoming_message=incoming_message,
            customer_state_before=customer_state_before.model_dump(),
            assessment=assessment,
            matched_policies=list(strategy.get("matched_policy_ids", [])),
            strategy=strategy.get("strategy", ""),
            approval_level=strategy.get("approval_level", "R0"),
            draft_response=draft_response,
            human_action=human_action,
            final_response=final_response,
            policy_candidates=list(strategy.get("matched_policy_ids", [])),
            run_id=run_id,
            composition_id="",  # settled by the replay driver from RunReceipt
        )
        written = self._store.append_interaction(receipt)
        new_state = customer_state_before.model_copy()
        new_state.updated_from = interaction_id
        new_state.next_best_action = _next_best_action(receipt.strategy)
        self._store.write_customer_state(new_state)
        return {
            "interaction_id": interaction_id,
            "customer_id": customer_id,
            "written": True,
            "run_id": run_id,
            "path": written.get("path", ""),
            "sha256": written.get("sha256", ""),
        }


def _policy_request_tokens(policy: Any) -> list[str]:
    """Coarse lexical hint of which requests a policy speaks to."""
    summary = policy.rule_summary
    tokens: list[str] = []
    if "案例" in summary:
        tokens.append("case")
    if "价格" in summary or "报价" in summary:
        tokens.append("price")
    if "封号" in summary or "保证" in summary:
        tokens.append("platform_guarantee")
    if "Prompt" in summary or "实现" in summary or "Workflow" in summary:
        tokens.append("implementation_details")
    return tokens


def build_client_service_toolset(
    store: ClientServiceStore,
    *,
    plugin_id: str,
    plugin_version: str,
    domain: str = "beauty-content",
) -> ClientServiceToolset:
    """Build the four domain tools, closure-registered over one store."""
    tools = _ClientServiceTools(
        store, plugin_id=plugin_id, plugin_version=plugin_version, domain=domain
    )
    toolset = ClientServiceToolset(
        instructions=(
            "Client Service Decision Slice tools. "
            "retrieve_client_context assembles the minimal business context "
            "for a customer message; assess_customer produces the structured "
            "assessment (stage/signals/authority/budget); "
            "select_response_strategy returns the deterministic policy "
            "decision (strategy, allowed/restricted actions, approval level, "
            "disclosure ceiling, evidence ids). Compose natural language "
            "from the strategy — never invent a fact, a case, a price, a "
            "guarantee, or an action the policy restricts. R2/R3 decisions "
            "are drafts for human approval; record_interaction only writes "
            "after approval."
        )
    )

    @toolset.tool
    def retrieve_client_context(
        ctx: RunContext[CoreDeps],
        customer_id: str,
        query: str = "",
        limit: int = 8,
    ) -> dict:
        """Assemble the minimal business context for one customer message.

        Returns customer state, matching knowledge, semantic refs, policy
        candidates and lexical evidence refs — bounded by `limit`, never the
        whole corpus. All entries carry asset ids and provenance.
        """
        return tools.retrieve_client_context(customer_id, query, limit)

    @toolset.tool
    def assess_customer(
        ctx: RunContext[CoreDeps],
        customer_id: str,
        message: str,
    ) -> dict:
        """Produce the structured customer assessment for this message.

        Deterministic: stage/signals/authority/budget come from the stored
        customer state plus lexical message classification; every non-unknown
        judgment carries the evidence ids it traces to. Uncertainties are
        explicit — the model must not guess (SPEC §15/§48).
        """
        return tools.assess_customer(customer_id, message)

    @toolset.tool
    def select_response_strategy(
        ctx: RunContext[CoreDeps],
        customer_id: str,
        assessment: dict,
    ) -> dict:
        """Run the deterministic policy engine over the assessment.

        Returns the §30 strategy, matched policy ids, allowed/restricted
        actions, approval level (R0-R3), disclosure ceiling (D0-D5) and the
        evidence ids behind the decision. Never generates reply text.
        """
        return tools.select_response_strategy(customer_id, assessment)

    @toolset.tool(requires_approval=True)
    def record_interaction(
        ctx: RunContext[CoreDeps],
        customer_id: str,
        incoming_message: str,
        assessment: dict,
        strategy: dict,
        draft_response: str,
        final_response: str = "",
        human_action: str = "APPROVED",
    ) -> dict:
        """Record one interaction after human approval (shadow flow §33).

        Writes the InteractionReceipt under state/interactions/ and updates
        the customer state under state/customers/. Requires approval because
        it is the business history write; the pause lets an operator approve,
        edit or reject before anything is recorded.
        """
        return tools.record_interaction(
            ctx.deps.run_id,
            customer_id,
            incoming_message,
            assessment,
            strategy,
            draft_response,
            final_response,
            human_action,
        )

    return toolset
