"""Host fixture adapter — a reliable DATA ENTRY, nothing else.

The production host needs one guarantee: the exact bytes that get hashed are
the exact bytes that get projected as the article material. This adapter
provides that guarantee and deliberately does NOT do anything else:

- it does NOT decide techniques;
- it does NOT decide article structure;
- it does NOT call an LLM;
- it does NOT touch benchmark assets (``task_inputs.py`` stays benchmark-only).

``load_material_file`` performs five deterministic steps per file:

  1. resolve the real path (expanduser + resolve, must be a file);
  2. read the exact bytes;
  3. sha256 of those exact bytes;
  4. rights metadata (caller-declared, validated against the enum);
  5. ACE ingest -> the real material id (M00x) from the ACE workspace index
     (only when the host supplies an ``article_id``; ACE dedupes by sha256,
     so re-loading the same fixture is idempotent).

``load_material_case`` does the same for a case directory of raw files
(``raw/`` by default) in one ACE ingest call, returning a ``MaterialCase``
whose ledger rows (S1..Sn) each carry the per-file sha256 / rights /
material id — a multi-source bundle stays byte-exact per source.

The host then turns the material into a ``WritingContext`` bundle
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
class MaterialFile:
    """One material file as a data record: exact text plus identity metadata.

    ``text`` is the EXACT decoded file bytes — the sha256 binds to it, and
    whatever the host projects as material must be this text so the hash
    stays a proof of what the model saw.
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
        """The ledger line for a run receipt (identity, never the text)."""
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


@dataclass(frozen=True)
class MaterialCase:
    """A case = an ordered set of raw material files with one rights status."""

    case_name: str
    files: list[MaterialFile]
    rights: str

    def to_record(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "rights": self.rights,
            "files": [f.to_record() for f in self.files],
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


def load_material_file(
    path: str | Path,
    *,
    rights: str = "study-only",
    source_ref: str | None = None,
    article_id: str | None = None,
    title: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
    ingest: bool = True,
) -> MaterialFile:
    """Load one raw file as a data entry (see module docstring).

    ``rights`` must be one of ``RIGHTS_STATUSES``; the caller declares it
    (this adapter never guesses). ``source_ref`` defaults to the resolved
    path as a string. ACE ingest (step 5) runs only when ``article_id`` is
    given AND ``ingest`` is true — unit tests can load the pure data entry
    without ACE.
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
        source_ref = str(resolved)
    material_id: str | None = None
    if article_id and ingest:
        ace_prepare(
            article_id,
            title=title,
            materials=[str(resolved)],
            ace_root=ace_root,
        )
        material_id = _read_material_id(ace_root, article_id, sha256)
    return MaterialFile(
        text=text,
        source_ref=source_ref,
        sha256=sha256,
        rights=rights,
        material_id=material_id,
        source_path=resolved,
        source_byte_length=len(data),
        projected_char_length=len(text),
    )


def load_material_case(
    case_dir: str | Path,
    *,
    rights: str = "study-only",
    raw_dir: str = "raw",
    source_ref_prefix: str | None = None,
    article_id: str | None = None,
    title: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
    ingest: bool = True,
) -> MaterialCase:
    """Load every file under ``<case_dir>/<raw_dir>/`` as one material case.

    Files are ordered by name (deterministic), each hashed individually.
    When ``article_id`` is given, ALL files are ingested in one ACE call and
    the real M id is read back per file from the workspace index.
    ``source_ref_prefix`` defaults to ``cases/<case-dir-name>`` so refs look
    like ``cases/01-content-team/raw/interview.txt``.
    """
    if rights not in RIGHTS_STATUSES:
        raise RightsError(f"rights must be one of {RIGHTS_STATUSES}, got {rights!r}")
    resolved = Path(case_dir).expanduser().resolve()
    raw = resolved / raw_dir
    if not raw.is_dir():
        raise FileNotFoundError(f"case raw dir not found: {raw}")
    paths = sorted(p for p in raw.iterdir() if p.is_file())
    if not paths:
        raise FileNotFoundError(f"case raw dir has no files: {raw}")
    if source_ref_prefix is None:
        source_ref_prefix = f"cases/{resolved.name}"

    if article_id and ingest:
        ace_prepare(
            article_id,
            title=title,
            materials=[str(p) for p in paths],
            ace_root=ace_root,
        )
    files: list[MaterialFile] = []
    for path in paths:
        data = path.read_bytes()
        text = data.decode("utf-8")
        sha256 = _sha256_of_bytes(data)
        material_id = (
            _read_material_id(ace_root, article_id, sha256)
            if article_id and ingest
            else None
        )
        files.append(
            MaterialFile(
                text=text,
                source_ref=f"{source_ref_prefix}/{raw_dir}/{path.name}",
                sha256=sha256,
                rights=rights,
                material_id=material_id,
                source_path=path,
                source_byte_length=len(data),
                projected_char_length=len(text),
            )
        )
    return MaterialCase(case_name=resolved.name, files=files, rights=rights)


def render_case_material(case: MaterialCase) -> str:
    """The exact material text projected into the WritingContext.

    Deterministic concatenation with per-file separators carrying each
    file's source_ref + sha256, so the projected text stays byte-verifiable
    against every ledger row.
    """
    blocks: list[str] = []
    for f in case.files:
        blocks.append(
            f"<file {f.source_ref}> (sha256: {f.sha256})\n"
            f"{f.text}\n"
            f"</file {f.source_ref}>"
        )
    return "\n\n".join(blocks)


def build_case_sources(case: MaterialCase) -> list[dict]:
    """Caller-owned source ledger rows S1..Sn for a multi-file case."""
    sources: list[dict] = []
    for i, f in enumerate(case.files, 1):
        sources.append(
            {
                "id": f"S{i}",
                "kind": "material",
                "label": Path(f.source_ref).name,
                "material_ids": [f.material_id or f"M{i:03d}"],
                "source_ref": f.source_ref,
                "sha256": f.sha256,
                "rights": f.rights,
            }
        )
    return sources
