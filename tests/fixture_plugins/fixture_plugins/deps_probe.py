"""Fixture plugin exposing a tool that echoes the run's CoreDeps.case_id.

Used by the Gateway Case-binding tests to prove the bound Case identity
reaches execution deps (SPEC v1.0 §5.6) — the server threads it, the model
never guesses it."""

from __future__ import annotations

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions="Fixture deps-probe tools."
    )

    @toolset.tool
    def probe_deps(
        ctx: RunContext[CoreDeps],
        label: str = "run",
    ) -> str:
        """Echo which Case this run is bound to (server-owned)."""
        return f"{label}:{ctx.deps.run_id}:case={ctx.deps.case_id}"

    return PluginBundle(toolsets=[toolset])