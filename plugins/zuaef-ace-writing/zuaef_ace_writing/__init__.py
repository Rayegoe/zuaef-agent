"""ACE Writing plugin for the ZUAEF Plugin Composition Layer.

Exposes the ``ace-writing`` ``zuaef.plugins`` entry point; the factory
assembles the verified BudgetedWritingToolset (list_materials, read_material,
retrieve_exemplars, retrieve_knowledge, check_claim, save_artifact) over the
external article-context-engine. No corpus selection, evidence validation,
material validation, or canonical artifact semantics live here (SPEC §34).

Editorial control (0.2.0 experiment) was removed from this production surface
in v1.2 T014B; the capability is benchmark/legacy only under
``benchmarks/editorial-learning/legacy/``.
"""

from __future__ import annotations

from .plugin import create_plugin
from .writing_toolset import BudgetedWritingToolset, build_writing_toolset

__all__ = [
    "BudgetedWritingToolset",
    "build_writing_toolset",
    "create_plugin",
]
