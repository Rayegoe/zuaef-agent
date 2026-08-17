"""ACE Writing plugin for the ZUAEF Plugin Composition Layer.

Exports the verified ACE writing toolset plus the optional cross-cutting
Cognitive Editorial Control capability. ACE remains owner of material,
evidence, claim-validation, and canonical artifact semantics.
"""

from __future__ import annotations

from .editorial_control import (
    EditorialControlCapability,
    EditorialDraftDecision,
    EditorialIntervention,
    EditorialSignal,
    detect_trajectory,
)
from .editorial_evidence import (
    EditorialEvidence,
    EditorialEvidenceStore,
    append_approved_evidence,
)
from .plugin import create_plugin
from .writing_toolset import BudgetedWritingToolset, build_writing_toolset

__all__ = [
    "BudgetedWritingToolset",
    "EditorialControlCapability",
    "EditorialDraftDecision",
    "EditorialEvidence",
    "EditorialEvidenceStore",
    "EditorialIntervention",
    "EditorialSignal",
    "append_approved_evidence",
    "build_writing_toolset",
    "create_plugin",
    "detect_trajectory",
]
