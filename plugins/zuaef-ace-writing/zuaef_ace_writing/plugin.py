"""``ace-writing`` plugin factory.

Config wiring only: the writing domain adapter is the byte-identical copy in
``.writing_toolset`` (provenance in its docstring); ACE stays the external
Context Engine. All host-side prep (ingest, gate) and settlement stay in the
proof drivers, not in the plugin.

Editorial control (SPEC ``zuaef-editorial-control-v0.1``, plugin 0.2.0): when
``editorial_control = true`` the bundle additionally carries exactly one
capability, ``EditorialControlCapability`` — a runtime cognitive editorial
feedback loop over the unchanged writing toolset. The profile must set
``allow_capabilities = true`` or composition fails loudly (Plugin Composition
Layer policy). With ``editorial_control`` unset/false the bundle keeps the
0.1.0 shape: one toolset, no capabilities.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic_ai_harness.code_mode import CodeMode

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .editorial import (
    EditorialControlCapability,
    EditorialEvidenceStore,
    EditorialSettings,
)
from .writing_toolset import DEFAULT_ACE_ROOT, build_writing_toolset

DEFAULT_EVIDENCE_PATH = Path.home() / ".config" / "zuaef" / "editorial" / "evidence.jsonl"

_EDITORIAL_INT_KEYS = ("editorial_max_injections", "editorial_max_save_vetoes", "editorial_evidence_limit")
_EDITORIAL_FLOAT_KEYS = ("editorial_veto_threshold", "editorial_temperature_nudge", "editorial_base_temperature")
_KNOWN_EDITORIAL_KEYS = frozenset(
    {"editorial_control", "editorial_evidence_path", *_EDITORIAL_INT_KEYS, *_EDITORIAL_FLOAT_KEYS}
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


def _editorial_settings(config: dict) -> EditorialSettings:
    """Parse the ``editorial_*`` config block; typo or type error fails loud.

    Non-editorial keys (``ace_root``) are not this function's business — only
    ``editorial_*`` keys are validated here.
    """
    unknown = sorted(k for k in config if k.startswith("editorial_") and k not in _KNOWN_EDITORIAL_KEYS)
    if unknown:
        raise CompositionError(
            f"unknown editorial config key(s): {', '.join(unknown)} — known "
            f"keys: {', '.join(sorted(_KNOWN_EDITORIAL_KEYS))}"
        )
    parsed: dict[str, Any] = {}
    for key in _EDITORIAL_INT_KEYS:
        if key in config:
            value = config[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CompositionError(f"{key} must be a non-negative integer, got {value!r}")
            parsed[key.removeprefix("editorial_")] = value
    for key in _EDITORIAL_FLOAT_KEYS:
        if key in config:
            value = config[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise CompositionError(f"{key} must be a number, got {value!r}")
            parsed[key.removeprefix("editorial_")] = float(value)
    evidence_path: Path | None = DEFAULT_EVIDENCE_PATH
    if "editorial_evidence_path" in config:
        evidence_path = Path(str(config["editorial_evidence_path"])).expanduser()
    return EditorialSettings(evidence_path=evidence_path, **parsed)


def create_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Assemble the ACE writing plugin from config (SPEC §34 + editorial v0.1
    + Writing v0.2 CodeMode).

    Returns exactly one toolset, plus capabilities that config opt-ins:
    - ``editorial_control = true``  -> EditorialControlCapability
    - ``code_mode = true``          -> Harness CodeMode wrapping the observe
      tools tagged ``code_mode=True`` (list/read/retrieve/check), leaving
      ``save_artifact`` as a normal explicit tool call (Writing SPEC §10).

    No skills are shipped by the plugin; writing skills live in the repo's
    skill library (``.agents/skills``).
    """
    ace_root = _resolve_ace_root(config)
    toolset = build_writing_toolset(ace_root)
    capabilities: list[Any] = []
    if config.get("editorial_control", False) is True:
        settings = _editorial_settings(config)
        store = EditorialEvidenceStore(settings.evidence_path)
        capabilities.append(EditorialControlCapability(settings=settings, store=store))
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
