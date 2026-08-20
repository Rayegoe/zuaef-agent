"""LEGACY / BENCHMARK-ONLY (v1.2 T014B demotion) — runtime cognitive editorial
control for ACE Writing (SPEC v0.1, 2026-08-17).

This module moved out of the production plugin (``plugins/zuaef-ace-writing``)
in v1.2 T014B. It is retained because the editorial-learning benchmark
experiments still exercise it; per QUALITY_LOOP §11 its sensors, vetoes,
evidence weights and ``approved_by`` fields are LEGACY DERIVED FEATURES, not
human truth, and no production capability may require them. The production
factory rejects ``editorial_*`` config keys loudly (see ``legacy/README.md``).

Original spec: ``zuaef-editorial-control-v0.1`` (repository
``Rayegoe/zuaef-agent``, plugin ``zuaef-ace-writing``). One capability, no new
runtime:

- ``EditorialControlCapability`` changes the *conditions of the next model
  step* from approved editorial evidence: minimal invariants on the first
  request, at most one cognitive move + provenance refs before later requests.
- The save boundary is adversarial generation, not post-hoc review:
  ``before_tool_execute(save_artifact)`` runs trajectory sensors over
  ``final_markdown`` and vetoes via ``ModelRetry`` BEFORE the tool executes,
  bounded by ``max_save_vetoes`` and a never-twice hash rule.
- Editorial learning lives in a host-owned JSONL evidence store. The agent has
  no tool for approving or persisting evidence; the capability only reads it.
  Built-in seeds bootstrap the loop and are outranked by human patches.

Non-goals honored here: the PydanticAI Agent Loop is untouched,
``writing_toolset.py`` domain behavior is untouched, no writer/reviewer agent
pair, no token-level decoding control, no auto-rewrite after generation, no
fabricated scenes/quotations/memories (veto text says so explicitly).

Sensor honesty: the five trajectory sensors do not define taste. They answer
one question — "is there enough evidence of drift to retrieve human-approved
editorial decisions?" Machine sensors are diagnostics (SPEC §11 Gate E); the
success metric is blind human evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import ToolDefinition

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError

# --- SPEC §7: exactly five cognitive actions in v0.1 ------------------------

COGNITIVE_ACTIONS: tuple[str, ...] = (
    "return_to_observation",
    "delay_interpretation",
    "shift_perspective",
    "retrieve_concrete_memory",
    "break_trajectory",
)

ACTION_MOVES: dict[str, str] = {
    "return_to_observation": (
        "Return to observation: pull the camera back to concrete people, "
        "objects and scenes already present in the retrieved material; replace "
        "generalization with what is actually there."
    ),
    "delay_interpretation": (
        "Delay interpretation: let one more scene or fact appear before you "
        "explain what it means; do not close a paragraph by summarizing its "
        "significance."
    ),
    "shift_perspective": (
        "Shift perspective: move the narration to a different concrete "
        "observer or participant position available in the material, then "
        "continue from there."
    ),
    "retrieve_concrete_memory": (
        "Retrieve concrete memory: go back to the material for one specific "
        "number, quotation or scene detail and build the next passage around "
        "it. Source-grounded detail only — never invent."
    ),
    "break_trajectory": (
        "Break trajectory: start the next passage with a different structural "
        "move than the previous one; do not reuse its opening shape or rhythm."
    ),
}

# SPEC §5.1: minimal invariants, never a style recipe.
FIRST_REQUEST_INVARIANTS = (
    "Editorial control is active (runtime, evidence-backed):",
    "- Do not optimize for one-pass completion; drafting in moves is expected.",
    "- Do not imitate a fixed template or reuse one paragraph rhythm.",
    "- Preserve factual boundaries: no invented scenes, quotations, memories or reported facts.",
    "- Editorial interventions are local cognitive moves, not target sentences.",
    "- Prefer the smallest useful patch over whole-document rewrites.",
)

# --- trajectory sensors (SPEC §5.3): calibration constants -------------------
# Densities are occurrences per 1000 characters of body text (CJK chars ≈
# words; Latin words ≈ 6 chars, so the same basis works for both). A sensor
# scores 0..1; combined drift is the plain sum, compared against
# ``veto_threshold`` (default 1.50 ≈ at least two clearly firing sensors).

TEMPLATE_CONNECTORS: tuple[str, ...] = (
    # zh
    "总之", "综上所述", "总而言之", "值得注意的是", "与此同时", "不仅如此",
    "换句话说", "毋庸置疑", "众所周知", "首先", "其次", "最后",
    # en
    "in summary", "in conclusion", "moreover", "furthermore", "notably",
    "it is worth noting", "at the same time", "that said",
)
CONNECTOR_FLOOR = 2.0
CONNECTOR_CEIL = 8.0

SUMMARY_MARKERS: tuple[str, ...] = (
    # zh — interpretive/summarizing moves that close a passage prematurely
    "这说明", "这表明", "这意味着", "由此可见", "不难看出", "本质上",
    "归根结底", "可以说", "正是因为", "正是因为如此",
    # en
    "this shows", "this means", "this demonstrates", "in other words",
    "the key point is", "what this reveals", "the takeaway is",
)
SUMMARY_FLOOR = 1.5
SUMMARY_CEIL = 6.0

ABSTRACT_NOUNS: tuple[str, ...] = (
    # zh
    "问题", "现象", "意义", "价值", "发展", "影响", "层面", "维度", "模式",
    "体系", "机制", "趋势", "概念", "结构", "关系", "背景", "因素", "角度",
    "本质", "重要性",
    # en
    "significance", "importance", "development", "phenomenon", "dynamics",
    "narrative", "framework", "paradigm", "identity", "trajectory",
)
ABSTRACT_FLOOR = 6.0
ABSTRACT_CEIL = 20.0

# Concrete anchors: numbers (incl. full-width digits, years, percents) and
# quoted speech spans (zh 「」『』“” and en "…"). Proper-noun detection is
# deliberately out of scope for v0.1 — it is not cheap and reliable across
# scripts.
NUMBER_RE = re.compile(r"[0-9０-９][0-9０-９.,，%％]*")
QUOTED_SPAN_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"「[^「」]{1,80}」"),
    re.compile(r"『[^『』]{1,80}』"),
    re.compile(r"“[^“”]{1,80}”"),
    re.compile(r'"[^"\n]{1,80}"'),
)
ANCHOR_TARGET = 4.0  # anchors per 1000 chars below which grounding is thin

UNIFORM_PARAGRAPH_CV = 0.30  # cv at/below which paragraphs count as uniform
MIN_SENSORED_CHARS = 500  # short replies and tool-call-only text: not sensorable
MIN_SENSORED_PARAGRAPHS = 3


def _density(occurrences: int, chars: int) -> float:
    return occurrences * 1000.0 / chars if chars else 0.0


def _ramp(density: float, floor: float, ceil: float) -> float:
    return max(0.0, min(1.0, (density - floor) / (ceil - floor)))


def _count_phrases(text: str, phrases: tuple[str, ...]) -> int:
    return sum(text.count(phrase) for phrase in phrases)


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def run_trajectory_sensors(text: str) -> dict[str, float]:
    """Run the five cheap sensors; empty dict when text is not long-form.

    Deterministic, no model calls, no taste claims — drift evidence only.
    """
    stripped = text.strip()
    if len(stripped) < MIN_SENSORED_CHARS:
        return {}
    paras = _paragraphs(stripped)
    if len(paras) < MIN_SENSORED_PARAGRAPHS:
        return {}
    chars = len(stripped)

    connectors = _ramp(_density(_count_phrases(stripped, TEMPLATE_CONNECTORS), chars), CONNECTOR_FLOOR, CONNECTOR_CEIL)
    summary = _ramp(_density(_count_phrases(stripped, SUMMARY_MARKERS), chars), SUMMARY_FLOOR, SUMMARY_CEIL)
    abstract = _ramp(_density(_count_phrases(stripped, ABSTRACT_NOUNS), chars), ABSTRACT_FLOOR, ABSTRACT_CEIL)

    anchors = len(NUMBER_RE.findall(stripped)) + sum(
        len(rx.findall(stripped)) for rx in QUOTED_SPAN_RES
    )
    low_anchor = max(0.0, min(1.0, (ANCHOR_TARGET - _density(anchors, chars)) / ANCHOR_TARGET))

    uniform = 0.0
    if len(paras) >= 4:
        lengths = [len(p) for p in paras]
        mean = sum(lengths) / len(lengths)
        if mean > 0:
            cv = math.sqrt(sum((n - mean) ** 2 for n in lengths) / len(lengths)) / mean
            uniform = max(0.0, min(1.0, (UNIFORM_PARAGRAPH_CV - cv) / UNIFORM_PARAGRAPH_CV))

    signals = {
        "template_connectors": round(connectors, 3),
        "summary_pressure": round(summary, 3),
        "uniform_paragraphs": round(uniform, 3),
        "low_concrete_anchor_density": round(low_anchor, 3),
        "abstract_noun_density": round(abstract, 3),
    }
    return {name: score for name, score in signals.items() if score > 0.0}


def combined_drift(signals: dict[str, float]) -> float:
    """SPEC §5.5: the combined drift score compared against the veto threshold."""
    return sum(signals.values())


# --- editorial evidence (SPEC §6) ---------------------------------------------


class EditorialEvidence(BaseModel):
    """One unit of editorial learning: situation → drift → action → why → source.

    ``before_excerpt``/``after_excerpt`` are bounded excerpts for provenance
    only; seeds ship none, and no full copyrighted article is ever stored.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source_type: str  # human_patch | corpus_observation | editorial_note | builtin_seed
    source_ref: str = ""
    situation_tags: list[str] = Field(default_factory=list)
    trigger_signals: list[str] = Field(default_factory=list)
    action: str
    directive: str
    rationale: str = ""
    weight: float = 1.0
    approved_by: str = "human-editor"
    before_excerpt: str = ""
    after_excerpt: str = ""


def seed_evidence() -> list[EditorialEvidence]:
    """Built-in bootstrap evidence (SPEC §6.2.4). Bootstrap only, not the moat:
    weight 1.0 so any human patch (typically 4.0) outranks them, and
    ``source_type`` stays ``builtin_seed`` so Gate F can measure the shift."""
    return [
        EditorialEvidence(
            id="seed.template-connectors.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction"],
            trigger_signals=["template_connectors"],
            action="break_trajectory",
            directive=(
                "When connector phrases and mirrored paragraph openings repeat, "
                "vary the structural move of the next passage instead of "
                "polishing individual sentences."
            ),
            rationale=(
                "Repeated discourse connectors mark a fixed template trajectory; "
                "changing the structural move breaks it with a smaller patch than "
                "a rewrite."
            ),
            weight=1.0,
            approved_by="seed:v0.1",
        ),
        EditorialEvidence(
            id="seed.summary-pressure.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction"],
            trigger_signals=["summary_pressure"],
            action="delay_interpretation",
            directive=(
                "When interpretive closers pile up, let the next scene or fact "
                "arrive before its meaning is stated."
            ),
            rationale=(
                "Premature explanation flattens narrative movement; the editor's "
                "standing decision is to hold interpretation until after the "
                "evidence has landed."
            ),
            weight=1.0,
            approved_by="seed:v0.1",
        ),
        EditorialEvidence(
            id="seed.uniform-paragraphs.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction"],
            trigger_signals=["uniform_paragraphs"],
            action="break_trajectory",
            directive=(
                "When paragraphs share one length and rhythm, split or merge "
                "where the material actually changes, not at a fixed cadence."
            ),
            rationale="Uniform blocks are the surface trace of template-driven drafting.",
            weight=1.0,
            approved_by="seed:v0.1",
        ),
        EditorialEvidence(
            id="seed.low-concrete-anchor.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction"],
            trigger_signals=["low_concrete_anchor_density"],
            action="retrieve_concrete_memory",
            directive=(
                "When the text carries few numbers, dates or quoted voices, go "
                "back to the material for one specific verifiable detail and "
                "build around it."
            ),
            rationale="Grounding lives in concrete anchors; retrieval beats invention.",
            weight=1.0,
            approved_by="seed:v0.1",
        ),
        EditorialEvidence(
            id="seed.abstract-noun-density.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction"],
            trigger_signals=["abstract_noun_density"],
            action="return_to_observation",
            directive=(
                "When abstract nouns dominate, return to what is observable in "
                "the material: people, objects, actions, places."
            ),
            rationale="Abstraction drift moves the draft away from its evidence base.",
            weight=1.0,
            approved_by="seed:v0.1",
        ),
        EditorialEvidence(
            id="seed.after-exemplar.001",
            source_type="builtin_seed",
            source_ref="seed:zuaef-editorial-control-v0.1",
            situation_tags=["drafting", "nonfiction", "exemplar_observed"],
            trigger_signals=[],
            action="return_to_observation",
            directive=(
                "After studying exemplar technique, return to your own material "
                "before writing the next passage: technique serves the material, "
                "never the reverse."
            ),
            rationale=(
                "The recurring editorial decision after exemplar study is a "
                "return to observation, preventing imitation of surface manner."
            ),
            weight=1.0,
            approved_by="seed:v0.1",
        ),
    ]


class EditorialEvidenceStore:
    """Read-only view over seeds + the host-owned JSONL evidence file.

    The file is human-maintained (Gate D: the agent has no tool to write it).
    A malformed line fails composition loudly — silently skipping a human
    editorial decision would be the exact failure this capability exists to
    prevent.
    """

    def __init__(self, extra_path: Path | None = None) -> None:
        self._entries: list[EditorialEvidence] = seed_evidence()
        if extra_path is not None:
            self._entries.extend(self._load_jsonl(extra_path))

    @staticmethod
    def _load_jsonl(path: Path) -> list[EditorialEvidence]:
        if not path.is_file():
            return []
        entries: list[EditorialEvidence] = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                entry = EditorialEvidence.model_validate(record)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise CompositionError(
                    f"editorial evidence {path}:{lineno} is not a valid "
                    f"EditorialEvidence record: {exc}"
                ) from exc
            if entry.action not in COGNITIVE_ACTIONS:
                raise CompositionError(
                    f"editorial evidence {path}:{lineno}: action {entry.action!r} "
                    f"is not one of {COGNITIVE_ACTIONS} (v0.1 freezes the set)"
                )
            entries.append(entry)
        return entries

    def __len__(self) -> int:
        return len(self._entries)

    def retrieve(
        self,
        *,
        signals: dict[str, float],
        tags: list[str],
        limit: int,
    ) -> list[EditorialEvidence]:
        """Rank approved evidence by trigger-signal and situation-tag overlap.

        Score: 2 per firing-signal match, 1 per situation-tag match; ties break
        by weight then id so retrieval is deterministic.
        """
        scored: list[tuple[int, float, str, EditorialEvidence]] = []
        for entry in self._entries:
            score = 2 * len(set(entry.trigger_signals) & set(signals))
            score += len(set(entry.situation_tags) & set(tags))
            if score > 0:
                scored.append((score, entry.weight, entry.id, entry))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [entry for _, _, _, entry in scored[:limit]]


# --- per-run state (SPEC §9) ---------------------------------------------------


@dataclass
class PendingIntervention:
    """One armed cognitive move awaiting the next model request."""

    serial: int  # run-local monotonic id, for the render→consume handshake
    action: str
    evidence_ids: list[str]
    signals: dict[str, float]
    origin: str  # "after_model_request" | "after_tool_execute" | "save_veto"


@dataclass
class EditorialRunState:
    """Ephemeral control state only; long-term learning stays in the store."""

    model_requests: int = 0
    interventions: int = 0
    save_vetoes: int = 0
    context_tags: list[str] = field(default_factory=list)
    latest_signals: dict[str, float] = field(default_factory=dict)
    pending: PendingIntervention | None = None
    last_veto_hash: str | None = None
    last_rendered_serial: int | None = None
    _next_serial: int = 0

    def next_serial(self) -> int:
        self._next_serial += 1
        return self._next_serial

    def add_tags(self, tags: list[str]) -> None:
        for tag in tags:
            if tag not in self.context_tags:
                self.context_tags.append(tag)


@dataclass(frozen=True)
class EditorialSettings:
    max_injections: int = 4
    max_save_vetoes: int = 1
    evidence_limit: int = 3
    veto_threshold: float = 1.50
    temperature_nudge: float = 0.0
    base_temperature: float = 0.7
    evidence_path: Path | None = None


SAVE_TOOL = "save_artifact"

# after_tool_execute context tags (SPEC §5.2): material/exemplar observation.
OBSERVATION_TOOL_TAGS: dict[str, list[str]] = {
    "list_materials": ["material_survey"],
    "read_material": ["material_observed"],
    "retrieve_exemplars": ["exemplar_observed"],
    "retrieve_knowledge": ["knowledge_observed"],
    "check_claim": ["claim_checked"],
}
# Tools after which a low-pressure intervention may be armed.
LOW_PRESSURE_TOOLS = ("read_material", "retrieve_exemplars")


def _evidence_line(entry: EditorialEvidence) -> str:
    return f"{entry.id} ({entry.action}, weight {entry.weight:g}, {entry.source_type})"


class EditorialControlCapability(AbstractCapability[CoreDeps]):
    """Cognitive editorial feedback loop over the ACE writing toolset.

    Loop: observe tools → arm at most one evidence-backed cognitive move →
    expose it via dynamic instructions before the next request → sense drift
    after substantial responses → veto templated ``save_artifact`` candidates
    before side effects, bounded and never twice for the same draft.
    """

    def __init__(self, *, settings: EditorialSettings, store: EditorialEvidenceStore) -> None:
        self._settings = settings
        self._store = store
        self.state = EditorialRunState()

    # -- lifecycle -------------------------------------------------------------

    async def for_run(self, ctx: RunContext[CoreDeps]) -> EditorialControlCapability[CoreDeps]:
        """Fresh run-local state; settings and the read-only store are shared."""
        return EditorialControlCapability(settings=self._settings, store=self._store)

    # -- dynamic instructions (SPEC §5.1 / §5.4) --------------------------------

    def get_instructions(self):
        # Bound method: resolved from the run-bound instance after for_run, and
        # re-invoked while assembling every model request, so it always sees
        # the current pending intervention.
        return self._instructions

    def _instructions(self, ctx: RunContext[CoreDeps]) -> str:
        lines = list(FIRST_REQUEST_INVARIANTS)
        pending = self.state.pending
        if pending is not None and self.state.last_rendered_serial != pending.serial:
            self.state.last_rendered_serial = pending.serial
            lines.append("")
            lines.append(f"[editorial move | {pending.action} | origin: {pending.origin}]")
            lines.append(ACTION_MOVES[pending.action])
            if pending.signals:
                shown = ", ".join(f"{k}={v:g}" for k, v in pending.signals.items())
                lines.append(f"recent trajectory signals: {shown}")
            lines.append(f"evidence: {', '.join(pending.evidence_ids)}")
            lines.append(
                "Apply this as one local cognitive move in your next step; do "
                "not rewrite earlier passages and keep claims and the source "
                "ledger untouched."
            )
        return "\n".join(lines)

    def get_model_settings(self):
        # SPEC §5.4: sampling changes only when explicitly configured (default
        # nudge 0.0 → no model settings at all, no behavior change).
        if self._settings.temperature_nudge == 0.0:
            return None
        return self._model_settings

    def _model_settings(self, ctx: RunContext[CoreDeps]) -> dict[str, Any]:
        pending = self.state.pending
        if pending is not None and self.state.last_rendered_serial == pending.serial:
            return {"temperature": self._settings.base_temperature + self._settings.temperature_nudge}
        return {}

    # -- hooks -------------------------------------------------------------------

    async def before_model_request(
        self,
        ctx: RunContext[CoreDeps],
        request_context: ModelRequestContext,
    ) -> ModelRequestContext:
        self.state.model_requests += 1
        # Consume the intervention the instruction callable rendered into THIS
        # request (instructions resolve before this hook in the agent graph).
        pending = self.state.pending
        if (
            pending is not None
            and self.state.last_rendered_serial == pending.serial
        ):
            self.state.interventions += 1
            self.state.pending = None
        return request_context

    async def after_model_request(
        self,
        ctx: RunContext[CoreDeps],
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        text = "\n".join(
            part.content for part in response.parts if isinstance(part, TextPart)
        )
        signals = run_trajectory_sensors(text)
        if not signals:
            return response
        self.state.latest_signals = signals
        self._maybe_arm(signals, origin="after_model_request")
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
        tags = OBSERVATION_TOOL_TAGS.get(tool_def.name)
        if tags:
            self.state.add_tags(tags)
        if tool_def.name in LOW_PRESSURE_TOOLS:
            self._maybe_arm(
                self.state.latest_signals,
                origin="after_tool_execute",
                extra_tags=tags or [],
            )
        return result

    async def before_tool_execute(
        self,
        ctx: RunContext[CoreDeps],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_def.name != SAVE_TOOL:
            return args
        text = args.get("final_markdown")
        if not isinstance(text, str):
            return args
        signals = run_trajectory_sensors(text)
        if not signals:
            return args  # not long-form enough to judge
        self.state.latest_signals = signals
        drift = combined_drift(signals)
        if drift < self._settings.veto_threshold:
            return args
        # Bounded (SPEC §5.5.4): at most max_save_vetoes rejections...
        if self.state.save_vetoes >= self._settings.max_save_vetoes:
            return args
        # ...and an identical candidate is never rejected twice (§5.5.5).
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest == self.state.last_veto_hash:
            return args

        evidence = self._store.retrieve(
            signals=signals,
            tags=[*self.state.context_tags, "save_boundary"],
            limit=self._settings.evidence_limit,
        )
        self.state.save_vetoes += 1
        self.state.last_veto_hash = digest
        self.state.pending = None  # the veto IS the intervention at this boundary
        shown = ", ".join(f"{k}={v:g}" for k, v in signals.items())
        moves = ", ".join(f"{e.action} ({e.id})" for e in evidence) or "break_trajectory"
        raise ModelRetry(
            "EDITORIAL SAVE VETO "
            f"({self.state.save_vetoes}/{self._settings.max_save_vetoes} allowed) — "
            "the draft was rejected before any side effect: it has converged on a "
            "strongly templated trajectory.\n"
            f"Combined drift {drift:.2f} >= threshold "
            f"{self._settings.veto_threshold:.2f}: {shown}\n"
            f"Approved editorial evidence: {moves}\n"
            "Required: make the SMALLEST useful patch that moves the draft off "
            "this trajectory — one local cognitive move, not a rewrite.\n"
            "- Preserve the claims ledger and source ledger exactly as provided.\n"
            "- Do not invent scenes, quotations, memories or reported facts.\n"
            "- Re-submit via save_artifact with the patched final_markdown.\n"
            "An identical draft will not be vetoed again."
        )

    # -- intervention arming -------------------------------------------------------

    def _maybe_arm(
        self,
        signals: dict[str, float],
        *,
        origin: str,
        extra_tags: list[str] | None = None,
    ) -> None:
        """Arm one evidence-backed cognitive move for the next request.

        Bounded by max_injections; never overwrites an armed move; requires at
        least one approved evidence match (Gate C: no semantic intervention
        without provenance). For the low-pressure after-observation path the
        signals may be empty — retrieval then rides on situation tags alone.
        """
        if self.state.pending is not None:
            return
        if self.state.interventions >= self._settings.max_injections:
            return
        tags = ["drafting", "nonfiction", *self.state.context_tags, *(extra_tags or [])]
        evidence = self._store.retrieve(
            signals=signals, tags=tags, limit=self._settings.evidence_limit
        )
        if not evidence:
            return
        best = evidence[0]
        self.state.pending = PendingIntervention(
            serial=self.state.next_serial(),
            action=best.action,
            evidence_ids=[entry.id for entry in evidence],
            signals=dict(signals),
            origin=origin,
        )
