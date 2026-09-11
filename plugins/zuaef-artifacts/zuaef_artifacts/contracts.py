"""Plugin-local contracts: the common artifact result envelope.

One small serializable shape returned by every model-visible tool in this
plugin (spec pack 04 "Common result envelope"). Errors are recoverable and
format-local: a bad office file or a rejected path must never fail a whole
run, so tools return ``ok=false`` results instead of raising to the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

ArtifactType = Literal["docx", "pdf", "slides", "spreadsheet"]

QAState = Literal["not_run", "passed", "passed_with_warnings", "failed"]

# Short machine-readable failure classes (spec pack 06 "Error strategy").
ErrorCode = Literal[
    "invalid_request",
    "path_rejected",
    "unsupported_file",
    "missing_dependency",
    "conversion_failed",
    "unsupported_operation",
    "qa_failed",
    "internal_error",
]


class ArtifactResult(BaseModel):
    """Common envelope for every artifact tool result.

    ``artifact_path`` is workspace-relative (or None when nothing was
    produced). ``warnings`` stays bounded — engine code must truncate long
    diagnostics before placing them here.
    """

    ok: bool
    artifact_path: str | None = None
    artifact_type: ArtifactType | None = None
    qa_state: QAState = "not_run"
    error_code: ErrorCode | None = None
    warnings: list[str] = Field(default_factory=list)
    summary: str = ""


def failed_result(
    artifact_type: ArtifactType,
    error_code: ErrorCode,
    error: str,
    *,
    summary: str = "",
    artifact_path: str | None = None,
) -> ArtifactResult:
    """One bounded failure envelope; never leak full stack traces to the model."""
    text = f"{type(error).__name__}: {error}" if isinstance(error, BaseException) else str(error)
    return ArtifactResult(
        ok=False,
        artifact_path=artifact_path,
        artifact_type=artifact_type,
        qa_state="failed",
        error_code=error_code,
        warnings=[text[:500]],
        summary=summary or f"{artifact_type} operation failed",
    )


@dataclass(frozen=True)
class ArtifactBounds:
    """Conservative plugin-local resource limits (spec pack 06 "Resource
    bounds"). Non-secret plugin config; freezes into the composition identity.
    """

    max_input_bytes: int
    max_output_bytes: int
    process_timeout_seconds: int
    render_max_pages: int
