"""Fixture broken plugins: a raising factory and a factory returning a
non-PluginBundle value."""

from __future__ import annotations

from zuaef_agent.plugin_api import PluginEnv


def create_plugin(env: PluginEnv, config: dict) -> object:
    raise RuntimeError("fixture factory boom")


def create_invalid(env: PluginEnv, config: dict) -> object:
    return {"toolsets": []}
