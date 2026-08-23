"""Plugin factory — deterministic composition, no model call at factory time.

Config (non-secret only):
    domain            validated but business-neutral (tool guidance hint)
    search_backend    "brave" (production) | "fixture" (tests/CI)
    output_language   report language preference (e.g. "zh-CN")
    max_search_results
    max_fetch_bytes
    max_preview_chars

Secret (environment only, never in profile/snapshot/receipt/tool result):
    ZUAEF_BRAVE_SEARCH_API_KEY  (fallback: BRAVE_API_KEY)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .report_tools import make_report_toolset
from .search_backend import (
    BRAVE_SECRET_ENV,
    BRAVE_SECRET_ENV_FALLBACK,
    BraveSearchBackend,
    FixtureSearchBackend,
    SearchBackend,
)
from .source_tools import make_source_toolset
from .work_product_tools import make_work_product_toolset

SUPPORTED_BACKENDS = ("brave", "fixture")
DEFAULT_MAX_SEARCH_RESULTS = 10
DEFAULT_MAX_FETCH_BYTES = 10_000_000
DEFAULT_MAX_PREVIEW_CHARS = 14_000

def _config_int(config: dict[str, Any], key: str, default: int) -> int:
    raw = config.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise CompositionError(
            f"competitive-intelligence config {key!r} must be an integer, "
            f"got {raw!r}"
        ) from exc
    if value <= 0:
        raise CompositionError(
            f"competitive-intelligence config {key!r} must be > 0"
        )
    return value


def _build_backend(
    name: str, config: dict[str, Any]
) -> tuple[SearchBackend, str]:
    if name not in SUPPORTED_BACKENDS:
        raise CompositionError(
            f"competitive-intelligence: unsupported search_backend {name!r} "
            f"(supported: {', '.join(SUPPORTED_BACKENDS)})"
        )
    if name == "fixture":
        fixture_hits = config.get("fixture_hits")
        if fixture_hits is None:
            raise CompositionError(
                "competitive-intelligence: fixture backend requires "
                "non-secret config 'fixture_hits' (query -> [hits])"
            )
        if not isinstance(fixture_hits, dict):
            raise CompositionError(
                "competitive-intelligence: fixture_hits must be a mapping"
            )
        return (
            FixtureSearchBackend(fixture_hits),
            "fixture",
        )
    secret = BraveSearchBackend.secret_from_env()
    if not secret:
        raise CompositionError(
            "competitive-intelligence: Brave backend selected but no API key "
            f"in environment ({BRAVE_SECRET_ENV} or {BRAVE_SECRET_ENV_FALLBACK})"
        )
    return (
        BraveSearchBackend(api_key=secret),
        "brave",
    )


def build_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    domain = str(config.get("domain") or "ebike").strip()
    if not domain:
        raise CompositionError(
            "competitive-intelligence: config 'domain' must not be empty"
        )
    backend_name = str(config.get("search_backend") or "brave").strip()
    output_language = str(config.get("output_language") or "zh-CN").strip()
    max_search_results = _config_int(
        config, "max_search_results", DEFAULT_MAX_SEARCH_RESULTS
    )
    max_fetch_bytes = _config_int(
        config, "max_fetch_bytes", DEFAULT_MAX_FETCH_BYTES
    )
    max_preview_chars = _config_int(
        config, "max_preview_chars", DEFAULT_MAX_PREVIEW_CHARS
    )
    backend, _ = _build_backend(backend_name, config)

    # Harness Skills consumes library roots; each immediate child is a skill
    # package. Passing a package directory itself fails during agent build.
    skills_dir = Path(__file__).parent / "skills"
    skill_dirs = [skills_dir] if skills_dir.is_dir() else []

    return PluginBundle(
        toolsets=[
            make_source_toolset(
                backend,
                max_search_results=max_search_results,
                max_fetch_bytes=max_fetch_bytes,
                max_preview_chars=max_preview_chars,
                domain=domain,
                output_language=output_language,
            ),
            make_work_product_toolset(),
            make_report_toolset(),
        ],
        skill_dirs=skill_dirs,
    )


__all__ = ["build_plugin"]
