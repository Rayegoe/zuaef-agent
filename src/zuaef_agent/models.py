from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .plugin_api import CompositionSnapshot


class SourceRef(BaseModel):
    """A source actually observed by the system (knowledge-module type).

    Retained only until the knowledge-store simplification (v1.2 T007)
    removes its last kernel consumer; it is NOT part of the receipt contract.
    """

    id: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    title: str | None = None
    evidence: str | None = None


class ArtifactFact(BaseModel):
    """Operational byte fact about one workspace artifact.

    A hash proves byte identity/change — never content correctness.
    """

    path: str
    size: int
    sha256: str
    change: Literal["created", "modified"]


class ToolEffectFact(BaseModel):
    """Operational fact from the StepStore tool-call ledger.

    A completed tool call proves the call finished — never that the business
    outcome was good.
    """

    tool_call_id: str
    tool_name: str
    status: Literal["started", "completed", "failed"]


# Terminal execution state. Pause is a separate receipt state (``state="paused"``).
ExecutionState = Literal["completed", "failed", "limit_reached"]


class RunReceipt(BaseModel):
    """Operational record of one terminal run — never a semantic verdict.

    Answers what ran, with which composition, when, with which usage, which
    execution state occurred, which byte facts changed, and why it failed or
    was limited. It does NOT claim an answer is true, a source supports a
    claim, or a business decision is correct.
    """

    schema_version: Literal["2.0"] = "2.0"
    state: Literal["terminal"] = "terminal"
    run_id: str
    conversation_id: str | None = None
    continued_from_run_id: str | None = None
    bindings: Mapping[str, str] = Field(default_factory=dict)
    model: str
    started_at: datetime
    finished_at: datetime
    execution_state: ExecutionState
    outcome: str
    usage: dict[str, Any] = Field(default_factory=dict)
    usage_complete: bool = False
    artifact_facts: list[ArtifactFact] = Field(default_factory=list)
    tool_effect_facts: list[ToolEffectFact] = Field(default_factory=list)
    knowledge_updates: list[str] = Field(default_factory=list)
    unresolved_effects: list[ToolEffectFact] = Field(default_factory=list)
    error: str | None = None
    step_store: str | None = None
    tool_result_store: str | None = None
    composition: CompositionSnapshot | None = None


class PauseReceipt(BaseModel):
    """Receipt for a run paused awaiting approval — pending work, not a verdict.

    ``composition`` is the resume authority: a continuation must reconstruct
    the exact frozen composition and must ignore the mutable current profile.
    """

    schema_version: Literal["2.0"] = "2.0"
    state: Literal["paused"] = "paused"
    run_id: str
    conversation_id: str
    bindings: Mapping[str, str] = Field(default_factory=dict)
    model: str
    started_at: datetime
    finished_at: datetime
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    pending_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifact_facts: list[ArtifactFact] = Field(default_factory=list)
    tool_effect_facts: list[ToolEffectFact] = Field(default_factory=list)
    knowledge_updates: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    usage_complete: bool = False
    step_store: str | None = None
    tool_result_store: str | None = None
    composition: CompositionSnapshot | None = None


AnyReceipt = RunReceipt | PauseReceipt


@dataclass(frozen=True)
class CoreDeps:
    workspace_root: Path
    run_id: str
    # Opaque host-provided bindings (v1.2 SPEC §4): the kernel preserves them
    # across pause/resume but never inspects their meaning or validates
    # domain-specific keys. Examples: {"case": "stillevo-beauty"},
    # {"project": "wp-redesign"}, {"tenant": "stillevo", "case": "beauty-001"}.
    bindings: Mapping[str, str] = field(default_factory=dict)
