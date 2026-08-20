"""``ace-writing`` plugin factory.

Config wiring only: the writing domain adapter is the byte-identical copy in
``.writing_toolset`` (provenance in its docstring); ACE stays the external
Context Engine. All host-side prep (ingest, gate) and settlement stay in the
proof drivers, not in the plugin.

Editorial control (SPEC ``zuaef-editorial-control-v0.1``) was REMOVED from the
production surface in v1.2 T014B: it showed no stable advantage in the Phase 9
blind A/B and its sensor-driven save veto is a machine gate on taste, which
the v1.2 architecture forbids as semantic authority. The capability, sensors
and evidence rows survive as benchmark/legacy assets under
``benchmarks/editorial-learning/legacy/`` (QUALITY_LOOP §11); any
``editorial_*`` config key now fails composition loudly so a stale profile
cannot silently re-enable it.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_ai_harness.code_mode import CodeMode

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .writing_toolset import DEFAULT_ACE_ROOT, build_writing_toolset


def _resolve_ace_root(config: dict) -> Path:
    """Explicit profile config wins, then ACE_ROOT, then the compiled default.

    A missing ``tools/ctx.py`` is a pre-run process error: the plugin cannot
    deliver anything without the Context Engine, so fail loud at composition
    time instead of on the first tool call.
    """
    raw = config.get("ace_root") or os.environ.get("ACE_ROOT") or DEFAULT_ACE_ROOT
    ace_root = Path(raw).expanduser().resolve()
    if not (ace_root / "tools" / "ctx.py").is_file():
        raise CompositionError(
            f"ace_root has no tools/ctx.py — is the article-context-engine "
            f"checked out at {ace_root}?"
        )
    return ace_root


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Assemble the ACE writing plugin from config (SPEC §34 + Writing v0.2
    CodeMode).

    Returns exactly one toolset, plus capabilities that config opt-ins:
    - ``code_mode = true`` -> Harness CodeMode wrapping the observe tools
      tagged ``code_mode=True`` (list/read/retrieve/check), leaving
      ``save_artifact`` as a normal explicit tool call (Writing SPEC §10).

    No skills are shipped by the plugin; writing skills live in the repo's
    skill library (``.agents/skills``).
    """
    stale = sorted(k for k in config if k.startswith("editorial_"))
    if stale:
        raise CompositionError(
            f"editorial control was removed from the production plugin in "
            f"v1.2 T014B; unknown editorial config key(s): {', '.join(stale)}. "
            "The capability is benchmark/legacy only — see "
            "benchmarks/editorial-learning/legacy/README.md."
        )
    ace_root = _resolve_ace_root(config)
    toolset = build_writing_toolset(ace_root)
    capabilities: list[CodeMode] = []
    if config.get("code_mode", False) is True:
        capabilities.append(
            CodeMode(
                tools={"code_mode": True},
                max_retries=3,
            )
        )
    if not capabilities:
        return PluginBundle(toolsets=[toolset])
    return PluginBundle(toolsets=[toolset], capabilities=capabilities)
