"""zuaef-case plugin factory — SPEC v0.3 FDE Platform §8/§12.

Validates config, resolves the cases root (explicit config >
``workspace/cases`` default; must live inside the workspace) and composes the
case toolset over one CaseStore. No model calls, no corpus access, no threads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .store import CaseStore
from .toolset import build_case_toolset


def create_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    raw = config.get("cases_root") or env.workspace_root / "cases"
    cases_root = Path(raw).expanduser().resolve()
    if not cases_root.is_relative_to(env.workspace_root.resolve()):
        raise CompositionError(
            f"cases_root must live inside the workspace: {cases_root}"
        )
    store = CaseStore(cases_root)
    return PluginBundle(toolsets=[build_case_toolset(store)])
