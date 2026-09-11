"""PDF artifact capability: create / convert / merge / edit / inspect
fixed-layout deliverables under ``workspace/artifacts/pdf/``."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.capabilities import Capability

from zuaef_agent.models import CoreDeps

from ..contracts import ArtifactBounds, ArtifactResult, failed_result
from ..engines import docx_engine, pdf_engine
from ..engines.docx_engine import DocumentSpec
from ..engines.errors import UnsupportedOperation
from ..guidance import load_guidance
from ..paths import (
    PathRejected,
    allocate_output_path,
    allocate_render_dir,
    allocate_work_dir,
    artifact_display_path,
    cleanup_dir,
    resolve_existing_artifact,
    resolve_input_path,
)
from ..process import MissingDependency, ProcessFailed
from ..qa import qa_pdf

DESCRIPTION = (
    "Polished fixed-layout PDF deliverables 客户最终版/正式版/发客户/归档/打印: "
    "produce a final shareable PDF, freeze DOCX/PPTX/XLSX into PDF, and do "
    "PDF page work (merge 合并, select/split pages 拆分, rotate 旋转, inspect). "
    "Use when the outcome is a final shareable version rather than an "
    "editable draft, or when the user asks for PDF."
)

_ERROR_CODES: tuple[tuple[type[Exception], str], ...] = (
    (PathRejected, "path_rejected"),
    (UnsupportedOperation, "unsupported_operation"),
    (MissingDependency, "missing_dependency"),
    (ProcessFailed, "conversion_failed"),
)


def _error_code_for(exc: Exception) -> str:
    for exc_type, code in _ERROR_CODES:
        if isinstance(exc, exc_type):
            return code
    return "invalid_request" if isinstance(exc, ValueError) else "internal_error"


def _default_stem() -> str:
    return f"document-{time.strftime('%Y%m%d-%H%M%S')}"


def build_capability(
    *,
    bounds: ArtifactBounds,
    workspace_root: Path,
    work_root: Path,
) -> Capability[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset[CoreDeps]()

    @toolset.tool_plain
    def create_pdf(spec: DocumentSpec, output_name: str | None = None) -> ArtifactResult:
        """Create a polished fixed-layout .pdf from a declarative content
        spec (same blocks as create_docx: heading/paragraph/lists/quote/
        table/image/page_break). Best for final shareable versions. Runs
        reopen/render QA inside this call and returns the artifact path."""
        out_path: Path | None = None
        work: Path | None = None
        render: Path | None = None
        try:
            docx_engine.validate_document_spec(spec)
            out_path = allocate_output_path(
                workspace_root, "pdf", output_name, default_stem=_default_stem()
            )
            work = allocate_work_dir(work_root, "pdf-create")
            pdf_engine.create_pdf_from_spec(
                spec,
                out_path,
                workspace_root=workspace_root,
                work_dir=work,
                timeout_seconds=bounds.process_timeout_seconds,
            )
            render = allocate_render_dir(work_root, "pdf-create")
            outcome = qa_pdf(
                out_path, render_dir=render, bounds=bounds
            )
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="pdf",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="PDF was created but failed QA; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="pdf",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=(
                    f"created PDF '{spec.title}' with {len(spec.blocks)} content block(s)"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("pdf", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if work is not None:
                cleanup_dir(work)
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def convert_to_pdf(path: str, output_name: str | None = None) -> ArtifactResult:
        """Convert an existing DOCX/PPTX/XLSX (workspace-relative) into a
        fixed-layout PDF under artifacts/pdf/. The source file is unchanged."""
        out_path: Path | None = None
        work = render = None
        try:
            source = resolve_input_path(
                workspace_root, path, max_bytes=bounds.max_input_bytes
            )
            if source.suffix.lower() not in pdf_engine.CONVERTIBLE_SUFFIXES:
                return failed_result(
                    "pdf",
                    "unsupported_file",
                    f"cannot convert {source.suffix or 'this file type'}; "
                    "supported: .docx, .pptx, .xlsx",
                )
            out_path = allocate_output_path(
                workspace_root,
                "pdf",
                output_name,
                default_stem=f"{source.stem}-{time.strftime('%Y%m%d-%H%M%S')}",
            )
            work = allocate_work_dir(work_root, "pdf-convert")
            pdf_engine.convert_office_to_pdf(
                source,
                out_path,
                work_dir=work,
                timeout_seconds=bounds.process_timeout_seconds,
            )
            render = allocate_render_dir(work_root, "pdf-convert")
            outcome = qa_pdf(out_path, render_dir=render, bounds=bounds)
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="pdf",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="conversion produced a PDF but QA failed; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="pdf",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=f"converted {source.name} to PDF",
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("pdf", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if work is not None:
                cleanup_dir(work)
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def merge_pdf(paths: list[str], output_name: str | None = None) -> ArtifactResult:
        """Merge two or more PDFs (workspace-relative, given in order) into
        one PDF under artifacts/pdf/."""
        out_path: Path | None = None
        render = None
        try:
            sources = [
                resolve_existing_artifact(
                    workspace_root, raw, "pdf", max_bytes=bounds.max_input_bytes
                )
                for raw in paths
            ]
            out_path = allocate_output_path(
                workspace_root, "pdf", output_name, default_stem=_default_stem()
            )
            expected = pdf_engine.merge_pdfs(
                sources, out_path, max_inputs=pdf_engine.MAX_MERGE_INPUTS
            )
            render = allocate_render_dir(work_root, "pdf-merge")
            outcome = qa_pdf(
                out_path, expected_pages=expected, render_dir=render, bounds=bounds
            )
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="pdf",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="merged PDF failed QA; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="pdf",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=f"merged {len(sources)} PDFs into {expected} pages",
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("pdf", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def edit_pdf(
        path: str,
        operations: list[pdf_engine.PdfOp],
        output_name: str | None = None,
    ) -> ArtifactResult:
        """Apply bounded page operations to an existing PDF: select_pages
        (pages: '1-3,5' — 1-based, keep-list) and rotate (degrees 90/180/270,
        pages optional — default all current pages). Operations apply in
        order; the result is a new PDF under artifacts/pdf/."""
        out_path: Path | None = None
        render = None
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "pdf", max_bytes=bounds.max_input_bytes
            )
            out_path = allocate_output_path(
                workspace_root,
                "pdf",
                output_name,
                default_stem=f"{source.stem}-edited-{time.strftime('%Y%m%d-%H%M%S')}",
            )
            expected = pdf_engine.apply_pdf_ops(source, out_path, operations)
            render = allocate_render_dir(work_root, "pdf-edit")
            outcome = qa_pdf(
                out_path, expected_pages=expected, render_dir=render, bounds=bounds
            )
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="pdf",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="edited PDF failed QA; it was removed",
                )
            applied = ", ".join(op.kind for op in operations)
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="pdf",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=f"applied {applied} to {source.name} → {expected} pages",
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("pdf", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def inspect_pdf(path: str) -> dict[str, Any]:
        """Inspect an existing PDF: page count, encryption, title/producer."""
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "pdf", max_bytes=bounds.max_input_bytes
            )
            facts = pdf_engine.inspect_pdf(source)
            facts.update(
                {
                    "path": artifact_display_path(workspace_root, source),
                    "bytes": source.stat().st_size,
                }
            )
            return facts
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            return {"error": _error_code_for(exc), "message": str(exc)[:500], "path": path}

    return Capability[CoreDeps](
        id="pdf-artifacts",
        description=DESCRIPTION,
        instructions=load_guidance("pdf.md"),
        toolsets=[toolset],
        defer_loading=True,
    )
