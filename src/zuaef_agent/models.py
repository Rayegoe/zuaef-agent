from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .plugin_api import CompositionSnapshot


class SourceRef(BaseModel):
    """A source actually observed by the system."""

    id: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    title: str | None = None
    evidence: str | None = None


class RunSummary(BaseModel):
    """Small terminal contract; large work belongs in artifacts.

    `artifacts` holds workspace-relative paths the model claims this run created
    or modified; `evidence` holds parseable refs of the form
    ``artifact:<path>`` / ``knowledge:<id>`` / ``tool-effect:<tool_call_id>``.
    Both are model proposals — the host verifies before the receipt finalizes.
    """

    status: Literal["completed", "partial", "blocked"]
    outcome: str
    artifacts: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    next_action: str | None = None
    run_id: str | None = None
    receipt: str | None = None


class ArtifactVerification(BaseModel):
    """Host-verified facts about one artifact claimed by a run."""

    path: str
    size: int
    sha256: str


class ToolEffectVerification(BaseModel):
    """Host-verified tool-effect ledger entry."""

    tool_call_id: str
    tool_name: str
    status: Literal["started", "completed", "failed"]


class RunReceipt(BaseModel):
    """Machine-readable index over one terminal run's durable evidence.

    ``composition`` freezes the plugin composition (profile, plugin refs,
    composition_id) for receipts of composed runs; runs without a profile
    keep ``composition = None``.
    """

    schema_version: Literal["1.2"] = "1.2"
    state: Literal["terminal"] = "terminal"
    run_id: str
    conversation_id: str | None = None
    continued_from_run_id: str | None = None
    model: str
    started_at: datetime
    finished_at: datetime
    status: Literal["completed", "partial", "blocked"]
    summary: RunSummary
    usage: dict[str, Any] = Field(default_factory=dict)
    usage_complete: bool = False
    verified_artifacts: list[ArtifactVerification] = Field(default_factory=list)
    verified_knowledge: list[str] = Field(default_factory=list)
    verified_tool_effects: list[ToolEffectVerification] = Field(default_factory=list)
    knowledge_updates: list[str] = Field(default_factory=list)
    unresolved_effects: list[ToolEffectVerification] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)
    error: str | None = None
    step_store: str | None = None
    tool_result_store: str | None = None
    composition: CompositionSnapshot | None = None


class PauseReceipt(BaseModel):
    """Receipt for a run that paused awaiting approval — not a terminal state.

    ``composition`` is the resume authority: a continuation must reconstruct
    the exact frozen composition and must ignore the mutable current profile.
    """

    schema_version: Literal["1.2"] = "1.2"
    state: Literal["paused"] = "paused"
    run_id: str
    conversation_id: str
    model: str
    started_at: datetime
    finished_at: datetime
    pending_approvals: list[dict[str, Any]] = Field(default_factory=list)
    pending_calls: list[dict[str, Any]] = Field(default_factory=list)
    settled_evidence: list[str] = Field(default_factory=list)
    verified_artifacts: list[ArtifactVerification] = Field(default_factory=list)
    verified_knowledge: list[str] = Field(default_factory=list)
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
