"""``zuaef-artifacts`` plugin factory.

Bundles the four deferred artifact capabilities into one ``PluginBundle``.
Config is non-secret composition identity (it freezes into the
CompositionSnapshot); unknown keys fail composition instead of being silently
ignored. The factory owns no policy beyond its own bounds: routing, format
selection, and content decisions stay with the agent; transport stays with
the Gateway.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .capabilities import (
    build_docx_capability as make_docx_capability,
)
from .capabilities import (
    build_pdf_capability as make_pdf_capability,
)
from .capabilities import (
    build_slides_capability as make_slides_capability,
)
from .capabilities import (
    build_spreadsheet_capability as make_spreadsheet_capability,
)
from .contracts import ArtifactBounds

_ALLOWED_CONFIG_KEYS = {
    "max_input_bytes",
    "max_output_bytes",
    "process_timeout_seconds",
    "render_max_pages",
    "work_dir",
}

DEFAULT_MAX_INPUT_BYTES = 25_000_000
DEFAULT_MAX_OUTPUT_BYTES = 25_000_000
DEFAULT_PROCESS_TIMEOUT_SECONDS = 120
DEFAULT_RENDER_MAX_PAGES = 8

_PROCESS_TIMEOUT_MIN = 5
_PROCESS_TIMEOUT_MAX = 600
_BYTES_MIN = 1
_BYTES_MAX = 200_000_000


def _int_value(config: dict[str, Any], key: str, default: int) -> int:
    raw = config.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise CompositionError(f"artifacts config {key!r} must be an integer") from exc
    return value


def _validated_bounds(config: dict[str, Any]) -> ArtifactBounds:
    """Strict non-secret config validation (fail composition before any run)."""
    bounds = ArtifactBounds(
        max_input_bytes=_int_value(config, "max_input_bytes", DEFAULT_MAX_INPUT_BYTES),
        max_output_bytes=_int_value(
            config, "max_output_bytes", DEFAULT_MAX_OUTPUT_BYTES
        ),
        process_timeout_seconds=_int_value(
            config, "process_timeout_seconds", DEFAULT_PROCESS_TIMEOUT_SECONDS
        ),
        render_max_pages=_int_value(
            config, "render_max_pages", DEFAULT_RENDER_MAX_PAGES
        ),
    )
    for name in ("max_input_bytes", "max_output_bytes"):
        value = getattr(bounds, name)
        if not _BYTES_MIN <= value <= _BYTES_MAX:
            raise CompositionError(
                f"artifacts config {name!r} must be in [{_BYTES_MIN}, {_BYTES_MAX}]"
            )
    if (
        not _PROCESS_TIMEOUT_MIN
        <= bounds.process_timeout_seconds
        <= _PROCESS_TIMEOUT_MAX
    ):
        raise CompositionError(
            "artifacts config 'process_timeout_seconds' must be in "
            f"[{_PROCESS_TIMEOUT_MIN}, {_PROCESS_TIMEOUT_MAX}]"
        )
    if not 1 <= bounds.render_max_pages <= 50:
        raise CompositionError("artifacts config 'render_max_pages' must be in [1, 50]")
    return bounds


def _resolve_work_dir(config: dict[str, Any]) -> Path | None:
    """Optional operator override for the internal work/render base.

    Needed on hosts where LibreOffice ships as a snap: it cannot read or
    write hidden directories (dot-prefixed) nor the host /tmp, so the
    default (state root) placement fails for conversion QA. Profile config
    wins; ``ZUAEF_ARTIFACTS_WORK_DIR`` is the host-level fallback. The path
    is operator-provided host configuration — never model input.
    """
    raw = str(config.get("work_dir", "")).strip() or os.getenv(
        "ZUAEF_ARTIFACTS_WORK_DIR", ""
    ).strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise CompositionError("artifacts config 'work_dir' must be an absolute path")
    return path


def build_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    unknown = sorted(set(config) - _ALLOWED_CONFIG_KEYS)
    if unknown:
        raise CompositionError(
            f"artifacts config has unknown key(s) {unknown}; allowed: "
            f"{sorted(_ALLOWED_CONFIG_KEYS)}"
        )
    bounds = _validated_bounds(config)
    work_root = _resolve_work_dir(config) or env.state_root
    capability_args = {
        "bounds": bounds,
        "workspace_root": env.workspace_root,
        "work_root": work_root,
    }
    return PluginBundle(
        capabilities=[
            make_docx_capability(**capability_args),
            make_pdf_capability(**capability_args),
            make_slides_capability(**capability_args),
            make_spreadsheet_capability(**capability_args),
        ]
    )
