"""DOCX artifact capability: create / revise / inspect editable formal
business documents under ``workspace/artifacts/docx/``."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.capabilities import Capability

from zuaef_agent.models import CoreDeps

from ..contracts import (
    ArtifactBounds,
    ArtifactResult,
    failed_result,
)
from ..engines import docx_engine
from ..engines.errors import UnsupportedOperation
from ..guidance import load_guidance
from ..paths import (
    PathRejected,
    allocate_output_path,
    allocate_render_dir,
    allocate_revision_path,
    allocate_work_dir,
    artifact_display_path,
    cleanup_dir,
    resolve_existing_artifact,
)
from ..process import MissingDependency
from ..qa import QAOutcome, qa_docx

DESCRIPTION = (
    "Editable formal business documents (Word/.docx): proposals 客户方案/提案, "
    "reports 报告, briefs, contract-like drafts 合同类草稿, meeting outputs, and "
    "documents the user will keep revising 以后还要改的可编辑文档. Use when the "
    "outcome is a formal long-form written deliverable that will be revised "
    "or reused, or when the user asks for Word."
)


def _default_stem() -> str:
    return f"document-{time.strftime('%Y%m%d-%H%M%S')}"


def _error_code_for(exc: Exception) -> str:
    if isinstance(exc, PathRejected):
        return "path_rejected"
    if isinstance(exc, UnsupportedOperation):
        return "unsupported_operation"
    if isinstance(exc, MissingDependency):
        return "missing_dependency"
    return "invalid_request" if isinstance(exc, ValueError) else "internal_error"


def _run_qa(
    out_path: Path,
    *,
    scope: str,
    work_root: Path,
    bounds: ArtifactBounds,
) -> tuple[QAOutcome, dict[str, Any]]:
    """Full mechanical QA lifecycle for one saved .docx. Returns the QA
    outcome and the fresh structural read of the saved file."""
    work = allocate_work_dir(work_root, scope)
    render = allocate_render_dir(work_root, scope)
    try:
        structure = docx_engine.inspect_document(out_path)
        outcome = qa_docx(
            out_path,
            inspect=structure,
            work_dir=work,
            render_dir=render,
            bounds=bounds,
        )
    finally:
        cleanup_dir(work)
        cleanup_dir(render)
    return outcome, structure


def build_capability(
    *,
    bounds: ArtifactBounds,
    workspace_root: Path,
    work_root: Path,
) -> Capability[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset[CoreDeps]()

    @toolset.tool_plain
    def create_docx(spec: docx_engine.DocumentSpec, output_name: str | None = None) -> ArtifactResult:
        """Create a formal editable business document (.docx) in one call,
        from a declarative spec: title, subtitle, and ordered blocks —
        heading(level 1-4, text), paragraph(text), bullet_list(items),
        numbered_list(items), quote(text), table(headers, rows, widths_cm?),
        image(path, caption?, width_inches?), page_break. Styling is a clean
        built-in business theme (A4). Runs reopen/convert/render QA inside
        this call and returns the workspace-relative artifact path."""
        out_path: Path | None = None
        try:
            docx_engine.validate_document_spec(spec)
            out_path = allocate_output_path(
                workspace_root, "docx", output_name, default_stem=_default_stem()
            )
            doc = docx_engine.build_document(spec, workspace_root)
            doc.save(str(out_path))

            outcome, structure = _run_qa(
                out_path, scope="docx-create", work_root=work_root, bounds=bounds
            )
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="docx",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="document was created but failed QA; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="docx",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=(
                    f"created .docx '{spec.title}' with {len(spec.blocks)} content "
                    f"block(s), {len(structure.get('tables', []))} table(s), "
                    f"{len(structure.get('headings', []))} heading(s)"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("docx", _error_code_for(exc), exc)  # type: ignore[arg-type]

    @toolset.tool_plain
    def revise_docx(
        path: str,
        operations: list[docx_engine.DocxRevisionOp],
        output_name: str | None = None,
    ) -> ArtifactResult:
        """Apply bounded structured edits to an existing .docx and re-run QA.
        Operations: replace_text(find, replacement, replace_all?),
        append_blocks(blocks), insert_after_heading(heading_text, blocks),
        update_title(title?, subtitle?), update_table_cell(table_index, row,
        col, text), replace_table(table_index, headers, rows). Writes a
        versioned copy (…-rev2.docx) unless output_name is given; the source
        file is never modified in place."""
        out_path: Path | None = None
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "docx", max_bytes=bounds.max_input_bytes
            )
            out_path = allocate_revision_path(
                workspace_root, "docx", source, output_name
            )
            from docx import Document

            doc = Document(str(source))
            changes = [
                docx_engine.apply_revision_op(doc, op, workspace_root)
                for op in operations
            ]
            doc.save(str(out_path))

            outcome, structure = _run_qa(
                out_path, scope="docx-revise", work_root=work_root, bounds=bounds
            )
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="docx",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=outcome.warnings,
                    summary="revision was applied but QA failed; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="docx",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=outcome.warnings,
                summary=(
                    f"revised '{source.name}': {'; '.join(changes)} — "
                    f"{len(structure.get('headings', []))} heading(s), "
                    f"{len(structure.get('tables', []))} table(s)"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if out_path is not None:
                out_path.unlink(missing_ok=True)
            return failed_result("docx", _error_code_for(exc), exc)  # type: ignore[arg-type]

    @toolset.tool_plain
    def inspect_docx(path: str) -> dict[str, Any]:
        """Inspect the structure of an existing .docx (headings, tables,
        paragraph/image counts) without returning the full text."""
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "docx", max_bytes=bounds.max_input_bytes
            )
            structure = docx_engine.inspect_document(source)
            structure.update(
                {
                    "path": artifact_display_path(workspace_root, source),
                    "bytes": source.stat().st_size,
                }
            )
            return structure
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            return {"error": _error_code_for(exc), "message": str(exc)[:500], "path": path}

    return Capability[CoreDeps](
        id="docx-artifacts",
        description=DESCRIPTION,
        instructions=load_guidance("docx.md"),
        toolsets=[toolset],
        defer_loading=True,
    )
