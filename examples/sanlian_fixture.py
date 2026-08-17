"""Sanlian-specific entry into the host fixture adapter.

The generic adapter lives in ``examples/host_fixture.py`` (``MaterialFile`` /
``load_material_file`` / ``load_material_case``). This module only adds the
Sanlian wiki convention: the default ``source_ref`` is the wiki-relative path
``wiki-sanlian-life-weekly-2026-30/sources/<filename>``. Everything else —
resolve path, exact bytes, sha256, rights validation, ACE ingest -> real M id
— is the adapter's, unchanged. The adapter still decides nothing about
techniques/structure and never calls an LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from examples.host_fixture import (
    DEFAULT_ACE_ROOT,
    RIGHTS_STATUSES,
    RightsError,
    load_material_file,
)
from examples.host_fixture import (
    MaterialFile as SanlianFixture,
)

__all__ = [
    "RIGHTS_STATUSES",
    "RightsError",
    "SanlianFixture",
    "load_sanlian_fixture",
]


def load_sanlian_fixture(
    path: str | Path,
    *,
    rights: str = "study-only",
    source_ref: str | None = None,
    article_id: str | None = None,
    title: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
    ingest: bool = True,
    **kwargs: Any,
) -> SanlianFixture:
    """Load a Sanlian wiki page as a data entry (see host_fixture module doc).

    ``source_ref`` defaults to
    ``wiki-sanlian-life-weekly-2026-30/sources/<filename>``.
    """
    if source_ref is None:
        resolved = Path(path).expanduser().resolve()
        source_ref = f"wiki-sanlian-life-weekly-2026-30/sources/{resolved.name}"
    return load_material_file(
        path,
        rights=rights,
        source_ref=source_ref,
        article_id=article_id,
        title=title,
        ace_root=ace_root,
        ingest=ingest,
        **kwargs,
    )
