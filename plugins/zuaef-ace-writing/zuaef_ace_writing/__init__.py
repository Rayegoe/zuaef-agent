"""ACE Writing plugin for the ZUAEF Plugin Composition Layer.

Exposes the ``ace-writing`` ``zuaef.plugins`` entry point; the factory
assembles the verified BudgetedWritingToolset (list_materials, read_material,
retrieve_exemplars, retrieve_knowledge, check_claim, save_artifact) over the
external article-context-engine. No corpus selection, evidence validation,
material validation, or canonical artifact semantics live here (SPEC §34).
"""

from __future__ import annotations

from .plugin import create_plugin
from .writing_toolset import BudgetedWritingToolset, build_writing_toolset

__all__ = ["BudgetedWritingToolset", "build_writing_toolset", "create_plugin"]
