"""Workspace-safe path authority for artifact operations.

Every path accepted from the model flows through this module before any I/O
(spec pack 06 "Path authority"): workspace-relative only, no traversal or
symlink escape, no protected/secret files, final outputs only under the
designated per-format artifact root, no silent overwrite of a delivered
artifact. Unicode filenames are preserved where safe.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

# Per-format durable output roots below workspace/artifacts/ (spec pack 02
# "Proposed paths"). Temporary work/render trees are host state, NOT model
# paths — they are allocated by the engines under the state root.
FORMAT_DIRS: dict[str, str] = {
    "docx": "docx",
    "pdf": "pdf",
    "slides": "slides",
    "spreadsheet": "spreadsheets",
}

# Suffix sets enforced per artifact type (output must match; inputs are
# checked against the type the tool can actually process).
FORMAT_SUFFIXES: dict[str, set[str]] = {
    "docx": {".docx"},
    "pdf": {".pdf"},
    "slides": {".pptx"},
    "spreadsheet": {".xlsx"},
}

# Secret/credential material is never readable or writable through this
# plugin. Knowledge stays read-allowed but is never an output root (writes
# go through the Knowledge capability only).
_PROTECTED_SUFFIXES = {".pem", ".key"}
_PROTECTED_NAMES = {".env", ".env.local"}
_PROTECTED_OUTPUT_PREFIXES = ("knowledge", "inbox", ".git")

# Filename sanitation: keep letters (incl. CJK), digits, dot, dash,
# underscore and space; everything else collapses to "_".
_SAFE_NAME_RE = re.compile(r"[^\w.\- ]", re.UNICODE)
_MAX_STEM_CHARS = 80


class PathRejected(ValueError):
    """A model-supplied path failed containment/type/policy validation."""


def _clean_root(workspace_root: Path) -> Path:
    return workspace_root.resolve()


def _reject_protected(path: Path) -> None:
    if path.name in _PROTECTED_NAMES or path.suffix.lower() in _PROTECTED_SUFFIXES:
        raise PathRejected(f"protected file: {path.name}")
    if "secrets" in path.parts:
        raise PathRejected("protected path: secrets")


def resolve_input_path(
    workspace_root: Path, raw_path: str, *, max_bytes: int
) -> Path:
    """Authorize one workspace-relative INPUT path for reading.

    resolve() follows symlinks, so a link planted inside the workspace that
    points outside resolves outside and is rejected here.
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise PathRejected("path must be a non-empty workspace-relative string")
    raw = raw_path.strip()
    root = _clean_root(workspace_root)
    candidate = Path(raw)
    if candidate.is_absolute():
        raise PathRejected(f"absolute paths are not accepted: {raw}")
    resolved = (root / candidate).resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise PathRejected(f"path is outside the workspace: {raw}")
    _reject_protected(resolved)
    if not resolved.is_file():
        raise PathRejected(f"file does not exist: {raw}")
    size = resolved.stat().st_size
    if size > max_bytes:
        raise PathRejected(
            f"file exceeds the configured byte limit ({size} > {max_bytes}): {raw}"
        )
    return resolved


def resolve_existing_artifact(
    workspace_root: Path,
    raw_path: str,
    artifact_type: str,
    *,
    max_bytes: int,
) -> Path:
    """Authorize an input that must be an artifact of the expected type."""
    resolved = resolve_input_path(workspace_root, raw_path, max_bytes=max_bytes)
    suffixes = FORMAT_SUFFIXES[artifact_type]
    if resolved.suffix.lower() not in suffixes:
        raise PathRejected(
            f"expected a {artifact_type} artifact ({', '.join(sorted(suffixes))}), "
            f"got {resolved.suffix or 'no extension'}"
        )
    return resolved


def sanitize_filename(raw_name: str) -> str:
    """Sanitize a model-supplied filename: no directories, no control or
    reserved characters, bounded length. Unicode (CJK) is preserved."""
    if not isinstance(raw_name, str):
        raise PathRejected("filename must be a string")
    name = Path(raw_name.strip()).name  # drops any directory component
    name = name.replace("\x00", "")
    cleaned = _SAFE_NAME_RE.sub("_", name).strip(" .")
    if not cleaned:
        raise PathRejected("filename is empty after sanitation")
    stem, dot, suffix = cleaned.rpartition(".")
    if not dot:
        stem, suffix = cleaned, ""
    if len(stem) > _MAX_STEM_CHARS:
        stem = stem[:_MAX_STEM_CHARS]
    return f"{stem}.{suffix}" if suffix else stem


def enforce_suffix(name: str, artifact_type: str) -> str:
    """Force the canonical extension for the artifact type."""
    suffix = next(iter(FORMAT_SUFFIXES[artifact_type]))
    if not name.lower().endswith(suffix):
        name = f"{name}{suffix}"
    return name


def allocate_output_path(
    workspace_root: Path,
    artifact_type: str,
    requested_name: str | None,
    *,
    default_stem: str,
) -> Path:
    """Allocate a NON-existing final output path under the format's artifact
    root. Existing files are never overwritten: a numeric -2, -3, … suffix
    is appended until a free name is found."""
    root = _clean_root(workspace_root)
    out_dir = root / "artifacts" / FORMAT_DIRS[artifact_type]
    name = sanitize_filename(requested_name) if requested_name else default_stem
    name = enforce_suffix(name, artifact_type)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate = out_dir / name
    if candidate.exists():
        stem = candidate.stem
        suffix = candidate.suffix
        for counter in range(2, 1000):
            candidate = out_dir / f"{stem}-{counter}{suffix}"
            if not candidate.exists():
                break
        else:
            raise PathRejected("could not allocate a free output filename")
    return candidate


def allocate_revision_path(
    workspace_root: Path,
    artifact_type: str,
    source: Path,
    requested_name: str | None,
) -> Path:
    """Output path for a revision. A versioned name derived from the source
    (``<stem>-rev2``, ``-rev3``, …) unless the caller explicitly names the
    output; the file always lands under the format's designated artifact
    root, and an existing file is never overwritten."""
    if requested_name:
        return allocate_output_path(
            workspace_root, artifact_type, requested_name, default_stem=source.stem
        )
    root = _clean_root(workspace_root)
    out_dir = root / "artifacts" / FORMAT_DIRS[artifact_type]
    out_dir.mkdir(parents=True, exist_ok=True)
    stem, suffix = source.stem, source.suffix
    counter = 2
    candidate = out_dir / f"{stem}-rev{counter}{suffix}"
    while candidate.exists():
        counter += 1
        candidate = out_dir / f"{stem}-rev{counter}{suffix}"
        if counter > 1000:  # pragma: no cover - absurd revision counts
            raise PathRejected("could not allocate a revision filename")
    return candidate


def artifact_display_path(workspace_root: Path, target: Path) -> str:
    """Workspace-relative display path (the only path form returned to the
    model)."""
    try:
        return str(target.resolve().relative_to(_clean_root(workspace_root)))
    except ValueError:  # pragma: no cover - allocation guarantees containment
        return str(target)


def allocate_work_dir(work_root: Path, call_scope: str) -> Path:
    """Internal conversion/work tree for one tool call (host state, never a
    model-visible path).

    ``work_root`` is the deployment's work base (state root by default). On
    hosts where LibreOffice ships as a snap it CANNOT access hidden
    directories (dot-prefixed) nor the host /tmp — operators then point
    ``work_dir`` config / ``ZUAEF_ARTIFACTS_WORK_DIR`` at a plain $HOME
    directory.
    """
    safe_scope = re.sub(r"[^A-Za-z0-9_-]", "_", call_scope)[:60] or "call"
    work = work_root / "artifact-work" / f"{safe_scope}-{_unique_tag()}"
    work.mkdir(parents=True, exist_ok=True)
    return work


def allocate_render_dir(work_root: Path, call_scope: str) -> Path:
    """Internal render tree for one tool call's QA images (same placement
    rules as allocate_work_dir)."""
    safe_scope = re.sub(r"[^A-Za-z0-9_-]", "_", call_scope)[:60] or "call"
    render = work_root / "artifact-renders" / f"{safe_scope}-{_unique_tag()}"
    render.mkdir(parents=True, exist_ok=True)
    return render


def cleanup_dir(directory: Path) -> None:
    """Best-effort removal of one internal work/render tree."""
    shutil.rmtree(directory, ignore_errors=True)


def _unique_tag() -> str:
    import secrets

    return secrets.token_hex(5)
