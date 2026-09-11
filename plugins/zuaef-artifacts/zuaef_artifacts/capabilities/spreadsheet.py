"""Spreadsheet artifact capability: create / revise / inspect structured
calculation workbooks under ``workspace/artifacts/spreadsheets/``."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.capabilities import Capability

from zuaef_agent.models import CoreDeps

from ..contracts import ArtifactBounds, ArtifactResult, failed_result
from ..engines import spreadsheet_engine
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
from ..process import MissingDependency, ProcessFailed
from ..qa import qa_workbook

logger = logging.getLogger(__name__)

DESCRIPTION = (
    "Structured calculation workbooks (.xlsx) 报价表/预算/财务测算/情景分析/"
    "对比表/跟踪表/经营模型: pricing, budgets, forecasts, scenario and "
    "sensitivity analysis 售价情景/利润测算, comparisons, trackers — with "
    "editable input assumptions the user can change 以后能自己改参数. Use "
    "when the outcome is numbers the user will reuse and adjust, or when "
    "the user asks for Excel."
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
    return f"workbook-{time.strftime('%Y%m%d-%H%M%S')}"


def _recalculate_into(
    staged: Path,
    out_path: Path,
    *,
    recalculate: bool,
    work_dir: Path,
    bounds: ArtifactBounds,
    warnings: list[str],
) -> None:
    """Deliver the workbook. With recalculate=True and LibreOffice present,
    a bounded xlsx→xlsx pass embeds cached formula results (formulas are
    preserved). Charts/tables are verified after the pass; a lossy pass
    falls back to the openpyxl original with a warning."""
    from openpyxl import load_workbook

    if not recalculate:
        shutil.move(str(staged), str(out_path))
        return
    try:
        spreadsheet_engine.recalculate(
            staged,
            out_path,
            timeout_seconds=bounds.process_timeout_seconds,
            work_dir=work_dir,
        )
    except MissingDependency as exc:
        warnings.append(
            f"{exc} — delivered without cached formula results (formulas intact)"
        )
        shutil.move(str(staged), str(out_path))
        return
    # Verify the recalculation pass did not lose structure (charts/tables).
    try:
        before = load_workbook(str(staged))
        after = load_workbook(str(out_path))
        before_charts = sum(
            len(getattr(ws, "_charts", ())) for ws in before.worksheets
        )
        after_charts = sum(len(getattr(ws, "_charts", ())) for ws in after.worksheets)
        if before_charts > after_charts:
            warnings.append(
                "recalculation pass dropped charts — delivered the original file "
                "(formulas intact; Excel/WPS will compute on open)"
            )
            shutil.move(str(staged), str(out_path))  # overwrites the recalc copy
            return
    except Exception as exc:  # noqa: BLE001 - verification is best-effort
        logger.info("recalc verification fallback: %s", exc)
        warnings.append("could not verify recalculated copy — delivered the original")
        shutil.move(str(staged), str(out_path))
        return
    # Success: the recalculated copy is the deliverable; the staging file is
    # intermediate and must never survive into the artifact roots (J1).
    staged.unlink(missing_ok=True)


def build_capability(
    *,
    bounds: ArtifactBounds,
    workspace_root: Path,
    work_root: Path,
) -> Capability[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset[CoreDeps]()

    @toolset.tool_plain
    def create_spreadsheet(
        spec: spreadsheet_engine.WorkbookSpec,
        output_name: str | None = None,
        recalculate: bool = True,
    ) -> ArtifactResult:
        """Create a structured calculation workbook (.xlsx) in one call.
        spec.sheets[]: name (≤31 chars) + blocks — matrix(start_cell, values;
        strings starting with '=' are formulas), format(range,
        number_format?, bold?, font_color?, fill_color?, border?, halign?,
        wrap?), widths(column→width), validation(range, allowed),
        conditional_format(range, operator, formula, fill_color?),
        table(range, name?), chart(chart_type bar|line|pie, anchor,
        data_range, categories_range?, title?). Keep derived business logic
        as formulas. Runs reopen/render QA inside this call; recalculate
        embeds cached formula results when LibreOffice is available."""
        staged: Path | None = None
        out_path: Path | None = None
        work: Path | None = None
        render: Path | None = None
        try:
            out_path = allocate_output_path(
                workspace_root, "spreadsheet", output_name, default_stem=_default_stem()
            )
            staged = out_path.parent / f"~{out_path.name}.staging.xlsx"
            workbook = spreadsheet_engine.build_workbook(spec)
            workbook.save(str(staged))

            work = allocate_work_dir(work_root, "xlsx-create")
            render = allocate_render_dir(work_root, "xlsx-create")
            warnings: list[str] = []
            _recalculate_into(
                staged,
                out_path,
                recalculate=recalculate,
                work_dir=work,
                bounds=bounds,
                warnings=warnings,
            )
            staged = None  # moved (delivered)
            expected = [sheet.name for sheet in spec.sheets]
            outcome = qa_workbook(
                out_path,
                expected_sheet_names=expected,
                work_dir=work,
                render_dir=render,
                bounds=bounds,
            )
            warnings.extend(outcome.warnings)
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="spreadsheet",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=warnings,
                    summary="workbook was created but failed QA; it was removed",
                )
            try:
                formula_cells = spreadsheet_engine.inspect_workbook(out_path)[
                    "total_formulas"
                ]
            except Exception:  # noqa: BLE001 - fact reporting is best-effort
                formula_cells = 0
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="spreadsheet",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=warnings,
                summary=(
                    f"created workbook with {len(expected)} sheet(s), "
                    f"{formula_cells} formula cell(s)"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if staged is not None:
                staged.unlink(missing_ok=True)
            elif out_path is not None:
                # Delivery had not completed; nothing valid may remain.
                out_path.unlink(missing_ok=True)
            return failed_result("spreadsheet", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if work is not None:
                cleanup_dir(work)
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def revise_spreadsheet(
        path: str,
        operations: list[spreadsheet_engine.SheetRevisionOp],
        output_name: str | None = None,
        recalculate: bool = False,
    ) -> ArtifactResult:
        """Apply bounded operations to an existing workbook: apply_blocks(
        sheet, blocks) reuses the creation blocks (matrix/format/widths/
        validation/conditional_format/table/chart) on an existing sheet;
        add_sheet(sheet) appends a whole new sheet. Formulas are preserved.
        Writes a versioned copy (…-rev2.xlsx); the source is unchanged."""
        staged: Path | None = None
        out_path: Path | None = None
        work: Path | None = None
        render: Path | None = None
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "spreadsheet", max_bytes=bounds.max_input_bytes
            )
            out_path = allocate_revision_path(
                workspace_root, "spreadsheet", source, output_name
            )
            from openpyxl import load_workbook

            workbook = load_workbook(str(source))
            changes = [
                spreadsheet_engine.apply_sheet_op(workbook, op) for op in operations
            ]
            staged = out_path.parent / f"~{out_path.name}.staging.xlsx"
            workbook.save(str(staged))

            work = allocate_work_dir(work_root, "xlsx-revise")
            render = allocate_render_dir(work_root, "xlsx-revise")
            warnings: list[str] = []
            _recalculate_into(
                staged,
                out_path,
                recalculate=recalculate,
                work_dir=work,
                bounds=bounds,
                warnings=warnings,
            )
            staged = None
            outcome = qa_workbook(
                out_path,
                expected_sheet_names=workbook.sheetnames,
                work_dir=work,
                render_dir=render,
                bounds=bounds,
            )
            warnings.extend(outcome.warnings)
            if outcome.qa_state == "failed":
                out_path.unlink(missing_ok=True)
                return ArtifactResult(
                    ok=False,
                    artifact_type="spreadsheet",
                    qa_state="failed",
                    error_code="qa_failed",
                    warnings=warnings,
                    summary="revision was applied but QA failed; it was removed",
                )
            return ArtifactResult(
                ok=True,
                artifact_path=artifact_display_path(workspace_root, out_path),
                artifact_type="spreadsheet",
                qa_state=outcome.qa_state,  # type: ignore[arg-type]
                warnings=warnings,
                summary=f"revised '{source.name}': {'; '.join(changes)}",
            )
        except Exception as exc:  # noqa: BLE001 - recoverable, format-local
            if staged is not None:
                staged.unlink(missing_ok=True)
            elif out_path is not None:
                # Delivery had not completed; nothing valid may remain.
                out_path.unlink(missing_ok=True)
            return failed_result("spreadsheet", _error_code_for(exc), exc)  # type: ignore[arg-type]
        finally:
            if work is not None:
                cleanup_dir(work)
            if render is not None:
                cleanup_dir(render)

    @toolset.tool_plain
    def inspect_spreadsheet(path: str) -> dict[str, Any]:
        """Inspect a workbook: sheets, dimensions, charts/tables, formula
        cells, and cached values for formulas when the file carries them."""
        try:
            source = resolve_existing_artifact(
                workspace_root, path, "spreadsheet", max_bytes=bounds.max_input_bytes
            )
            facts = spreadsheet_engine.inspect_workbook(source)
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
        id="spreadsheet-artifacts",
        description=DESCRIPTION,
        instructions=load_guidance("spreadsheet.md"),
        toolsets=[toolset],
        defer_loading=True,
    )
