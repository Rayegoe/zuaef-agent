"""ACE Writing plugin for the ZUAEF Plugin Composition Layer.

Exposes the ``ace-writing`` ``zuaef.plugins`` entry point; the factory
assembles the verified BudgetedWritingToolset (list_materials, read_material,
retrieve_exemplars, retrieve_knowledge, check_claim, save_artifact) over the
external article-context-engine. No corpus selection, evidence validation,
material validation, or canonical artifact semantics live here (SPEC §34).

Since 0.2.0 (SPEC ``zuaef-editorial-control-v0.1``): with
``editorial_control = true`` the bundle also carries the
EditorialControlCapability — runtime cognitive editorial control over the
unchanged writing toolset.
"""

from __future__ import annotations

from .editorial import (
    COGNITIVE_ACTIONS,
    EditorialControlCapability,
    EditorialEvidence,
    EditorialEvidenceStore,
    EditorialSettings,
)
from .plugin import create_plugin
from .writing_toolset import BudgetedWritingToolset, build_writing_toolset

__all__ = [
    "COGNITIVE_ACTIONS",
    "BudgetedWritingToolset",
    "EditorialControlCapability",
    "EditorialEvidence",
    "EditorialEvidenceStore",
    "EditorialSettings",
    "build_writing_toolset",
    "create_plugin",
]
