"""Fixture second-business-domain plugin (hardware scout) for the
domain-neutrality and no-implicit-activation contracts."""

from __future__ import annotations

from pydantic_ai import FunctionToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions="Fixture hardware-scout tools."
    )

    @toolset.tool_plain
    def scan_components(market: str) -> str:
        return f"scanning {market}"

    return PluginBundle(toolsets=[toolset])
