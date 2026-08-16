"""EMTB budget plugin for the ZUAEF Plugin Composition Layer.

Exposes the ``zuaef-emtb-budget`` ``zuaef.plugins`` entry point; the factory
assembles the deterministic budget toolset (parse_budget_csv, budget_summary,
budget_variance, budget_consistency, budget_health, budget_query,
significant_changes, save_budget_report) over ``budget_lib`` — a faithful
extraction of zesenticai finance_agent's deterministic commands. No LLM call,
no scoring, no judgment lives here; the model composes the trajectory, the
human owns taste.
"""

from __future__ import annotations

from .plugin import create_plugin
from .toolset import BUDGET_RULES, build_budget_toolset

__all__ = ["BUDGET_RULES", "build_budget_toolset", "create_plugin"]
