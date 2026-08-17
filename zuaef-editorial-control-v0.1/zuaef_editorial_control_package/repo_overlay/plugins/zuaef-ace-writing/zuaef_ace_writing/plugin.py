"""``ace-writing`` plugin factory.

The verified ACE toolset remains the domain adapter. Cognitive Editorial Control
is an optional cross-cutting PydanticAI capability: it never duplicates ACE
materials/evidence/artifact semantics and never writes the article itself.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .editorial_control import EditorialControlCapability
from .editorial_evidence import EditorialEvidenceStore
from .writing_toolset import DEFAULT_ACE_ROOT, build_writing_toolset


def _resolve_ace_root(config: dict) -> Path:
    """Explicit profile config wins, then ACE_ROOT, then the compiled default."""
    raw = config.get("ace_root") or os.environ.get("ACE_ROOT") or DEFAULT_ACE_ROOT
    ace_root = Path(raw).expanduser().resolve()
    if not (ace_root / "tools" / "ctx.py").is_file():
        raise CompositionError(
            f"ace_root has no tools/ctx.py — is the article-context-engine "
            f"checked out at {ace_root}?"
        )
    return ace_root


def _as_bool(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise CompositionError(f"{key} must be a boolean")


def _optional_path(raw: Any, *, base: Path) -> Path | None:
    if raw in (None, ""):
        candidate = base / "editorial" / "evidence.jsonl"
        return candidate if candidate.is_file() else None
    return Path(str(raw)).expanduser().resolve()


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Assemble ACE Writing toolset plus optional Editorial Control capability.

    The profile must explicitly opt into plugin capabilities with
    ``allow_capabilities = true``. This is intentional: enabling a lifecycle
    hook changes runtime behavior and must be composition-visible/resume-frozen.
    """

    ace_root = _resolve_ace_root(config)
    toolset = build_writing_toolset(ace_root)

    if not _as_bool(config, "editorial_control", True):
        return PluginBundle(toolsets=[toolset])

    evidence_path = _optional_path(
        config.get("editorial_evidence_path"),
        base=env.state_root,
    )
    try:
        evidence_store = EditorialEvidenceStore.load(evidence_path)
    except ValueError as exc:
        raise CompositionError(str(exc)) from exc

    capability = EditorialControlCapability(
        id="ace-writing.editorial-control",
        description=(
            "Evidence-backed cognitive editorial control for nonfiction drafting. "
            "Applies bounded run-time interventions and one pre-save veto."
        ),
        evidence_store=evidence_store,
        max_injections=int(config.get("editorial_max_injections", 4)),
        max_save_vetoes=int(config.get("editorial_max_save_vetoes", 1)),
        evidence_limit=int(config.get("editorial_evidence_limit", 3)),
        veto_threshold=float(config.get("editorial_veto_threshold", 1.50)),
        temperature_nudge=float(config.get("editorial_temperature_nudge", 0.0)),
        base_temperature=(
            float(config["editorial_base_temperature"])
            if config.get("editorial_base_temperature") not in (None, "")
            else None
        ),
    )
    return PluginBundle(toolsets=[toolset], capabilities=[capability])
