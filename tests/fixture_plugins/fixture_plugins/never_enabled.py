"""Fixture plugin that must never be imported: no profile in the suite
enables it, so any import is implicit activation — a contract violation."""

from __future__ import annotations

from pydantic_ai import FunctionToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()

    @toolset.tool_plain
    def hidden_tool() -> str:
        return "should never be reachable"

    return PluginBundle(toolsets=[toolset])
