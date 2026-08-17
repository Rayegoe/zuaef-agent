"""Cognitive Editorial Control capability for ACE Writing.

The capability does not write the article and does not own taste as a static prompt.
It applies bounded, provenance-bearing directional pressure across the PydanticAI
agent loop:

1. dynamic instructions expose the current editorial intervention to the next request;
2. model-response hooks observe long-form drift and prepare the next intervention;
3. tool-result hooks learn which writing context has actually been observed;
4. save_artifact is gated before execution and may receive one bounded ModelRetry.

The existing ACE writing toolset remains untouched.
"""

from __future__ import annotations

import hashlib
import math
import re
import statistics
from dataclasses import dataclass, field, replace
from typing import Any

from pydantic_ai import ModelRequestContext, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.tools import ToolDefinition

from zuaef_agent.models import CoreDeps

from .editorial_evidence import (
    CognitiveAction,
    EditorialEvidence,
    EditorialEvidenceStore,
    TrajectorySignalName,
)


@dataclass(frozen=True)
class EditorialSignal:
    name: TrajectorySignalName
    severity: float
    detail: str


@dataclass(frozen=True)
class EditorialIntervention:
    action: CognitiveAction
    directive: str
    rationale: str
    evidence_ids: tuple[str, ...]
    trigger_signals: tuple[TrajectorySignalName, ...]


@dataclass(frozen=True)
class EditorialDraftDecision:
    veto: bool
    signals: tuple[EditorialSignal, ...]
    intervention: EditorialIntervention | None


@dataclass
class EditorialRunState:
    model_requests: int = 0
    interventions_emitted: int = 0
    save_vetoes: int = 0
    context_tags: set[str] = field(default_factory=lambda: {"nonfiction"})
    last_signals: tuple[EditorialSignal, ...] = ()
    pending: EditorialIntervention | None = None
    last_veto_hash: str | None = None


_TEMPLATE_MARKERS = (
    "首先",
    "其次",
    "再次",
    "最后",
    "综上",
    "总的来说",
    "总而言之",
    "值得注意的是",
    "不难发现",
    "可以看出",
    "在这个过程中",
    "与此同时",
    "从这个角度来看",
)

_SUMMARY_MARKERS = (
    "这意味着",
    "这说明",
    "由此可见",
    "因此可以看出",
    "归根结底",
    "换句话说",
    "本质上",
    "说到底",
)

_ABSTRACT_MARKERS = (
    "趋势",
    "逻辑",
    "价值",
    "意义",
    "体系",
    "模式",
    "生态",
    "能力",
    "认知",
    "增长",
    "转型",
    "升级",
    "赋能",
    "赛道",
    "闭环",
    "方法论",
)


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def detect_trajectory(text: str) -> tuple[EditorialSignal, ...]:
    """Cheap structural sensors, not a taste oracle.

    Sensors only decide *when to consult approved editorial evidence*. They are not
    themselves the style standard.
    """

    if len(text.strip()) < 400:
        return ()

    paragraphs = _paragraphs(text)
    para_count = max(1, len(paragraphs))
    signals: list[EditorialSignal] = []

    template_hits = sum(text.count(marker) for marker in _TEMPLATE_MARKERS)
    if template_hits >= 3:
        severity = min(1.0, 0.55 + 0.12 * (template_hits - 2))
        signals.append(
            EditorialSignal(
                "template_connectors",
                severity,
                f"{template_hits} template-like connective markers across {para_count} paragraphs",
            )
        )

    summary_hits = sum(text.count(marker) for marker in _SUMMARY_MARKERS)
    if summary_hits >= 2:
        severity = min(1.0, 0.60 + 0.14 * (summary_hits - 1))
        signals.append(
            EditorialSignal(
                "summary_pressure",
                severity,
                f"{summary_hits} explicit interpretation/summary markers",
            )
        )

    if len(paragraphs) >= 5:
        lengths = [len(p) for p in paragraphs if len(p) >= 20]
        if len(lengths) >= 5 and statistics.mean(lengths) > 0:
            cv = statistics.pstdev(lengths) / statistics.mean(lengths)
            if cv < 0.24:
                severity = min(1.0, 0.72 + (0.24 - cv))
                signals.append(
                    EditorialSignal(
                        "uniform_paragraphs",
                        severity,
                        f"paragraph-length coefficient of variation is only {cv:.2f}",
                    )
                )

    # Concrete anchors are intentionally conservative: quotes, numbers, explicit
    # clock/calendar forms, and direct-speech punctuation. This does not declare
    # prose without them "bad"; it only opens an evidence lookup.
    if len(text) >= 1200:
        quote_pairs = min(text.count("“"), text.count("”")) + text.count('"') // 2
        numbers = len(re.findall(r"\d+(?:\.\d+)?", text))
        time_marks = len(
            re.findall(
                r"(?:\d{1,2}[:：]\d{2})|(?:\d{2,4}年)|(?:\d{1,2}月)|(?:\d{1,2}日)",
                text,
            )
        )
        anchors = quote_pairs + numbers + time_marks
        if anchors <= 3:
            severity = 0.78 if len(text) >= 1800 else 0.68
            signals.append(
                EditorialSignal(
                    "low_concrete_anchor_density",
                    severity,
                    f"only {anchors} quote/number/time anchors in {len(text)} characters",
                )
            )

    abstract_hits = sum(text.count(marker) for marker in _ABSTRACT_MARKERS)
    abstract_per_k = abstract_hits / max(1.0, len(text) / 1000.0)
    if abstract_hits >= 8 and abstract_per_k >= 7.0:
        severity = min(0.82, 0.58 + (abstract_per_k - 7.0) * 0.025)
        signals.append(
            EditorialSignal(
                "abstract_noun_density",
                severity,
                f"{abstract_per_k:.1f} tracked abstract markers per 1000 characters",
            )
        )

    return tuple(sorted(signals, key=lambda signal: -signal.severity))


def _extract_long_text(response: ModelResponse) -> str:
    chunks: list[str] = []
    for part in response.parts:
        if isinstance(part, TextPart):
            chunks.append(part.content)
    return "\n".join(chunks).strip()


def _tool_names(response: ModelResponse) -> set[str]:
    return {
        part.tool_name
        for part in response.parts
        if isinstance(part, ToolCallPart)
    }


@dataclass
class EditorialControlCapability(AbstractCapability[CoreDeps]):
    """Cross-cutting writing control that nudges generation instead of rewriting it."""

    evidence_store: EditorialEvidenceStore
    max_injections: int = 4
    max_save_vetoes: int = 1
    evidence_limit: int = 3
    veto_threshold: float = 1.50
    temperature_nudge: float = 0.0
    base_temperature: float | None = None
    _state: EditorialRunState = field(default_factory=EditorialRunState, repr=False)

    async def for_run(
        self, ctx: RunContext[CoreDeps]
    ) -> "EditorialControlCapability":
        # Capability instances may be shared by an Agent across runs. Never share
        # editorial trajectory state across customers/articles/runs.
        return replace(self, _state=EditorialRunState())

    def get_instructions(self):
        def _instructions(ctx: RunContext[CoreDeps]) -> str:
            base = (
                "[Editorial control]\n"
                "Do not optimize for one-pass completion or imitate a fixed template. "
                "Preserve source truth. Treat editorial interventions as local cognitive "
                "moves, not wording to copy. Never invent reported scenes, quotations, "
                "memories, or facts. Prefer the smallest useful change over a full rewrite."
            )
            pending = self._state.pending
            if pending is None:
                return base
            return (
                f"{base}\n"
                f"Current cognitive move: {pending.action}\n"
                f"Direction: {pending.directive}\n"
                f"Why now: {pending.rationale}\n"
                f"Editorial evidence refs: {', '.join(pending.evidence_ids)}"
            )

        return _instructions

    async def before_model_request(
        self,
        ctx: RunContext[CoreDeps],
        request_context: ModelRequestContext,
    ) -> ModelRequestContext:
        self._state.model_requests += 1

        # Temperature control is deliberately opt-in. Semantic pressure from evidence
        # is the default; provider/model sampling behavior is not assumed.
        if self.temperature_nudge == 0:
            return request_context

        pending = self._state.pending
        if pending is None:
            return request_context

        settings = dict(request_context.model_settings or {})
        current = settings.get("temperature", self.base_temperature)
        if current is None:
            return request_context

        exploratory = pending.action in {"shift_perspective", "break_trajectory"}
        direction = 1.0 if exploratory else -0.5
        settings["temperature"] = max(
            0.0, min(2.0, float(current) + self.temperature_nudge * direction)
        )
        request_context.model_settings = settings
        return request_context

    async def after_model_request(
        self,
        ctx: RunContext[CoreDeps],
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        tool_names = _tool_names(response)
        if "read_material" in tool_names or "list_materials" in tool_names:
            self._state.context_tags.add("grounded")
        if "retrieve_exemplars" in tool_names:
            self._state.context_tags.add("technique_reference_used")
        if "retrieve_knowledge" in tool_names:
            self._state.context_tags.add("evidence_policy_used")

        text = _extract_long_text(response)
        if len(text) >= 600:
            self._update_from_text(ctx, text)

        return response

    async def after_tool_execute(
        self,
        ctx: RunContext[CoreDeps],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
        result: Any,
    ) -> Any:
        if tool_def.name == "read_material":
            self._state.context_tags.update({"grounded", "material_observed"})
            self._prepare_proactive_intervention(ctx)
        elif tool_def.name == "retrieve_exemplars":
            self._state.context_tags.update({"drafting", "technique_reference_used"})
            self._prepare_proactive_intervention(ctx)
        elif tool_def.name == "retrieve_knowledge":
            self._state.context_tags.add("evidence_policy_used")
        elif tool_def.name == "check_claim":
            self._state.context_tags.add("claim_validation_used")
        return result

    async def before_tool_execute(
        self,
        ctx: RunContext[CoreDeps],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_def.name != "save_artifact":
            return args

        markdown = str(args.get("final_markdown") or "")
        if not markdown.strip():
            return args

        self._state.context_tags.add("drafting")
        decision = self.evaluate_draft(ctx, markdown)
        self._state.last_signals = decision.signals

        if not decision.veto or decision.intervention is None:
            self._state.pending = None
            return args

        draft_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        if self._state.save_vetoes >= self.max_save_vetoes:
            return args
        if self._state.last_veto_hash == draft_hash:
            # Never loop on an identical candidate.
            return args

        self._state.save_vetoes += 1
        self._state.last_veto_hash = draft_hash
        self._state.pending = decision.intervention

        details = "\n".join(
            f"- {signal.name} ({signal.severity:.2f}): {signal.detail}"
            for signal in decision.signals[:4]
        )
        evidence = ", ".join(decision.intervention.evidence_ids)
        raise ModelRetry(
            "Editorial control rejected this save once before side effects occurred. "
            "Do NOT rewrite the whole article. Patch the smallest set of passages that "
            "addresses the observed drift while preserving sourced facts, claims, and "
            "the source ledger.\n"
            f"Observed drift:\n{details}\n"
            f"Cognitive move: {decision.intervention.action}\n"
            f"Direction: {decision.intervention.directive}\n"
            f"Evidence refs: {evidence}\n"
            "Then call save_artifact again with the patched final_markdown."
        )

    def evaluate_draft(
        self, ctx: RunContext[CoreDeps], markdown: str
    ) -> EditorialDraftDecision:
        signals = detect_trajectory(markdown)
        if not signals:
            return EditorialDraftDecision(False, (), None)

        intervention = self._select_intervention(ctx, signals)
        total = sum(signal.severity for signal in signals[:3])
        hard = any(signal.severity >= 0.90 for signal in signals)
        # One medium signal is advisory; multiple independent drifts or one very
        # strong drift can veto the first save attempt.
        veto = hard or (len(signals) >= 2 and total >= self.veto_threshold)
        return EditorialDraftDecision(veto, signals, intervention)

    def _update_from_text(self, ctx: RunContext[CoreDeps], text: str) -> None:
        signals = detect_trajectory(text)
        self._state.last_signals = signals
        if not signals:
            return
        if self._state.interventions_emitted >= self.max_injections:
            return
        intervention = self._select_intervention(ctx, signals)
        if intervention is not None:
            self._state.pending = intervention
            self._state.interventions_emitted += 1

    def _prepare_proactive_intervention(self, ctx: RunContext[CoreDeps]) -> None:
        if self._state.pending is not None:
            return
        if self._state.interventions_emitted >= self.max_injections:
            return

        # Proactive interventions are still evidence-backed. We use the gentlest
        # "specificity" signal as a retrieval key after actual material/tool work,
        # rather than fabricating a semantic diagnosis.
        signals = (
            EditorialSignal(
                "low_concrete_anchor_density",
                0.50,
                "proactive specificity check after observing writing context",
            ),
        )
        intervention = self._select_intervention(ctx, signals)
        if intervention is not None:
            self._state.pending = intervention
            self._state.interventions_emitted += 1

    def _select_intervention(
        self,
        ctx: RunContext[CoreDeps],
        signals: tuple[EditorialSignal, ...],
    ) -> EditorialIntervention | None:
        records = self.evidence_store.select(
            signals={signal.name for signal in signals},
            situation_tags=set(self._state.context_tags),
            run_id=ctx.deps.run_id,
            run_step=ctx.run_step,
            limit=self.evidence_limit,
        )
        if not records:
            return None

        # One action per intervention. Multiple approved records may support it.
        primary = records[0]
        same_action = [r for r in records if r.action == primary.action]
        evidence_ids = tuple(r.id for r in same_action)
        rationale = " | ".join(dict.fromkeys(r.rationale for r in same_action))
        return EditorialIntervention(
            action=primary.action,
            directive=primary.directive,
            rationale=rationale,
            evidence_ids=evidence_ids,
            trigger_signals=tuple(signal.name for signal in signals),
        )
