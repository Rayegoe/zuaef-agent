"""Plugin factory for the Client Service Decision Slice (SPEC v0.1 §20-22).

Responsibilities only: parse config, resolve slice_root, build the store and
toolset, return skill dirs, return the PluginBundle. No model calls, no
side-effect reads of customer data at factory time, no agent creation, no
threads/servers/event bus (§21). Corpus validation fails loud pre-run so a
broken slice_root surfaces as a composition process error (§47 blocked), not
as a mid-run fabrication.
"""

from __future__ import annotations

import os
from pathlib import Path

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .store import ClientServiceStore, CorpusError
from .toolset import build_client_service_toolset

DEFAULT_SLICE_ROOT = Path.home() / ".local/share/zuaef/client-service"
_SKILLS_DIR = Path(__file__).parent / "skills"


def _resolve_slice_root(config: dict) -> Path:
    """Explicit config wins, then ZUAEF_CLIENT_SERVICE_ROOT, then the default.

    The root must exist and carry the evidence ledger; anything else is a
    pre-run process error (§22 config carries no secrets; slice_root points
    at the private corpus which never enters the public repo).
    """
    raw = (
        config.get("slice_root")
        or os.environ.get("ZUAEF_CLIENT_SERVICE_ROOT")
        or DEFAULT_SLICE_ROOT
    )
    slice_root = Path(raw).expanduser().resolve()
    if not slice_root.is_dir():
        raise CompositionError(f"slice_root missing: {slice_root}")
    if not (slice_root / "evidence" / "evidence_ledger.jsonl").is_file():
        raise CompositionError(
            f"slice_root has no evidence/evidence_ledger.jsonl: {slice_root}"
        )
    return slice_root


def build_plugin(env: PluginEnv, config: dict) -> PluginBundle:
    """Compose the Client Service plugin (SPEC §20)."""
    slice_root = _resolve_slice_root(config)
    try:
        store = ClientServiceStore(slice_root)
    except CorpusError as exc:
        raise CompositionError(f"corpus unavailable: {exc}") from exc
    domain = config.get("domain", "beauty-content")
    toolset = build_client_service_toolset(
        store,
        plugin_id=env.plugin_id,
        plugin_version=env.plugin_version,
        domain=domain,
    )
    if not (_SKILLS_DIR / "client-service" / "SKILL.md").is_file():
        raise CompositionError(f"plugin skills missing: {_SKILLS_DIR}")
    return PluginBundle(toolsets=[toolset], skill_dirs=[_SKILLS_DIR])
