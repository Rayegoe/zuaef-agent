"""ZUAEF Agent Console — local operator surface over existing runtime facts.

This package is an external interaction layer (Surface/Gateway boundary,
AGENTS.md): it owns transport and view projection only. It never executes an
agent loop, never persists a derived trace, and never implements approval
semantics — supervision routes through ``continuation.resume_paused_run``.

Rollback (SPEC §16): deleting this package, ``web-ui/`` and the CLI ``web``
branch restores prior runtime semantics.
"""

from .server import create_app, serve

__all__ = ["create_app", "serve"]
