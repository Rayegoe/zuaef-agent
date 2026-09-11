"""Bounded fixed-executable process wrapper and dependency probing.

Office conversion and page rendering need installed system executables
(LibreOffice, poppler). This module owns the ONLY process invocation path in
the plugin (spec pack 06 "External process wrapper"): the executable is
chosen from a fixed internal allowlist by name, arguments are argv lists
(never shell text), ``shell=False`` always, timeouts are bounded, output is
captured and truncated, and a missing dependency is a clean recoverable
error — never a crash and never a fallback to a broader execution surface.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Fixed allowlist: name → candidate executable names tried in order via
# PATH. No model- or config-supplied executable path is ever used.
_OFFICE_CANDIDATES = ("soffice", "libreoffice")
_PDF_RENDER_CANDIDATES = ("pdftoppm",)

# Bound on captured child output placed in warnings/diagnostics.
_MAX_OUTPUT_CHARS = 2000


class MissingDependency(RuntimeError):
    """A required optional system dependency is not installed."""


class ProcessFailed(RuntimeError):
    """A bounded external process failed or timed out."""


@dataclass(frozen=True)
class BoundedResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def resolve_executable(candidates: tuple[str, ...]) -> str | None:
    """Resolve the first allowlisted candidate present on PATH, else None."""
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    return None


def run_bounded(
    executable: str,
    argv_tail: list[str],
    *,
    timeout_seconds: int,
    cwd: Path,
    env_additions: dict[str, str] | None = None,
) -> BoundedResult:
    """Run one fixed executable with argv-list arguments under a timeout.

    ``executable`` must come from this module's resolvers (allowlist
    selection happens at the call sites); argv is a list; shell=False.
    """
    env = os.environ.copy()
    if env_additions:
        env.update(env_additions)
    try:
        completed = subprocess.run(
            [executable, *argv_tail],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return BoundedResult(
            returncode=-1,
            stdout=(exc.stdout or b"").decode("utf-8", "replace")[:_MAX_OUTPUT_CHARS]
            if isinstance(exc.stdout, bytes)
            else str(exc.stdout or "")[:_MAX_OUTPUT_CHARS],
            stderr=(exc.stderr or b"").decode("utf-8", "replace")[:_MAX_OUTPUT_CHARS]
            if isinstance(exc.stderr, bytes)
            else str(exc.stderr or "")[:_MAX_OUTPUT_CHARS],
            timed_out=True,
        )
    except FileNotFoundError as exc:
        raise MissingDependency(f"executable not found: {executable}") from exc
    return BoundedResult(
        returncode=completed.returncode,
        stdout=completed.stdout[:_MAX_OUTPUT_CHARS],
        stderr=completed.stderr[:_MAX_OUTPUT_CHARS],
    )


def office_convert(
    source: Path,
    target_suffix: str,
    out_dir: Path,
    *,
    timeout_seconds: int,
    profile_dir: Path | None = None,
) -> Path:
    """Convert one office document via headless LibreOffice into ``out_dir``.

    An isolated UserInstallation profile keeps the conversion independent of
    any interactive LibreOffice instance. Returns the produced file path.
    """
    executable = resolve_executable(_OFFICE_CANDIDATES)
    if executable is None:
        raise MissingDependency(
            "LibreOffice (soffice/libreoffice) is not installed — "
            f"cannot convert to {target_suffix}"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = ["--headless", "--norestore"]
    if profile_dir is not None:
        profile_dir.mkdir(parents=True, exist_ok=True)
        argv.append(f"-env:UserInstallation=file://{profile_dir}")
    argv += [
        "--convert-to",
        target_suffix,
        "--outdir",
        str(out_dir),
        str(source),
    ]
    result = run_bounded(
        executable, argv, timeout_seconds=timeout_seconds, cwd=out_dir
    )
    produced = out_dir / f"{source.stem}.{target_suffix}"
    if result.timed_out:
        raise ProcessFailed(
            f"conversion timed out after {timeout_seconds}s: {source.name}"
        )
    if result.returncode != 0 or not produced.is_file():
        detail = (result.stderr or result.stdout or "no output").strip()
        raise ProcessFailed(
            f"conversion failed for {source.name} "
            f"(rc={result.returncode}): {detail[:_MAX_OUTPUT_CHARS]}"
        )
    return produced


def render_pdf_pages(
    pdf_path: Path,
    out_dir: Path,
    *,
    max_pages: int,
    timeout_seconds: int,
    dpi: int = 100,
) -> list[Path]:
    """Render the first ``max_pages`` pages of a PDF to PNG images via
    poppler's pdftoppm. Returns the produced image paths in page order."""
    executable = resolve_executable(_PDF_RENDER_CANDIDATES)
    if executable is None:
        raise MissingDependency(
            "pdftoppm (poppler-utils) is not installed — cannot render PDF pages"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    result = run_bounded(
        executable,
        [
            "-png",
            "-r",
            str(dpi),
            "-f",
            "1",
            "-l",
            str(max_pages),
            str(pdf_path),
            str(prefix),
        ],
        timeout_seconds=timeout_seconds,
        cwd=out_dir,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no output").strip()
        raise ProcessFailed(f"PDF rendering failed (rc={result.returncode}): {detail}")
    images = sorted(out_dir.glob("page-*.png"))
    if not images:
        raise ProcessFailed("PDF rendering produced no pages")
    return images


def probe_dependencies() -> dict[str, object]:
    """Factual availability probe for tests/diagnostics (never model-visible).

    Reports architecture, Python version, importability of the Python format
    engines, and presence/version of the optional system tools.
    """
    import importlib
    import platform
    import sys

    def _import(name: str) -> str:
        try:
            module = importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - probe reports, never raises
            return f"ERROR: {type(exc).__name__}: {exc}"
        return getattr(module, "__version__", None) or "installed"

    def _exe(candidates: tuple[str, ...], version_flag: str = "--version") -> str:
        found = resolve_executable(candidates)
        if found is None:
            return "absent"
        version = run_bounded(
            found, [version_flag], timeout_seconds=30, cwd=Path.home()
        )
        return f"{found} ({(version.stdout or version.stderr).strip().splitlines()[-1] if (version.stdout or version.stderr).strip() else 'unknown version'})"

    return {
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "docx": _import("docx"),
        "pypdf": _import("pypdf"),
        "openpyxl": _import("openpyxl"),
        "pptx": _import("pptx"),
        "libreoffice": _exe(_OFFICE_CANDIDATES),
        "pdftoppm": _exe(_PDF_RENDER_CANDIDATES, version_flag="-v"),
    }
