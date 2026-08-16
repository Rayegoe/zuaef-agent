"""Plugin Composition Layer contract types.

A plugin is an installed Python distribution exposing one factory per
``zuaef.plugins`` entry point; a factory receives a frozen {@link PluginEnv}
and returns one {@link PluginBundle}. A bundle only packages the existing
primitives — Toolset, Skill directory, explicitly allowed Capability — and
degrades to ``build_agent(extra_toolsets=..., extra_capabilities=...)``.
There is no plugin runtime: no agent registry, no event bus, no second
approval or receipt store.

The composition identity for receipts and resume lives in
{@link CompositionSnapshot}; its {@link CompositionSnapshot.composition_id}
is a SHA-256 over the canonical serialization of every identity-relevant
fact (profile, plugin id, version, entry point, non-secret config, order,
capability permission).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.toolsets import AbstractToolset

    from .models import CoreDeps


class CompositionError(ValueError):
    """A pre-run composition problem: invalid profile, unresolvable or
    misbehaving plugin, unauthorized capability, tool conflict, or resume
    version mismatch. Process error: no receipt is written.
    """


@dataclass(frozen=True)
class PluginEnv:
    """Environment handed to a plugin factory. Deliberately thin: identity,
    workspace and state roots only — never the Agent, credentials, or a
    mutable runtime handle that could become a hidden DI container.
    """

    plugin_id: str
    plugin_version: str
    workspace_root: Path
    state_root: Path


@dataclass(frozen=True)
class PluginBundle:
    """The only output v0.2 allows a factory to return.

    Toolsets and Skills are allowed by default; Capabilities are denied
    unless the profile explicitly sets ``allow_capabilities = true``.
    Adding hooks/middleware/events/services/background tasks here is
    deliberately impossible — the dataclass has no fields for them.
    """

    toolsets: Sequence[AbstractToolset[CoreDeps]] = ()
    skill_dirs: Sequence[Path] = ()
    capabilities: Sequence[AbstractCapability[CoreDeps]] = ()


class PluginRef(BaseModel):
    """One frozen plugin entry inside a CompositionSnapshot."""

    id: str
    version: str
    entry_point: str
    config: dict[str, Any] = Field(default_factory=dict)
    capabilities_allowed: bool = False


class CompositionSnapshot(BaseModel):
    """Frozen, receipt-visible identity of one composed run.

    A snapshot is the single authority for resume: a continued run must
    reproduce the exact plugin versions, entry points and config recorded
    here, ignoring whatever the current profile says.
    """

    schema_version: Literal["1"] = "1"
    profile: str | None = None
    plugins: list[PluginRef] = Field(default_factory=list)
    composition_id: str


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_composition_id(
    *,
    profile: str | None,
    plugins: Sequence[PluginRef],
) -> str:
    """SHA-256 of the canonical composition payload.

    The payload covers every fact that must change the hash: profile, plugin
    id, plugin version, entry point, non-secret config, plugin order, and
    capability permission. A non-JSON-serializable config value is a
    composition error — the snapshot must always be JSON-safe.
    """
    try:
        payload = _canonical_json(
            {
                "schema_version": "1",
                "profile": profile,
                "plugins": [
                    {
                        "id": ref.id,
                        "version": ref.version,
                        "entry_point": ref.entry_point,
                        "config": ref.config,
                        "capabilities_allowed": ref.capabilities_allowed,
                    }
                    for ref in plugins
                ],
            }
        )
    except (TypeError, ValueError) as exc:
        raise CompositionError(
            f"plugin config is not JSON-serializable: {exc}"
        ) from exc
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
