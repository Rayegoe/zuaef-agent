"""Fixture Case-orientation plugin: an eager load_case_context tool.

Mirrors the production zuaef-case plugin's eager orientation role in hermetic
phase-2 tests (progressive disclosure / Case binding) without the real store."""

from __future__ import annotations

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions="Fixture Case orientation tools."
    )

    @toolset.tool
    def load_case_context(
        ctx: RunContext[CoreDeps],
        case_id: str,
        limit: int = 20,
    ) -> str:
        """Fixture: echo the requested case and the run's bound case."""
        return f"case={case_id} bound={ctx.deps.case_id}"

    return PluginBundle(toolsets=[toolset])