"""``zuaef-emtb-budget`` plugin factory.

Config wiring only: the budget domain library lives in ``.budget_lib``
(provenance in its docstring — faithful extraction of zesenticai
finance_agent). No profile config is required; ``config`` is accepted and
ignored (the domain has no secrets or endpoint settings).

The toolset's only write effect is ``save_budget_report`` (local_write under
the ZUAEF workspace artifacts dir, host-verified). Nothing here adds
platform machinery: the factory returns exactly one PluginBundle.
"""

from __future__ import annotations

from zuaef_agent.plugin_api import PluginBundle, PluginEnv

from .toolset import build_budget_toolset

# Observability for tests: record what the factory received.
last_env: PluginEnv | None = None
last_config: dict | None = None


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Assemble the EMTB budget plugin (Stage 6A).

    Returns exactly one toolset; no skills, no capabilities.
    """
    global last_env, last_config
    last_env = env
    last_config = dict(config)
    return PluginBundle(toolsets=[build_budget_toolset()])
