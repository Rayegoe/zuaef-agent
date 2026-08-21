"""``ace-writing`` production plugin factory.

ACE remains the material store. The plugin compresses that world into bounded
writer context and exposes only ``pull_context`` and ``save_article``.

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

from .writing_toolset import (
    DEFAULT_ACE_ROOT,
    DEFAULT_CORPUS_ROOT,
    TECHNIQUE_SELECTION_MODES,
    build_writing_toolset,
)


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


def _resolve_corpus_root(config: dict) -> Path:
    """Resolve the optional file-native corpus without requiring it to exist."""
    raw = (
        config.get("corpus_root")
        or os.environ.get("WRITING_CORPUS_ROOT")
        or DEFAULT_CORPUS_ROOT
    )
    corpus_root = Path(raw).expanduser().resolve()
    if corpus_root.exists() and not corpus_root.is_dir():
        raise CompositionError(f"corpus_root is not a directory: {corpus_root}")
    return corpus_root


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Assemble one small writing environment from deployment paths."""
    stale = sorted(k for k in config if k.startswith("editorial_"))
    if stale:
        raise CompositionError(
            f"editorial control was removed from the production plugin in "
            f"v1.2 T014B; unknown editorial config key(s): {', '.join(stale)}. "
            "The capability is benchmark/legacy only — see "
            "benchmarks/editorial-learning/legacy/README.md."
        )
    ace_root = _resolve_ace_root(config)
    corpus_root = _resolve_corpus_root(config)
    learning_root = Path(
        config.get("learning_root") or env.workspace_root.parent / "learning"
    ).expanduser().resolve()
    include_technique_guidance = config.get("include_technique_guidance", True)
    if not isinstance(include_technique_guidance, bool):
        raise CompositionError(
            "include_technique_guidance must be a boolean when configured"
        )
    technique_selection_mode = config.get("technique_selection_mode", "host")
    if technique_selection_mode not in TECHNIQUE_SELECTION_MODES:
        raise CompositionError(
            "technique_selection_mode must be one of "
            f"{TECHNIQUE_SELECTION_MODES}, got {technique_selection_mode!r}"
        )
    if technique_selection_mode != "host" and not include_technique_guidance:
        raise CompositionError(
            "include_technique_guidance=false cannot be combined with "
            f"technique_selection_mode={technique_selection_mode!r}"
        )
    toolset = build_writing_toolset(
        ace_root,
        learning_root=learning_root,
        corpus_root=corpus_root,
        include_technique_guidance=include_technique_guidance,
        technique_selection_mode=technique_selection_mode,
    )
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
