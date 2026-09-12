"""Repository / deployment path helpers shared by Quant production modules.

This module is intentionally stdlib-only: thin operator surfaces (dashboard
render/serve) and side-environment entry points may import it without pulling
the plugin capability (pydantic_ai) or heavy quant dependencies.  Production
modules must not depend on the repository's developer tool directory; the
repository root is used only to locate the workspace/data/benchmark layout
around the installed package (or explicitly via ``ZUAEF_QUANT_REPO_ROOT``).
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT_ENV = "ZUAEF_QUANT_REPO_ROOT"
QUANT_PYTHON_ENV = "ZUAEF_QUANT_PYTHON"
QUANT_PYTHON_DEFAULT = ".venv-quant/bin/python"

#: A repo checkout is identified by the frozen benchmark contract and the
#: package source tree — never by a root developer/production tool script.
REPO_ROOT_MARKERS = (
    "benchmarks/quant/gen1/quant.toml",
    "plugins/zuaef-quant/zuaef_quant/__init__.py",
)


def package_parent() -> Path:
    """Directory that must be on ``PYTHONPATH`` to import ``zuaef_quant``."""
    return Path(__file__).resolve().parents[1]


def _has_repo_markers(candidate: Path) -> bool:
    return all((candidate / marker).exists() for marker in REPO_ROOT_MARKERS)


def resolve_repo_root() -> Path:
    """Locate the deployment/repository root that carries workspace/data.

    Resolution order: ``ZUAEF_QUANT_REPO_ROOT`` wins (explicit deployment
    binding), then the package position derives the repo root for editable
    layouts, then the current directory is accepted only when it carries the
    benchmark/package markers.  Unlike the pre-P5.9 resolver this never needs
    a root production script to exist.
    """
    configured = os.getenv(REPO_ROOT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    package = Path(__file__).resolve()
    candidate = package.parents[3]  # <repo>/plugins/zuaef-quant/zuaef_quant/runtime.py
    if _has_repo_markers(candidate):
        return candidate
    cwd = Path.cwd().resolve()
    if _has_repo_markers(cwd):
        return cwd
    # Installed-package deployments bind their workspace/data layout explicitly
    # through the environment (or run from it).  Returning cwd keeps the
    # renderer/CLI honest on missing artifacts instead of failing on repo
    # script topology.
    return cwd


def resolve_quant_python() -> Path:
    """Locate the isolated quant side environment (pandas/akshare/qlib).

    ``ZUAEF_QUANT_PYTHON`` is the explicit deployment binding; otherwise the
    conventional repo-relative ``.venv-quant/bin/python`` is used.  Callers
    raise their own domain-specific error when the path is unavailable.
    """
    configured = os.getenv(QUANT_PYTHON_ENV)
    if configured:
        # expanduser only — never resolve(): a symlinked venv interpreter
        # (e.g. uv's .venv-quant/bin/python -> base cpython) loses its
        # pyvenv.cfg context when resolved, and the bare base interpreter
        # cannot import the venv's site-packages (pandas/akshare).
        return Path(configured).expanduser()
    return resolve_repo_root() / QUANT_PYTHON_DEFAULT
