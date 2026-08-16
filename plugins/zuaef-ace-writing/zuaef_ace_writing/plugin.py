"""``ace-writing`` plugin factory.

Config wiring only: the writing domain adapter is the byte-identical copy in
``.writing_toolset`` (provenance in its docstring); ACE stays the external
Context Engine. All host-side prep (ingest, gate) and settlement stay in the
proof drivers, not in the plugin.
"""

from __future__ import annotations

import os
from pathlib import Path

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
    """Assemble the ACE writing plugin from config (SPEC §34).

    Returns exactly one toolset; no skills, no capabilities — the profile's
    capability policy is irrelevant here because nothing is requested.
    """
    ace_root = _resolve_ace_root(config)
    return PluginBundle(toolsets=[build_writing_toolset(ace_root)])
