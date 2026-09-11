"""PDF engine: create-from-content (via the DOCX engine + bounded office
conversion), office→PDF conversion, and page-level operations via pypdf.

One coherent stack (spec pack 07): pypdf owns page manipulation; LibreOffice
owns office conversion; poppler owns page rendering. Rendered page QA lives
in the shared qa module.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from .docx_engine import DocumentSpec
from .errors import UnsupportedOperation

MAX_MERGE_INPUTS = 10

# Office formats the converter accepts for convert_to_pdf.
CONVERTIBLE_SUFFIXES = {".docx", ".pptx", ".xlsx"}


class SelectPagesOp(BaseModel):
    """Keep only the given pages (1-based spec like '1-3,5,7-')."""

    kind: Literal["select_pages"] = "select_pages"
    pages: str = Field(min_length=1, max_length=200)


class RotatePagesOp(BaseModel):
    """Rotate the given pages (default: all current pages) by 90/180/270°."""

    kind: Literal["rotate"] = "rotate"
    degrees: Literal[90, 180, 270]
    pages: str | None = Field(default=None, max_length=200)


PdfOp = Annotated[SelectPagesOp | RotatePagesOp, Field(discriminator="kind")]


def pdf_ops_from_json(data: list[dict]) -> list[PdfOp]:
    try:
        ops = TypeAdapter(list[PdfOp]).validate_python(data)
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        raise ValueError(
            f"invalid pdf operation at {location or '<root>'}: {first.get('msg')}"
        ) from exc
    if not ops:
        raise ValueError("edit_pdf has no operations")
    if len(ops) > 20:
        raise ValueError("edit_pdf exceeds 20 operations")
    return ops


def parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse a 1-based page spec ('2', '1-3', '5-') to zero-based indices,
    validated against the current page count."""
    spec = (spec or "").strip()
    if not spec:
        raise ValueError("page spec is empty")
    picked: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d+)(?:-(\d*))?", part)
        if not match:
            raise ValueError(f"invalid page range: {part!r}")
        start = int(match.group(1))
        if start < 1:
            raise ValueError(f"page numbers start at 1: {part!r}")
        end_raw = match.group(2)
        end = int(end_raw) if end_raw else total_pages
        end = min(end, total_pages)
        if end < start:
            raise ValueError(f"page range end before start: {part!r}")
        if start > total_pages:
            raise ValueError(
                f"page {start} out of range (document has {total_pages} pages)"
            )
        picked.extend(range(start - 1, end))
    if not picked:
        raise ValueError("page spec selected no pages")
    return picked


def page_spec_subset(pages: list, spec: str | None) -> list:
    """Apply a page spec to the current page list (None/empty = all)."""
    if spec is None or not spec.strip():
        return list(pages)
    indices = parse_page_spec(spec, len(pages))
    return [pages[i] for i in indices]


def inspect_pdf(path) -> dict:
    """Reopen a .pdf with pypdf and report page count + basic metadata."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    meta = reader.metadata or {}
    return {
        "pages": len(reader.pages),
        "encrypted": bool(reader.is_encrypted),
        "title": (meta.get("/Title") or "")[:200] if meta else "",
        "producer": (meta.get("/Producer") or "")[:200] if meta else "",
    }


def create_pdf_from_spec(
    spec: DocumentSpec,
    output_path,
    *,
    workspace_root,
    work_dir,
    timeout_seconds: int,
) -> None:
    """Build the spec as a DOCX inside ``work_dir`` and convert it to
    ``output_path`` (a .pdf under the pdf artifact root)."""
    import shutil

    from ..process import office_convert
    from .docx_engine import build_document

    doc = build_document(spec, workspace_root)
    staged_docx = work_dir / "content.docx"
    doc.save(str(staged_docx))
    produced = office_convert(
        staged_docx,
        "pdf",
        work_dir,
        timeout_seconds=timeout_seconds,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(produced), str(output_path))


def convert_office_to_pdf(
    source,
    output_path,
    *,
    work_dir,
    timeout_seconds: int,
) -> None:
    """Convert one office document to ``output_path`` via LibreOffice."""
    import shutil

    from ..process import office_convert

    produced = office_convert(
        source,
        "pdf",
        work_dir,
        timeout_seconds=timeout_seconds,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(produced), str(output_path))


def merge_pdfs(sources: list, output_path, *, max_inputs: int = MAX_MERGE_INPUTS) -> int:
    """Merge ordered PDF inputs; returns the resulting page count."""
    from pypdf import PdfReader, PdfWriter

    if len(sources) < 2:
        raise ValueError("merge needs at least two PDF inputs")
    if len(sources) > max_inputs:
        raise ValueError(f"merge exceeds {max_inputs} inputs")
    writer = PdfWriter()
    total = 0
    for source in sources:
        reader = PdfReader(str(source))
        writer.append(reader)
        total += len(reader.pages)
    with open(output_path, "wb") as handle:
        writer.write(handle)
    return total


def apply_pdf_ops(source, output_path, ops: list[PdfOp]) -> int:
    """Apply sequential bounded page operations; returns the resulting page
    count."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(source))
    pages = list(reader.pages)
    for op in ops:
        if op.kind == "select_pages":
            pages = page_spec_subset(pages, op.pages)
            continue
        if op.kind == "rotate":
            targets = page_spec_subset(pages, op.pages)
            for page in targets:
                page.rotate(op.degrees)
            continue
        raise UnsupportedOperation(f"unknown pdf op: {op.kind!r}")
    writer = PdfWriter()
    for page in pages:
        writer.add_page(page)
    with open(output_path, "wb") as handle:
        writer.write(handle)
    return len(pages)
