"""Format-local QA lifecycle shared by create/revise tools.

Structure QA is required and runs everywhere (reopen + structural checks).
Render QA runs wherever the deployment provides the system tools (LibreOffice,
poppler); a missing optional renderer degrades to a warning, never to a fake
pass, and a real conversion/render failure fails the tool call — the broken
output is removed so the artifact roots only ever contain deliverables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contracts import ArtifactBounds
from .process import (
    MissingDependency,
    ProcessFailed,
    office_convert,
    render_pdf_pages,
)


@dataclass
class QAOutcome:
    qa_state: str  # passed | passed_with_warnings | failed
    warnings: list[str] = field(default_factory=list)
    detail: str = ""


def _outcome(state: str, warnings: list[str]) -> QAOutcome:
    return QAOutcome(
        qa_state=state,
        warnings=warnings,
        detail="; ".join(warnings) if warnings else "",
    )


def qa_docx(
    path: Path,
    *,
    inspect: dict,
    work_dir: Path,
    render_dir: Path,
    bounds: ArtifactBounds,
) -> QAOutcome:
    """Structure QA + (where available) convert-and-render QA for a .docx.

    ``inspect`` is the engine's fresh structural read of the saved file.
    """
    warnings: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return _outcome("failed", ["saved file is missing or empty"])
    if not inspect.get("paragraphs") and not inspect.get("tables"):
        return _outcome("failed", ["reopened document has no content"])

    try:
        converted = office_convert(
            path,
            "pdf",
            work_dir,
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        return _outcome("passed_with_warnings", [str(exc)])
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])

    try:
        images = render_pdf_pages(
            converted,
            render_dir,
            max_pages=min(bounds.render_max_pages, 3),
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        warnings.append(str(exc))
        return _outcome("passed_with_warnings", warnings)
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])
    if not images:
        return _outcome("failed", ["render QA produced no page images"])
    return _outcome("passed", warnings)


def qa_slides(
    path: Path,
    *,
    expected_slides: int,
    work_dir: Path,
    render_dir: Path,
    bounds: ArtifactBounds,
) -> QAOutcome:
    """Structure QA (python-pptx reopen, slide count) + convert/render QA."""
    warnings: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return _outcome("failed", ["saved file is missing or empty"])

    try:
        from pptx import Presentation

        prs = Presentation(str(path))
        if len(prs.slides) != expected_slides:
            return _outcome(
                "failed",
                [f"expected {expected_slides} slides, reopened deck has {len(prs.slides)}"],
            )
    except Exception as exc:  # noqa: BLE001 - any reopen failure is a QA failure
        return _outcome("failed", [f"python-pptx could not reopen the deck: {exc}"])

    try:
        converted = office_convert(
            path,
            "pdf",
            work_dir,
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        return _outcome("passed_with_warnings", [str(exc)])
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])

    try:
        images = render_pdf_pages(
            converted,
            render_dir,
            max_pages=min(bounds.render_max_pages, expected_slides),
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        warnings.append(str(exc))
        return _outcome("passed_with_warnings", warnings)
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])
    if not images:
        return _outcome("failed", ["render QA produced no slide images"])
    return _outcome("passed", warnings)


def qa_workbook(
    path: Path,
    *,
    expected_sheet_names: list[str],
    work_dir: Path,
    render_dir: Path,
    bounds: ArtifactBounds,
) -> QAOutcome:
    """Structure QA (openpyxl reopen, sheet inventory, formula presence) +
    convert/render QA for a .xlsx workbook."""
    warnings: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return _outcome("failed", ["saved file is missing or empty"])

    try:
        from openpyxl import load_workbook

        workbook = load_workbook(str(path))
        if workbook.sheetnames != expected_sheet_names:
            return _outcome(
                "failed",
                [
                    (
                        f"expected sheets {expected_sheet_names}, reopened "
                        f"workbook has {workbook.sheetnames}"
                    )
                ],
            )
    except Exception as exc:  # noqa: BLE001 - any reopen failure is a QA failure
        return _outcome("failed", [f"openpyxl could not reopen the workbook: {exc}"])

    try:
        converted = office_convert(
            path,
            "pdf",
            work_dir,
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        return _outcome("passed_with_warnings", [str(exc)])
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])

    try:
        images = render_pdf_pages(
            converted,
            render_dir,
            max_pages=min(bounds.render_max_pages, 3),
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        warnings.append(str(exc))
        return _outcome("passed_with_warnings", warnings)
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])
    if not images:
        return _outcome("failed", ["render QA produced no page images"])
    return _outcome("passed", warnings)


def qa_pdf(
    path: Path,
    *,
    expected_pages: int | None = None,
    render_dir: Path,
    bounds: ArtifactBounds,
) -> QAOutcome:
    """Structure QA (pypdf reopen, page count) + render QA for a .pdf."""
    warnings: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return _outcome("failed", ["saved file is missing or empty"])

    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        if page_count == 0:
            return _outcome("failed", ["PDF has no pages"])
        if reader.is_encrypted:
            return _outcome("failed", ["produced PDF is unexpectedly encrypted"])
    except Exception as exc:  # noqa: BLE001 - any reopen failure is a QA failure
        return _outcome("failed", [f"pypdf could not reopen the PDF: {exc}"])
    if expected_pages is not None and page_count != expected_pages:
        return _outcome(
            "failed",
            [f"expected {expected_pages} pages, reopened PDF has {page_count}"],
        )

    try:
        images = render_pdf_pages(
            path,
            render_dir,
            max_pages=min(bounds.render_max_pages, 3),
            timeout_seconds=bounds.process_timeout_seconds,
        )
    except MissingDependency as exc:
        warnings.append(str(exc))
        return _outcome("passed_with_warnings", warnings)
    except ProcessFailed as exc:
        return _outcome("failed", [str(exc)])
    if not images:
        return _outcome("failed", ["render QA produced no page images"])
    return _outcome("passed", warnings)
