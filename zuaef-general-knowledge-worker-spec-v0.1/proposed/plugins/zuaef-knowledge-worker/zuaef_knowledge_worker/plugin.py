from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai_harness import YouResearch, YouSearch
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .document_tools import make_document_toolset

_ALLOWED_SEARCH_MODES = {"highlights", "full_page"}
_ALLOWED_RESEARCH_EFFORTS = {"lite", "standard", "deep", "exhaustive"}
_ALLOWED_FINANCE_EFFORTS = {"deep", "exhaustive"}


def _int_value(config: dict[str, Any], key: str, default: int, minimum: int = 1) -> int:
    raw = config.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise CompositionError(f"knowledge-worker config {key!r} must be an integer") from exc
    if value < minimum:
        raise CompositionError(f"knowledge-worker config {key!r} must be >= {minimum}")
    return value


def _bool_value(config: dict[str, Any], key: str, default: bool) -> bool:
    raw = config.get(key, default)
    if isinstance(raw, bool):
        return raw
    raise CompositionError(f"knowledge-worker config {key!r} must be a boolean")


def _choice(config: dict[str, Any], key: str, default: str, allowed: set[str]) -> str:
    value = str(config.get(key, default)).strip()
    if value not in allowed:
        raise CompositionError(
            f"knowledge-worker config {key!r} must be one of {sorted(allowed)}"
        )
    return value


def build_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    search_results = _int_value(config, "search_results", 6)
    if search_results > 20:
        raise CompositionError("knowledge-worker search_results must be <= 20")

    search_mode = _choice(config, "search_mode", "highlights", _ALLOWED_SEARCH_MODES)
    page_chars = _int_value(config, "page_chars", 12_000)
    research_enabled = _bool_value(config, "research_enabled", True)
    research_effort = _choice(
        config, "research_effort", "standard", _ALLOWED_RESEARCH_EFFORTS
    )
    finance_effort = _choice(
        config, "finance_effort", "deep", _ALLOWED_FINANCE_EFFORTS
    )
    document_chunk_chars = _int_value(config, "document_chunk_chars", 12_000)
    document_max_bytes = _int_value(config, "document_max_bytes", 25_000_000)

    capabilities = [
        YouSearch(
            num_results=search_results,
            extraction_mode=search_mode,
            max_text_chars=page_chars,
        )
    ]
    if research_enabled:
        capabilities.append(
            YouResearch(
                research_effort=research_effort,
                finance_effort=finance_effort,
            )
        )

    skills_root = Path(__file__).parent / "skills"
    skill_dirs = [skills_root] if skills_root.is_dir() else []

    return PluginBundle(
        capabilities=capabilities,
        toolsets=[
            make_document_toolset(
                workspace_root=env.workspace_root,
                chunk_chars=document_chunk_chars,
                max_bytes=document_max_bytes,
            )
        ],
        skill_dirs=skill_dirs,
    )
