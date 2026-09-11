"""DOCX engine: declarative document spec → styled .docx, bounded revisions,
and structure/render QA.

Styling is opinionated and limited (spec pack 07): one clean default business
theme (A4, restrained fonts with a CJK-aware east-asian face, built-in heading
and list styles). Direct OOXML manipulation is used only where python-docx
has no API — the east-asian font attribute on the Normal style.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from ..paths import resolve_input_path
from .errors import UnsupportedOperation

# ── content bounds (conservative, plugin-local) ───────────────────────────

MAX_TITLE_CHARS = 200
MAX_TEXT_CHARS = 20_000
MAX_ITEM_CHARS = 2_000
MAX_LIST_ITEMS = 100
MAX_TABLE_ROWS = 200
MAX_TABLE_COLS = 30
MAX_CELL_CHARS = 1_000
MAX_BLOCKS = 300


def _bounded_text(value: str, cap: int, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")
    if len(value) > cap:
        raise ValueError(f"{what} exceeds {cap} characters")
    return value


def _bounded_cell(value: str, cap: int, what: str) -> str:
    """Cells may legitimately be empty (备注列、留白); only bound length."""
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a string")
    if len(value) > cap:
        raise ValueError(f"{what} exceeds {cap} characters")
    return value


# ── declarative document spec ─────────────────────────────────────────────


class HeadingBlock(BaseModel):
    kind: Literal["heading"] = "heading"
    level: int = Field(default=1, ge=1, le=4)
    text: str

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.text, MAX_TEXT_CHARS, "heading text")


class ParagraphBlock(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    text: str

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.text, MAX_TEXT_CHARS, "paragraph text")


class BulletListBlock(BaseModel):
    kind: Literal["bullet_list"] = "bullet_list"
    items: list[str]

    def model_post_init(self, __context: Any, /) -> None:
        if not self.items or len(self.items) > MAX_LIST_ITEMS:
            raise ValueError("bullet_list needs 1..100 items")
        for item in self.items:
            _bounded_text(item, MAX_ITEM_CHARS, "bullet item")


class NumberedListBlock(BaseModel):
    kind: Literal["numbered_list"] = "numbered_list"
    items: list[str]

    def model_post_init(self, __context: Any, /) -> None:
        if not self.items or len(self.items) > MAX_LIST_ITEMS:
            raise ValueError("numbered_list needs 1..100 items")
        for item in self.items:
            _bounded_text(item, MAX_ITEM_CHARS, "list item")


class QuoteBlock(BaseModel):
    kind: Literal["quote"] = "quote"
    text: str

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.text, MAX_TEXT_CHARS, "quote text")


class TableBlock(BaseModel):
    kind: Literal["table"] = "table"
    headers: list[str]
    rows: list[list[str]]
    widths: list[float] | None = None  # column widths in cm

    def model_post_init(self, __context: Any, /) -> None:
        if not self.headers or len(self.headers) > MAX_TABLE_COLS:
            raise ValueError(f"table needs 1..{MAX_TABLE_COLS} columns")
        for row in self.rows:
            if len(row) != len(self.headers):
                raise ValueError("every table row must match the header width")
        if len(self.rows) > MAX_TABLE_ROWS:
            raise ValueError(f"table exceeds {MAX_TABLE_ROWS} rows")
        for cell in [*self.headers, *[c for row in self.rows for c in row]]:
            _bounded_cell(str(cell), MAX_CELL_CHARS, "table cell")


class ImageBlock(BaseModel):
    kind: Literal["image"] = "image"
    path: str
    caption: str | None = None
    width_inches: float | None = Field(default=None, gt=0.5, lt=8.0)


class PageBreakBlock(BaseModel):
    kind: Literal["page_break"] = "page_break"


Block = Annotated[
    HeadingBlock | ParagraphBlock | BulletListBlock | NumberedListBlock | QuoteBlock | TableBlock | ImageBlock | PageBreakBlock,
    Field(discriminator="kind"),
]


class DocumentSpec(BaseModel):
    """Declarative document: metadata + ordered content blocks.

    Shared by create_docx and create_pdf (the PDF create route renders the
    same spec through the DOCX engine and a bounded office conversion).
    """

    title: str
    subtitle: str | None = None
    blocks: list[Block] = Field(default_factory=list)
    header_text: str | None = None
    footer_text: str | None = None

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.title, MAX_TITLE_CHARS, "title")
        if self.blocks and len(self.blocks) > MAX_BLOCKS:
            raise ValueError(f"document exceeds {MAX_BLOCKS} blocks")
        if self.subtitle is not None:
            _bounded_text(self.subtitle, MAX_TITLE_CHARS, "subtitle")
        for text in (self.header_text, self.footer_text):
            if text is not None:
                _bounded_text(text, 500, "header/footer text")


def validate_document_spec(spec: DocumentSpec) -> None:
    """Cross-block validation beyond per-field checks."""
    if not spec.blocks:
        raise ValueError("document has no content blocks")


def spec_from_json(data: dict[str, Any]) -> DocumentSpec:
    """Parse+validate a spec dict, mapping pydantic errors to a readable
    ValueError (the model sees one clear message, not a traceback)."""
    try:
        spec = DocumentSpec.model_validate(data)
    except ValidationError as exc:
        raise ValueError(_first_error(exc)) from exc
    validate_document_spec(spec)
    return spec


def _first_error(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error.get("loc", ()))
    return f"invalid document spec at {location or '<root>'}: {error.get('msg')}"


# ── revision operations ───────────────────────────────────────────────────


class ReplaceTextOp(BaseModel):
    kind: Literal["replace_text"] = "replace_text"
    find: str
    replacement: str
    replace_all: bool = False

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.find, 200, "find text")


class AppendBlocksOp(BaseModel):
    kind: Literal["append_blocks"] = "append_blocks"
    blocks: list[Block]

    def model_post_init(self, __context: Any, /) -> None:
        if not self.blocks or len(self.blocks) > 50:
            raise ValueError("append_blocks needs 1..50 blocks")


class InsertAfterHeadingOp(BaseModel):
    kind: Literal["insert_after_heading"] = "insert_after_heading"
    heading_text: str
    blocks: list[Block]

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_text(self.heading_text, 200, "heading_text")
        if not self.blocks or len(self.blocks) > 50:
            raise ValueError("insert_after_heading needs 1..50 blocks")


class UpdateTitleOp(BaseModel):
    kind: Literal["update_title"] = "update_title"
    title: str | None = None
    subtitle: str | None = None

    def model_post_init(self, __context: Any, /) -> None:
        if self.title is None and self.subtitle is None:
            raise ValueError("update_title needs a title and/or subtitle")
        if self.title is not None:
            _bounded_text(self.title, MAX_TITLE_CHARS, "title")
        if self.subtitle is not None:
            _bounded_text(self.subtitle, MAX_TITLE_CHARS, "subtitle")


class UpdateTableCellOp(BaseModel):
    kind: Literal["update_table_cell"] = "update_table_cell"
    table_index: int = Field(ge=0)
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    text: str = ""

    def model_post_init(self, __context: Any, /) -> None:
        _bounded_cell(self.text, MAX_CELL_CHARS, "cell text")


class ReplaceTableOp(BaseModel):
    kind: Literal["replace_table"] = "replace_table"
    table_index: int = Field(ge=0)
    headers: list[str]
    rows: list[list[str]]

    def model_post_init(self, __context: Any, /) -> None:
        # Reuse TableBlock validation by constructing one.
        TableBlock(headers=self.headers, rows=self.rows)


DocxRevisionOp = Annotated[
    ReplaceTextOp | AppendBlocksOp | InsertAfterHeadingOp | UpdateTitleOp | UpdateTableCellOp | ReplaceTableOp,
    Field(discriminator="kind"),
]


def revision_ops_from_json(data: list[dict[str, Any]]) -> list[DocxRevisionOp]:
    """Parse a revision op list; unknown kinds fail with a clear message."""
    try:
        ops = TypeAdapter(list[DocxRevisionOp]).validate_python(data)
    except ValidationError as exc:
        raise ValueError(_first_error(exc)) from exc
    if not ops:
        raise ValueError("revision has no operations")
    if len(ops) > 50:
        raise ValueError("revision exceeds 50 operations")
    return ops


# ── build ─────────────────────────────────────────────────────────────────


def build_document(spec: DocumentSpec, workspace_root) -> Document:  # noqa: F821
    """Render a DocumentSpec into a python-docx Document (unsaved)."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    _apply_theme(doc)
    _apply_page(doc)

    if spec.title:
        doc.add_heading(spec.title, level=0)
    if spec.subtitle:
        subtitle = doc.add_paragraph(spec.subtitle, style="Subtitle")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for block in spec.blocks:
        _append_block(doc, block, workspace_root)
    return doc


def _apply_theme(doc) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    # CJK business documents need an explicit east-asian face; python-docx
    # exposes no API for it, so this single attribute is set via OOXML.
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    for style_name in ("Heading 1", "Heading 2"):
        try:
            doc.styles[style_name].font.color.rgb = RGBColor(0x1F, 0x3B, 0x63)
        except KeyError:  # pragma: no cover - default template has them
            continue


def _apply_page(doc) -> None:
    from docx.shared import Mm

    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    for side in ("top", "bottom", "left", "right"):
        setattr(section, f"{side}_margin", Mm(25.4))


def _append_block(doc, block: Any, workspace_root) -> list[Any]:
    """Append one spec block at the end of the document; returns the created
    elements (used by insert-after-heading to relocate them)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt

    kind = block.kind  # discriminated union tag

    if kind == "heading":
        return [doc.add_heading(block.text, level=block.level)._p]
    if kind == "paragraph":
        return [doc.add_paragraph(block.text)._p]
    if kind == "bullet_list":
        return [
            doc.add_paragraph(item, style="List Bullet")._p for item in block.items
        ]
    if kind == "numbered_list":
        return [
            doc.add_paragraph(item, style="List Number")._p for item in block.items
        ]
    if kind == "quote":
        quote = doc.add_paragraph()
        run = quote.add_run(block.text)
        run.italic = True
        quote.paragraph_format.left_indent = Inches(0.4)
        return [quote._p]
    if kind == "table":
        return _append_table(doc, block.headers, block.rows, getattr(block, "widths", None))
    if kind == "image":
        source = resolve_input_path(
            workspace_root, block.path, max_bytes=25_000_000
        )
        doc.add_picture(
            str(source), width=Inches(block.width_inches) if block.width_inches else None
        )
        last = doc.paragraphs[-1]
        last.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elements = [last._p]
        if block.caption:
            caption = doc.add_paragraph(block.caption)
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in caption.runs:
                run.italic = True
                run.font.size = Pt(9)
            elements.append(caption._p)
        return elements
    if kind == "page_break":
        doc.add_page_break()
        return [doc.paragraphs[-1]._p]
    raise UnsupportedOperation(f"unknown block kind: {kind!r}")


def _append_table(doc, headers, rows, widths=None) -> list[Any]:
    from docx.shared import Cm

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:  # pragma: no cover - default template has Table Grid
        pass
    for col, header in enumerate(headers):
        cell = table.rows[0].cells[col]
        cell.text = str(header)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
    for row_i, row in enumerate(rows, start=1):
        for col, value in enumerate(row):
            table.rows[row_i].cells[col].text = str(value)
    if widths:
        for col, width in enumerate(widths[: len(headers)]):
            for row in table.rows:
                row.cells[col].width = Cm(width)
    return [table._tbl]


# ── bounded revisions ─────────────────────────────────────────────────────


def _iter_all_paragraphs(doc):
    for paragraph in doc.paragraphs:
        yield paragraph
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def _rewrite_paragraph_text(paragraph, new_text: str) -> None:
    """Replace a paragraph's text, keeping the first run's formatting.
    Formatting variation inside the paragraph is intentionally flattened —
    the documented bounded-edit tradeoff."""
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(new_text)


def _find_heading(doc, heading_text: str):
    for paragraph in doc.paragraphs:
        if (
            paragraph.style is not None
            and paragraph.style.name
            and paragraph.style.name.startswith("Heading")
            and paragraph.text.strip() == heading_text.strip()
        ):
            return paragraph
    raise UnsupportedOperation(f"heading not found: {heading_text!r}")


def _insert_blocks_after(doc, anchor_paragraph, blocks, workspace_root) -> None:
    new_elements: list[Any] = []
    for block in blocks:
        new_elements.extend(_append_block(doc, block, workspace_root))
    # The blocks were appended at the body end; relocate them after the
    # anchor, preserving their relative order.
    for element in reversed(new_elements):
        anchor_paragraph._p.addnext(element)


def apply_revision_op(doc, op: Any, workspace_root) -> str:
    """Apply one bounded revision op; returns a short change statement."""
    kind = op.kind

    if kind == "replace_text":
        replaced = 0
        for paragraph in _iter_all_paragraphs(doc):
            if op.find in paragraph.text:
                new_text = (
                    paragraph.text.replace(op.find, op.replacement)
                    if op.replace_all
                    else paragraph.text.replace(op.find, op.replacement, 1)
                )
                _rewrite_paragraph_text(paragraph, new_text)
                replaced += 1
                if not op.replace_all:
                    break
        if replaced == 0:
            raise UnsupportedOperation(f"find text not found: {op.find!r}")
        return f"replaced {replaced} occurrence(s) of the find text"

    if kind == "append_blocks":
        for block in op.blocks:
            _append_block(doc, block, workspace_root)
        return f"appended {len(op.blocks)} block(s)"

    if kind == "insert_after_heading":
        anchor = _find_heading(doc, op.heading_text)
        _insert_blocks_after(doc, anchor, op.blocks, workspace_root)
        return f"inserted {len(op.blocks)} block(s) after heading {op.heading_text!r}"

    if kind == "update_title":
        changed: list[str] = []
        if op.title is not None:
            title_para = next(
                (
                    p
                    for p in doc.paragraphs
                    if p.style is not None and p.style.name == "Title"
                ),
                None,
            )
            if title_para is None:
                raise UnsupportedOperation("document has no Title paragraph")
            _rewrite_paragraph_text(title_para, op.title)
            changed.append("title")
        if op.subtitle is not None:
            subtitle_para = next(
                (
                    p
                    for p in doc.paragraphs
                    if p.style is not None and p.style.name == "Subtitle"
                ),
                None,
            )
            if subtitle_para is None:
                raise UnsupportedOperation("document has no Subtitle paragraph")
            _rewrite_paragraph_text(subtitle_para, op.subtitle)
            changed.append("subtitle")
        return f"updated {' and '.join(changed)}"

    if kind == "update_table_cell":
        tables = doc.tables
        if op.table_index >= len(tables):
            raise UnsupportedOperation(
                f"table index {op.table_index} out of range ({len(tables)} tables)"
            )
        table = tables[op.table_index]
        try:
            cell = table.rows[op.row].cells[op.col]
        except IndexError as exc:
            raise UnsupportedOperation(
                f"cell ({op.row}, {op.col}) out of range for table {op.table_index}"
            ) from exc
        cell.text = op.text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = False
                run.font.size = None
        return f"updated table {op.table_index} cell ({op.row}, {op.col})"

    if kind == "replace_table":
        tables = doc.tables
        if op.table_index >= len(tables):
            raise UnsupportedOperation(
                f"table index {op.table_index} out of range ({len(tables)} tables)"
            )
        old = tables[op.table_index]
        new_elements = _append_table(doc, op.headers, op.rows)
        old._tbl.addprevious(new_elements[0])
        old._tbl.getparent().remove(old._tbl)
        return f"replaced table {op.table_index}"

    raise UnsupportedOperation(f"unknown revision op: {kind!r}")


# ── inspection (QA + model-facing structure) ──────────────────────────────


def inspect_document(path) -> dict[str, Any]:
    """Reopen a .docx and report its deterministic structure."""
    from docx import Document

    doc = Document(str(path))
    headings = []
    for paragraph in doc.paragraphs:
        style = paragraph.style.name if paragraph.style is not None else ""
        if style.startswith("Heading") and paragraph.text.strip():
            headings.append({"level": style, "text": paragraph.text.strip()[:120]})
        elif style == "Title" and paragraph.text.strip():
            headings.append({"level": "Title", "text": paragraph.text.strip()[:120]})
    tables = [
        {"rows": len(t.rows), "cols": len(t.columns), "header": [c.text[:60] for c in t.rows[0].cells] if t.rows else []}
        for t in doc.tables
    ]
    return {
        "paragraphs": sum(1 for p in doc.paragraphs if p.text.strip()),
        "headings": headings,
        "tables": tables,
        "sections": len(doc.sections),
        "images": sum(1 for shape in doc.inline_shapes),
    }
