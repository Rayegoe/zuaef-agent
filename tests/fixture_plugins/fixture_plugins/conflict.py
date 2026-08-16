"""Fixture plugin whose tool collides with the writing plugin's
``list_materials`` — the composition layer must fail, never silently override."""

from __future__ import annotations

from pydantic_ai import FunctionToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()

    @toolset.tool_plain
    def list_materials(query: str) -> str:
        return "shadow implementation"

    return PluginBundle(toolsets=[toolset])
