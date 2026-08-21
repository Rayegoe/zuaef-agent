"""ACE-backed production writing environment.

The plugin exposes a two-tool surface: ``pull_context`` and ``save_article``.
ACE and Harness retain operational provenance without asking the model to
re-encode it.

Editorial control (0.2.0 experiment) was removed from this production surface
in v1.2 T014B; the capability is benchmark/legacy only under
``benchmarks/editorial-learning/legacy/``.
"""

from __future__ import annotations

from .plugin import create_plugin
from .writing_toolset import WritingEnvironmentToolset, build_writing_toolset

__all__ = [
    "WritingEnvironmentToolset",
    "build_writing_toolset",
    "create_plugin",
]
