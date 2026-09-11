"""Engine-level error types mapped to bounded ArtifactResult error codes."""

from __future__ import annotations


class UnsupportedOperation(ValueError):
    """A requested edit/operation cannot be represented safely (spec pack 07:
    return an unsupported-operation error and let the model decide whether a
    controlled rebuild is acceptable)."""
