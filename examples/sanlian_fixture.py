"""Sanlian Host Fixture adapter — a reliable DATA ENTRY, nothing else.

The production host (``sanlian_showcase.py``) needs one guarantee: the exact
bytes that get hashed are the exact bytes that get projected as the article
material. This adapter provides that guarantee and deliberately does NOT do
anything else:

- it does NOT decide techniques;
- it does NOT decide article structure;
- it does NOT call an LLM;
- it does NOT touch benchmark assets (``task_inputs.py`` stays benchmark-only).

``load_sanlian_fixture`` performs five deterministic steps:

  1. resolve the real path (expanduser + resolve, must be a file);
  2. read the exact bytes;
  3. sha256 of those exact bytes;
  4. rights metadata (caller-declared, validated against the enum);
  5. ACE ingest -> the real material id (M00x) from the ACE workspace index
     (only when the host supplies an ``article_id``; ACE dedupes by sha256,
     so re-loading the same fixture is idempotent).

The host then turns the fixture into a ``WritingContext`` bundle
(``prepare_writing_context``) with its own task / writing_plan / techniques /
editorial_memory / examples — none of which this adapter knows about.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import DEFAULT_ACE_ROOT, ace_prepare

RIGHTS_STATUSES = ("study-only", "licensed", "user-provided", "unknown")


class RightsError(ValueError):
    """Declared rights status is not one of the accepted enum values."""


@dataclass(frozen=True)
class SanlianFixture:
    """The fixture as a data record: exact text plus identity metadata.

    ``text`` is the EXACT decoded file bytes (front matter included) — the
    sha256 binds to it, and whatever the host projects as material must be
    this text so the hash stays a proof of what the model saw.
    """

    text: str
    source_ref: str
    sha256: str
    rights: str
    material_id: str | None = None
    source_path: Path | None = None
    source_byte_length: int = 0
    projected_char_length: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        """The fixture line for a run receipt (bytes/hash/rights, no text)."""
        return {
            "source_ref": self.source_ref,
            "source_path": str(self.source_path) if self.source_path else None,
            "source_byte_length": self.source_byte_length,
            "source_sha256": self.sha256,
            "projected_char_length": self.projected_char_length,
            "rights": self.rights,
            "material_id": self.material_id,
            **self.extra,
        }


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _material_index_path(ace_root: Path, article_id: str) -> Path:
    """Mirror ACE's index resolution: new flat layout, then legacy."""
    base = ace_root / "workspaces" / article_id
    for rel in ("materials.jsonl", "00_intake/material-index.jsonl"):
        candidate = base / rel
        if candidate.exists():
            return candidate
    return base / "materials.jsonl"


def _read_material_id(ace_root: Path, article_id: str, sha256: str) -> str | None:
    """The ACE row for our exact bytes -> the REAL M id (never a placeholder)."""
    index = _material_index_path(ace_root, article_id)
    if not index.is_file():
        return None
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("sha256") == sha256:
            return str(row.get("id"))
    return None


def load_sanlian_fixture(
    path: str | Path,
    *,
    rights: str = "study-only",
    source_ref: str | None = None,
    article_id: str | None = None,
    title: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
    ingest: bool = True,
) -> SanlianFixture:
    """Load a Sanlian wiki page as a data entry (see module docstring).

    ``rights`` must be one of ``RIGHTS_STATUSES``; the caller declares it
    (this adapter never guesses). ``source_ref`` defaults to the wiki-relative
    path ``wiki-sanlian-life-weekly-2026-30/sources/<filename>``.

    ACE ingest (step 5) runs only when ``article_id`` is given AND
    ``ingest`` is true — the host passes the run workspace id; unit tests can
    load the pure data entry without ACE.
    """
    if rights not in RIGHTS_STATUSES:
        raise RightsError(f"rights must be one of {RIGHTS_STATUSES}, got {rights!r}")
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"fixture not a file: {resolved}")
    data = resolved.read_bytes()
    text = data.decode("utf-8")
    sha256 = _sha256_of_bytes(data)
    if source_ref is None:
        source_ref = f"wiki-sanlian-life-weekly-2026-30/sources/{resolved.name}"
    material_id: str | None = None
    if article_id and ingest:
        ace_prepare(
            article_id,
            title=title,
            materials=[str(resolved)],
            ace_root=ace_root,
        )
        material_id = _read_material_id(ace_root, article_id, sha256)
    return SanlianFixture(
        text=text,
        source_ref=source_ref,
        sha256=sha256,
        rights=rights,
        material_id=material_id,
        source_path=resolved,
        source_byte_length=len(data),
        projected_char_length=len(text),
    )
