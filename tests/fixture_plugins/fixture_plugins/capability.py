"""Fixture capability-returning plugin: must fail closed unless the profile
explicitly sets ``allow_capabilities = true``."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv


@dataclass
class FixtureCapability(AbstractCapability[CoreDeps]):
    def get_toolset(self) -> AgentToolset[CoreDeps] | None:
        toolset: FunctionToolset[CoreDeps] = FunctionToolset(
            instructions="Fixture capability tools."
        )

        @toolset.tool
        def capability_tool(ctx: RunContext[CoreDeps], value: str) -> str:
            return f"capability handled {value}"

        return toolset


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    return PluginBundle(capabilities=[FixtureCapability()])
