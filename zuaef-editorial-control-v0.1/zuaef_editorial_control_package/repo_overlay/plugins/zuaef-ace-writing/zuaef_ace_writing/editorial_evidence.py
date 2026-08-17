"""Evidence model and deterministic retrieval for editorial-control.

This is intentionally host-owned. The agent can read selected editorial evidence
through the capability's dynamic instructions, but it is never given a tool that
can approve or persist its own taste.

The store contains derivative editorial decisions, not full source articles:
situation -> observed drift -> editorial action -> rationale -> provenance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

CognitiveAction = Literal[
    "return_to_observation",
    "delay_interpretation",
    "shift_perspective",
    "retrieve_concrete_memory",
    "break_trajectory",
]

TrajectorySignalName = Literal[
    "template_connectors",
    "summary_pressure",
    "uniform_paragraphs",
    "low_concrete_anchor_density",
    "abstract_noun_density",
]


class EditorialEvidence(BaseModel):
    """One approved, provenance-bearing editorial decision."""

    id: str = Field(min_length=1)
    source_type: Literal["human_patch", "corpus_observation", "editorial_note", "builtin"]
    source_ref: str = Field(min_length=1)
    situation_tags: list[str] = Field(default_factory=list)
    trigger_signals: list[TrajectorySignalName] = Field(default_factory=list)
    action: CognitiveAction
    directive: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    approved_by: str = Field(default="builtin")
    before_excerpt: str | None = None
    after_excerpt: str | None = None


DEFAULT_EVIDENCE: tuple[EditorialEvidence, ...] = (
    EditorialEvidence(
        id="builtin.scene-before-interpretation",
        source_type="builtin",
        source_ref="builtin:editorial-control-v0.1",
        situation_tags=["drafting", "nonfiction", "grounded"],
        trigger_signals=["summary_pressure", "low_concrete_anchor_density"],
        action="return_to_observation",
        directive=(
            "Before the next conclusion, recover one observable action, line of speech, "
            "object, place, time marker, or other concrete anchor already supported by the "
            "materials. Do not invent a scene."
        ),
        rationale=(
            "Interpretation becomes more convincing when the reader encounters evidence "
            "before the author explains its meaning."
        ),
        weight=1.4,
    ),
    EditorialEvidence(
        id="builtin.delay-thesis",
        source_type="builtin",
        source_ref="builtin:editorial-control-v0.1",
        situation_tags=["drafting", "nonfiction"],
        trigger_signals=["summary_pressure", "abstract_noun_density"],
        action="delay_interpretation",
        directive=(
            "Postpone the thesis for one beat. Let two grounded facts, voices, or tensions "
            "coexist before resolving them into an explanation."
        ),
        rationale=(
            "Premature synthesis is a common source of generic explanatory prose; delayed "
            "interpretation preserves discovery and reader participation."
        ),
        weight=1.3,
    ),
    EditorialEvidence(
        id="builtin.change-camera",
        source_type="builtin",
        source_ref="builtin:editorial-control-v0.1",
        situation_tags=["drafting"],
        trigger_signals=["uniform_paragraphs"],
        action="shift_perspective",
        directive=(
            "Change the camera rather than merely varying sentence length: move to another "
            "person, time scale, spatial position, or level of observation that is already "
            "available in the evidence."
        ),
        rationale=(
            "Human prose often changes cognitive distance; mechanical prose tends to keep "
            "the same explanatory camera for every paragraph."
        ),
        weight=1.2,
    ),
    EditorialEvidence(
        id="builtin.retrieve-specificity",
        source_type="builtin",
        source_ref="builtin:editorial-control-v0.1",
        situation_tags=["drafting", "grounded"],
        trigger_signals=["low_concrete_anchor_density", "abstract_noun_density"],
        action="retrieve_concrete_memory",
        directive=(
            "Search the already observed material for a specific remembered or recorded "
            "detail that can carry the idea. If no such detail exists, keep the association "
            "explicitly hypothetical; never manufacture autobiographical or reported fact."
        ),
        rationale=(
            "The useful human move is associative recall, not fabrication. In nonfiction, "
            "the factual boundary must remain explicit."
        ),
        weight=1.25,
    ),
    EditorialEvidence(
        id="builtin.break-smoothness",
        source_type="builtin",
        source_ref="builtin:editorial-control-v0.1",
        situation_tags=["drafting"],
        trigger_signals=["template_connectors", "uniform_paragraphs", "summary_pressure"],
        action="break_trajectory",
        directive=(
            "Interrupt the current smooth explanatory path with a grounded contradiction, "
            "exception, unanswered question, or asymmetry. Do not add a decorative twist."
        ),
        rationale=(
            "Template prose optimizes for frictionless completion; serious writing often "
            "advances by preserving a real contradiction long enough to think with it."
        ),
        weight=1.45,
    ),
)


class EditorialEvidenceStore:
    """Small deterministic evidence retriever.

    Ranking is deliberately simple and inspectable: matching trajectory signals dominate,
    then situation tags, then human-supplied weight. A stable hash breaks ties so repeated
    runs can vary without nondeterministic global randomness.
    """

    def __init__(self, evidence: tuple[EditorialEvidence, ...]) -> None:
        self.evidence = evidence

    @classmethod
    def load(cls, path: Path | None = None) -> "EditorialEvidenceStore":
        records = list(DEFAULT_EVIDENCE)
        if path is not None and path.is_file():
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                try:
                    records.append(EditorialEvidence.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(
                        f"invalid editorial evidence at {path}:{line_no}: {exc}"
                    ) from exc
        # Explicit later records with the same id override built-ins.
        by_id = {record.id: record for record in records}
        return cls(tuple(by_id.values()))

    def select(
        self,
        *,
        signals: set[str],
        situation_tags: set[str],
        run_id: str,
        run_step: int,
        limit: int = 3,
    ) -> list[EditorialEvidence]:
        scored: list[tuple[float, int, EditorialEvidence]] = []
        for record in self.evidence:
            signal_overlap = len(signals.intersection(record.trigger_signals))
            tag_overlap = len(situation_tags.intersection(record.situation_tags))
            if signals and signal_overlap == 0:
                # Evidence with no connection to the observed drift is not taste evidence
                # for this intervention.
                continue
            score = signal_overlap * 5.0 + tag_overlap * 1.5 + record.weight
            tie = int.from_bytes(
                hashlib.sha256(
                    f"{run_id}:{run_step}:{record.id}".encode("utf-8")
                ).digest()[:8],
                "big",
            )
            scored.append((score, tie, record))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [record for _, _, record in scored[:limit]]


def append_approved_evidence(path: Path, evidence: EditorialEvidence) -> None:
    """Host-side ingestion for a human-approved edit decision.

    This function is intentionally not exposed as an Agent tool.
    """

    if not evidence.approved_by.strip() or evidence.approved_by == "model":
        raise ValueError("editorial evidence requires a non-model approver")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(evidence.model_dump_json())
        f.write("\n")
