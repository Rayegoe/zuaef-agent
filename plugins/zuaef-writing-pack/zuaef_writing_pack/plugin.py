"""Composition-only adapter for the external writing intelligence pack.

The pack owns Skills, corpus configuration, and mechanical CLI commands. This
plugin only resolves those paths and exposes the three read-only commands as a
native zuaef-agent toolset. It contains no writing policy or semantic ranking.
"""

from __future__ import annotations

import os
from pathlib import Path

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .toolset import build_sanlian_toolset

DEFAULT_PACK_ROOT = Path.home() / "zuaef_writing"
SKILL_NAME = "sanlian-editorial-reading"
COMMAND_NAMES = ("sanlian_catalog.py", "sanlian_search.py", "sanlian_read.py")


def _resolve_pack_root(config: dict) -> Path:
    raw = config.get("pack_root") or os.environ.get("ZUAEF_WRITING_PACK_ROOT")
    root = Path(raw).expanduser() if raw else DEFAULT_PACK_ROOT
    root = root.resolve()
    if not root.is_dir():
        raise CompositionError(
            "writing pack missing; set plugins.config.pack_root or "
            f"ZUAEF_WRITING_PACK_ROOT: {root}"
        )
    skills_dir = root / "skills"
    skill_file = skills_dir / SKILL_NAME / "SKILL.md"
    if not skill_file.is_file():
        raise CompositionError(f"writing pack skill missing: {skill_file}")
    commands_dir = skills_dir / SKILL_NAME / "commands"
    missing = [name for name in COMMAND_NAMES if not (commands_dir / name).is_file()]
    if missing:
        raise CompositionError(
            f"writing pack commands missing under {commands_dir}: {', '.join(missing)}"
        )
    collections_file = root / "corpus" / "collections.toml"
    if not collections_file.is_file():
        raise CompositionError(f"writing pack collections file missing: {collections_file}")
    return root


def _optional_path(config: dict, key: str, env_name: str, default: Path) -> Path:
    raw = config.get(key) or os.environ.get(env_name)
    return Path(raw).expanduser().resolve() if raw else default.resolve()


def build_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Expose the external pack without adding a new capability layer."""

    pack_root = _resolve_pack_root(config)
    skills_dir = pack_root / "skills"
    collections_file = _optional_path(
        config,
        "collections_file",
        "ZUAEF_WRITING_COLLECTIONS_FILE",
        pack_root / "corpus" / "collections.toml",
    )
    manifest_file = _optional_path(
        config,
        "manifest_file",
        "ZUAEF_WRITING_MANIFEST_FILE",
        pack_root / "corpus" / "manifest.jsonl",
    )
    corpus_dir = config.get("corpus_dir") or os.environ.get("ZUAEF_WRITING_CORPUS_DIR")
    return PluginBundle(
        toolsets=[
            build_sanlian_toolset(
                pack_root,
                collections_file=collections_file,
                manifest_file=manifest_file,
                corpus_dir=corpus_dir,
            )
        ],
        skill_dirs=[skills_dir],
    )
