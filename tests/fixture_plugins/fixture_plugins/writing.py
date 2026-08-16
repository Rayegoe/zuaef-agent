"""Fixture ACE-writing-style plugin: one toolset plus one skill directory."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import FunctionToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv

# Observability for tests: module state records what the factory received.
last_env: PluginEnv | None = None
last_config: dict | None = None


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    global last_env, last_config
    last_env = env
    last_config = dict(config)
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions="Fixture writing tools: observe materials, save artifacts."
    )

    @toolset.tool_plain
    def list_materials(query: str) -> str:
        return f"materials for {query}"

    @toolset.tool_plain
    def save_artifact(title: str, body: str) -> str:
        return f"saved {title}"

    @toolset.tool_plain(requires_approval=True)
    def publish_article(article_id: str) -> str:
        """External side effect; pauses for native approval before settling."""
        return f"published {article_id}"

    # Skill LIBRARY root (contains skill packages, one directory per skill,
    # each holding SKILL.md) — the Skills primitive's directories contract.
    skill_library = Path(__file__).parent / "skills"
    return PluginBundle(toolsets=[toolset], skill_dirs=[skill_library])


# Distinct entry-point value resolving to the same factory — used to prove an
# entry-point change alters the composition id.
create_plugin_alias = create_plugin
