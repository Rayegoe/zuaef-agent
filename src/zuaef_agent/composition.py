"""Plugin resolution, composition and agent assembly.

Implements the §14 pipeline without ever touching the model: resolving a
profile, loading enabled factories, validating bundles, enforcing the
capability policy, detecting tool conflicts, and freezing a
CompositionSnapshot is all pre-run work (``profile check`` runs it with no
credentials).

The same {@link build_agent_from_snapshot} path composes a new run after
resolve and a resumed run from a frozen snapshot, which is what makes resume
ignore the mutable current profile: the snapshot is the only authority, and
an installed plugin whose version or entry point no longer matches the
snapshot is a pre-run process error.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext, RunUsage

from .config import AgentSettings
from .core import build_agent
from .models import CoreDeps
from .plugin_api import (
    CompositionError,
    CompositionSnapshot,
    PluginBundle,
    PluginEnv,
    PluginRef,
    compute_composition_id,
)
from .profiles import load_profile

PLUGIN_GROUP = "zuaef.plugins"

Discover = Callable[[], Mapping[str, EntryPoint]]
VersionFor = Callable[[EntryPoint], str]


def discover_entry_points() -> Mapping[str, EntryPoint]:
    """Installed ``zuaef.plugins`` entry points keyed by plugin id.

    Reads package metadata only — nothing is imported, so an installed-but-
    disabled plugin can never execute code from discovery alone.
    """
    return {ep.name: ep for ep in entry_points(group=PLUGIN_GROUP)}


def version_for(ep: EntryPoint) -> str:
    """Plugin version from the distribution that declares the entry point."""
    return ep.dist.version if ep.dist is not None else "<unknown>"


def installed_plugins(
    *,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> list[tuple[str, str]]:
    """(id, version) of every installed plugin, sorted by id.

    Installed means discoverable, never enabled — enabling happens only in a
    profile. No plugin module is imported.
    """
    return sorted((pid, version_for(ep)) for pid, ep in discover().items())


def inspect_plugin(
    plugin_id: str,
    *,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> tuple[str, str, str]:
    """(id, version, entry point value) of one installed plugin, metadata only."""
    ep = discover().get(plugin_id)
    if ep is None:
        raise CompositionError(
            f"plugin {plugin_id!r} is not installed (no {PLUGIN_GROUP} entry point)"
        )
    return plugin_id, version_for(ep), ep.value


def _environment(settings: AgentSettings) -> tuple[Path, Path]:
    return (
        settings.workspace_root.resolve(),
        settings.state_root.resolve(),
    )


def _load_factory(
    plugin_id: str,
    entry_point: EntryPoint,
    version: str,
    *,
    settings: AgentSettings,
    config: Mapping[str, Any],
) -> PluginBundle:
    """Import ONE enabled plugin factory and validate its bundle.

    ``entry_point.load()`` is the only place plugin code is imported; callers
    only reach this for plugins a profile or snapshot explicitly enables.
    """
    factory = entry_point.load()
    if not callable(factory):
        raise CompositionError(
            f"plugin {plugin_id!r} entry point does not resolve to a factory "
            f"callable: {entry_point.value!r}"
        )
    workspace_root, state_root = _environment(settings)
    env = PluginEnv(
        plugin_id=plugin_id,
        plugin_version=version,
        workspace_root=workspace_root,
        state_root=state_root,
    )
    try:
        bundle = factory(env, dict(config))
    except CompositionError:
        raise
    except Exception as exc:
        raise CompositionError(
            f"plugin {plugin_id!r} factory failed: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(bundle, PluginBundle):
        raise CompositionError(
            f"plugin {plugin_id!r} factory must return a PluginBundle, got "
            f"{type(bundle).__name__}"
        )
    return bundle


def _check_skill_dirs(ref: PluginRef, bundle: PluginBundle) -> None:
    for directory in bundle.skill_dirs:
        resolved = Path(directory).expanduser()
        if not resolved.is_dir():
            raise CompositionError(
                f"plugin {ref.id!r} skill dir does not exist: {directory}"
            )


def _check_capability_policy(ref: PluginRef, bundle: PluginBundle) -> None:
    if bundle.capabilities and not ref.capabilities_allowed:
        raise CompositionError(
            f"plugin {ref.id!r} returns capabilities but the profile does not "
            f"allow them (set allow_capabilities = true to enable)"
        )


async def _tool_names(toolset: Any, deps: CoreDeps) -> set[str]:
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    return set(await toolset.get_tools(ctx))


def _check_tool_conflicts(
    refs: Sequence[PluginRef],
    bundles: Sequence[PluginBundle],
    deps: CoreDeps,
) -> None:
    """Every tool name must be owned by exactly one plugin; a duplicate is a
    composition error, never a silent override."""
    owners: dict[str, str] = {}
    for ref, bundle in zip(refs, bundles):
        for toolset in bundle.toolsets:
            try:
                names = asyncio.run(_tool_names(toolset, deps))
            except Exception as exc:
                raise CompositionError(
                    f"plugin {ref.id!r} toolset failed to enumerate tools: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            for name in names:
                _claim(owners, ref.id, name)
        for capability in bundle.capabilities:
            toolset = capability.get_toolset()
            if toolset is None:
                continue
            try:
                names = asyncio.run(_tool_names(toolset, deps))
            except Exception as exc:
                raise CompositionError(
                    f"plugin {ref.id!r} capability failed to enumerate tools: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            for name in names:
                _claim(owners, ref.id, name)


def _claim(owners: dict[str, str], plugin_id: str, tool_name: str) -> None:
    existing = owners.get(tool_name)
    if existing is not None and existing != plugin_id:
        raise CompositionError(
            f"tool conflict: {tool_name!r} is provided by both {existing!r} "
            f"and {plugin_id!r}; no silent override"
        )
    owners[tool_name] = plugin_id


def _resolve_bundles(
    refs: Sequence[PluginRef],
    *,
    settings: AgentSettings,
    discover: Discover,
    version_for: VersionFor,
) -> list[PluginBundle]:
    """Load every enabled plugin's factory and validate its bundle against the
    plugin's (possibly frozen) reference. Installed-but-unlisted plugins are
    never imported here."""
    installed = discover()
    bundles: list[PluginBundle] = []
    for ref in refs:
        ep = installed.get(ref.id)
        if ep is None:
            raise CompositionError(
                f"plugin {ref.id!r} is not installed (no {PLUGIN_GROUP} entry point)"
            )
        if ep.value != ref.entry_point:
            raise CompositionError(
                f"plugin {ref.id!r}: snapshot requires entry point "
                f"{ref.entry_point!r} but installed entry point is {ep.value!r}"
            )
        version = version_for(ep)
        if version != ref.version:
            raise CompositionError(
                f"plugin {ref.id!r}: composition requires version {ref.version!r} "
                f"but installed version is {version!r}; automatic upgrade is "
                "not allowed"
            )
        bundle = _load_factory(
            ref.id,
            ep,
            ref.version,
            settings=settings,
            config=ref.config,
        )
        _check_capability_policy(ref, bundle)
        _check_skill_dirs(ref, bundle)
        bundles.append(bundle)
    return bundles


def _freeze(refs: Sequence[PluginRef], profile: str | None) -> CompositionSnapshot:
    return CompositionSnapshot(
        profile=profile,
        plugins=list(refs),
        composition_id=compute_composition_id(profile=profile, plugins=refs),
    )


def resolve_profile(
    name: str,
    settings: AgentSettings,
    *,
    config_root: Path | None = None,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> CompositionSnapshot:
    """Full §14 pipeline for one profile: parse, validate, resolve enabled
    plugin ids to exactly one entry point each, load factories, validate
    bundles, enforce the capability policy and tool-conflict rules, and freeze
    a snapshot. No model request happens here.
    """
    profile = load_profile(name, config_root)
    installed = discover()
    refs: list[PluginRef] = []
    for plugin in profile.plugins:
        ep = installed.get(plugin.id)
        if ep is None:
            raise CompositionError(
                f"plugin {plugin.id!r} is not installed (no {PLUGIN_GROUP} "
                f"entry point)"
            )
        version = version_for(ep)
        refs.append(
            PluginRef(
                id=plugin.id,
                version=version,
                entry_point=ep.value,
                config=dict(plugin.config),
                capabilities_allowed=plugin.allow_capabilities,
            )
        )
    bundles = _resolve_bundles(
        refs, settings=settings, discover=discover, version_for=version_for
    )
    _check_tool_conflicts(
        refs,
        bundles,
        CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=""),
    )
    return _freeze(refs, profile.name)


def build_agent_from_snapshot(
    settings: AgentSettings,
    *,
    run_id: str | None = None,
    snapshot: CompositionSnapshot,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> Agent[CoreDeps, Any]:
    """Compose an agent exactly from a frozen snapshot — the resume authority.

    The current profile is never consulted. Version or entry-point drift
    between the snapshot and the installed environment fails here, before any
    model request.
    """
    bundles = _resolve_bundles(
        snapshot.plugins,
        settings=settings,
        discover=discover,
        version_for=version_for,
    )
    _check_tool_conflicts(
        snapshot.plugins,
        bundles,
        CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=""),
    )
    toolsets = [ts for bundle in bundles for ts in bundle.toolsets]
    capabilities = [cap for bundle in bundles for cap in bundle.capabilities]
    skill_dirs = [d for bundle in bundles for d in bundle.skill_dirs]
    return build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=toolsets,
        extra_capabilities=capabilities,
        extra_skill_dirs=skill_dirs,
    )


def build_profile_agent(
    settings: AgentSettings,
    *,
    run_id: str | None = None,
    profile: str | None = None,
    snapshot: CompositionSnapshot | None = None,
    config_root: Path | None = None,
    discover: Discover = discover_entry_points,
    version_for: VersionFor = version_for,
) -> tuple[
    Agent[CoreDeps, Any],
    CompositionSnapshot | None,
]:
    """Public composition API: build an agent from a profile (resolve-then-
    freeze) or from a frozen snapshot (exact). Passing both is an error;
    passing neither keeps the current no-profile behavior.

    Returns the composed agent and the snapshot it was frozen from (None when
    no profile/snapshot was involved), so callers can thread the snapshot
    into the receipt.
    """
    if profile is not None and snapshot is not None:
        raise CompositionError("pass either profile or snapshot, not both")
    if snapshot is None:
        if profile is None:
            return build_agent(settings, run_id=run_id), None
        snapshot = resolve_profile(
            profile,
            settings,
            config_root=config_root,
            discover=discover,
            version_for=version_for,
        )
    agent = build_agent_from_snapshot(
        settings,
        run_id=run_id,
        snapshot=snapshot,
        discover=discover,
        version_for=version_for,
    )
    return agent, snapshot
