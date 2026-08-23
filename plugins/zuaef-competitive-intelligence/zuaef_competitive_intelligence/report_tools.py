"""Report delivery tools: ``render_report`` and ``render_report_preview``.

Deterministic mechanical delivery (ADR-008/ADR-009): render the current
run's ``report.md`` to PDF + DOCX, then rasterize the PDF into preview
pages + a contact sheet. Mechanical warnings only — never a claim that
layout quality passed (LESSONS §8).
"""

from __future__ import annotations

import json
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.models import CoreDeps

from .report_renderer import RenderError, render_markdown_document
from .work_product_tools import artifact_root

_PREVIEW_DPI = 100
_CONTACT_THUMB = 260
_CONTACT_COLS = 4


class ReportToolError(RuntimeError):
    """Raised for programming errors only; tool-level failures return
    structured JSON error results (repo convention)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _error_result(code: str, message: str) -> str:
    return json.dumps(
        {"error": {"code": code, "message": message}}, ensure_ascii=False
    )


def make_report_toolset() -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=(
            "Report delivery is deterministic: render_report turns the "
            "current run's report.md into report.pdf + report.docx (the "
            "report must be saved with save_work_product(kind='report') "
            "first); render_report_preview rasterizes the PDF into "
            "preview/page-*.png plus a contact sheet and reports mechanical "
            "warnings only. A successful render is not a visual-quality "
            "verdict — record any real review in qa.md."
        )
    )

    @toolset.tool
    async def render_report(
        ctx: RunContext[CoreDeps], style: str | None = "executive"
    ) -> str:
        """Render the current run's report.md to report.pdf and report.docx.

        ``style`` is accepted for forward compatibility but rendering is
        deterministic; the report Skill constrains the markdown subset.
        Fails specifically when report.md is missing or unrenderable.

        中文关键词：渲染报告、生成PDF、生成Word文档、导出报告。
        """
        root = artifact_root(ctx.deps.workspace_root, ctx.deps.run_id)
        report_md = root / "report.md"
        if not report_md.is_file():
            return _error_result(
                "REPORT_MISSING",
                f"no report.md in {root}; save it first with "
                "save_work_product(kind='report', ...)",
            )
        try:
            facts = render_markdown_document(
                report_md.read_text(encoding="utf-8"),
                pdf_path=root / "report.pdf",
                docx_path=root / "report.docx",
                base_dir=root,
            )
        except RenderError as exc:
            return _error_result(exc.code, exc.message)
        # Renderer boundary: any renderer-family failure becomes a specific
        # JSON error result so the run survives (precedent: runtime receipt
        # boundary uses the same wide catch with noqa: BLE001).
        except Exception as exc:  # noqa: BLE001 — renderer boundary failures
            return _error_result(
                "RENDER_FAILED",
                f"render failed for {report_md!s}: {type(exc).__name__}: {exc}",
            )
        return json.dumps(
            {
                "report.pdf": str((root / "report.pdf").relative_to(ctx.deps.workspace_root)),
                "report.docx": str((root / "report.docx").relative_to(ctx.deps.workspace_root)),
                "pages": facts["pages"],
                "markdown_chars": facts["markdown_chars"],
                "cjk_font": facts["cjk_font"],
            },
            ensure_ascii=False,
        )

    @toolset.tool
    async def render_report_preview(
        ctx: RunContext[CoreDeps], max_pages: int | None = None
    ) -> str:
        """Rasterize the current run's report.pdf into preview/page-*.png
        plus preview/contact-sheet.png for operator/model visual review.

        Returns mechanical facts: page count, rasterized count, contact
        sheet path and warnings (rasterize failure / zero-text page / image
        decode failure). No visual-quality verdict is implied.

        中文关键词：页面预览、缩略图、联系表、PDF转图片。
        """
        root = artifact_root(ctx.deps.workspace_root, ctx.deps.run_id)
        pdf_path = root / "report.pdf"
        if not pdf_path.is_file():
            return _error_result(
                "PDF_MISSING", "no report.pdf yet; run render_report first"
            )
        preview_dir = root / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []
        try:
            import pymupdf  # PyMuPDF

            with pymupdf.open(str(pdf_path)) as document:
                page_count = document.page_count
                cap = min(page_count, max_pages) if max_pages and max_pages > 0 else page_count
                rendered: list[str] = []
                for index in range(cap):
                    try:
                        page = document.load_page(index)
                        pix = page.get_pixmap(dpi=_PREVIEW_DPI)
                        target = preview_dir / f"page-{index + 1:03d}.png"
                        pix.save(str(target))
                        rendered.append(target.name)
                        text = page.get_text().strip()
                        if not text:
                            warnings.append(
                                f"page {index + 1}: extracted zero text"
                            )
                    except Exception as exc:  # noqa: BLE001 — per-page warning
                        warnings.append(
                            f"page {index + 1}: rasterization failed ({exc})"
                        )
        except RenderError:
            raise
        except Exception as exc:
            raise ReportToolError(
                "PDF_UNREADABLE",
                f"report.pdf cannot be opened: {type(exc).__name__}: {exc}",
            ) from exc

        contact_sheet: str | None = None
        if rendered:
            try:
                from PIL import Image as PILImage

                thumbs: list[Any] = []
                for name in rendered:
                    with PILImage.open(preview_dir / name) as image:
                        thumb = image.copy()
                        thumb.thumbnail((_CONTACT_THUMB, _CONTACT_THUMB))
                        thumbs.append(thumb.convert("RGB"))
                if thumbs:
                    columns = _CONTACT_COLS
                    rows = (len(thumbs) + columns - 1) // columns
                    sheet = PILImage.new(
                        "RGB",
                        (columns * (_CONTACT_THUMB + 8), rows * (_CONTACT_THUMB + 8)),
                        (245, 245, 245),
                    )
                    for index, thumb in enumerate(thumbs):
                        x = (index % columns) * (_CONTACT_THUMB + 8) + 4
                        y = (index // columns) * (_CONTACT_THUMB + 8) + 4
                        sheet.paste(thumb, (x, y))
                    sheet_path = preview_dir / "contact-sheet.png"
                    sheet.save(str(sheet_path))
                    contact_sheet = str(
                        sheet_path.relative_to(ctx.deps.workspace_root)
                    )
            except Exception as exc:  # noqa: BLE001 — mechanical decode warning
                warnings.append(f"contact sheet failed: {exc}")

        return json.dumps(
            {
                "page_count": page_count,
                "rendered_pages": len(rendered),
                "contact_sheet": contact_sheet,
                "warnings": warnings,
                "preview_dir": str(preview_dir.relative_to(ctx.deps.workspace_root)),
            },
            ensure_ascii=False,
        )

    return toolset