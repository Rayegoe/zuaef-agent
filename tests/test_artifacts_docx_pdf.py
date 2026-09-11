"""P3 acceptance scenario (spec pack 09 P3 / 10 sections C & D):

1. Generate a multi-page Chinese business proposal DOCX with heading
   hierarchy, bullets, a table, and an image.
2. Convert it to PDF.
3. Reopen both formats.
4. Render both.
5. Revise a price and a payment term in the DOCX.
6. Regenerate/revalidate the client PDF from the revised document.

Requires the system tools (LibreOffice + poppler); skips cleanly when they
are absent (e.g. a bare ARM64 lane). The workspace lives under $HOME because
snap-packaged LibreOffice cannot read /tmp.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from zuaef_artifacts import paths, process
from zuaef_artifacts.contracts import ArtifactBounds
from zuaef_artifacts.engines import docx_engine, pdf_engine
from zuaef_artifacts.engines.docx_engine import (
    BulletListBlock,
    DocumentSpec,
    HeadingBlock,
    ImageBlock,
    PageBreakBlock,
    ParagraphBlock,
    ReplaceTextOp,
    TableBlock,
    UpdateTableCellOp,
)
from zuaef_artifacts.process import MissingDependency

RENDER_AVAILABLE = process.resolve_executable(process._OFFICE_CANDIDATES) is not None

BOUNDS = ArtifactBounds(
    max_input_bytes=25_000_000,
    max_output_bytes=25_000_000,
    process_timeout_seconds=180,
    render_max_pages=8,
)


@pytest.fixture()
def home_workspace():
    """A workspace + state pair under $HOME in a NON-hidden directory.

    Snap-packaged LibreOffice can neither read /tmp nor hidden directories
    under $HOME, so the conversion scenario needs a plain directory there.
    """
    if not RENDER_AVAILABLE:
        pytest.skip("LibreOffice not installed — render QA scenario skipped")
    base = Path(tempfile.mkdtemp(prefix="zuaef-artifacts-test-", dir=Path.home()))
    workspace = base / "workspace"
    state = base / "state"
    (workspace / "inbox").mkdir(parents=True)
    (workspace / "artifacts" / "docx").mkdir(parents=True)
    (workspace / "artifacts" / "pdf").mkdir(parents=True)
    state.mkdir(parents=True)
    yield workspace, state
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture()
def proposal_png(home_workspace):
    workspace, _ = home_workspace
    from PIL import Image

    image_path = workspace / "inbox" / "logo.png"
    Image.new("RGB", (240, 80), (31, 59, 99)).save(image_path, format="PNG")
    return image_path


def _proposal_spec(png: ImageBlock | None = None) -> DocumentSpec:
    blocks: list = [
        HeadingBlock(level=1, text="一、项目背景"),
        ParagraphBlock(
            text="客户计划在 2026 年第四季度完成门店数字化改造,本项目提供整体方案与实施服务。"
        ),
        BulletListBlock(items=["统一收银与库存", "会员数据打通", "经营看板"]),
        HeadingBlock(level=1, text="二、报价方案"),
        TableBlock(
            headers=["项目", "单价", "数量", "小计"],
            rows=[
                ["软件许可", "¥50,000", "1", "¥50,000"],
                ["实施服务", "¥30,000", "2", "¥60,000"],
                ["年度维保", "¥12,000", "1", "¥12,000"],
            ],
        ),
        HeadingBlock(level=2, text="2.1 付款方式"),
        ParagraphBlock(text="签约后支付 50%,验收后支付 50%。"),
        PageBreakBlock(),
        HeadingBlock(level=1, text="三、服务承诺"),
        ParagraphBlock(text="项目周期 12 周,提供 7×24 支持与季度回顾。"),
    ]
    if png is not None:
        blocks.append(png)
    return DocumentSpec(
        title="门店数字化改造方案",
        subtitle="提交客户版",
        blocks=blocks,
        header_text="机密文件",
        footer_text="2026 © Example Ltd",
    )


def test_p3_docx_pdf_acceptance_scenario(home_workspace, proposal_png):
    workspace, state = home_workspace
    image_block = ImageBlock(path="inbox/logo.png", caption="公司标识", width_inches=2.0)

    # 1. Create the proposal DOCX (spec via JSON round-trip to mimic the model path).
    spec = _proposal_spec(image_block)
    spec = DocumentSpec.model_validate(spec.model_dump())
    doc = docx_engine.build_document(spec, workspace)
    out_docx = paths.allocate_output_path(workspace, "docx", "客户方案.docx", default_stem="doc")
    doc.save(str(out_docx))
    assert out_docx.exists() and out_docx.stat().st_size > 0
    assert out_docx.parent == workspace / "artifacts" / "docx"
    assert out_docx.suffix == ".docx"

    # 2+4. Convert to PDF (render via LibreOffice = the conversion itself),
    #      reopen + render both.
    structure = docx_engine.inspect_document(out_docx)
    assert structure["headings"], "heading hierarchy must survive the save"
    assert structure["tables"], "the pricing table must survive the save"
    assert structure["images"] == 1, "the embedded image must survive the save"

    from zuaef_artifacts.qa import qa_docx, qa_pdf

    work = paths.allocate_work_dir(state, "scenario")
    render = paths.allocate_render_dir(state, "scenario")
    outcome = qa_docx(
        out_docx, inspect=structure, work_dir=work, render_dir=render, bounds=BOUNDS
    )
    assert outcome.qa_state in {"passed", "passed_with_warnings"}, outcome.warnings
    assert outcome.qa_state == "passed", outcome.warnings  # tools present here
    paths.cleanup_dir(work)
    paths.cleanup_dir(render)

    converted = paths.allocate_output_path(workspace, "pdf", None, default_stem="client")
    work = paths.allocate_work_dir(state, "scenario-convert")
    pdf_engine.convert_office_to_pdf(
        out_docx, converted, work_dir=work, timeout_seconds=BOUNDS.process_timeout_seconds
    )
    paths.cleanup_dir(work)
    assert converted.parent == workspace / "artifacts" / "pdf"
    facts = pdf_engine.inspect_pdf(converted)
    assert facts["pages"] >= 2, "proposal must span multiple pages"

    render = paths.allocate_render_dir(state, "scenario-render")
    pdf_outcome = qa_pdf(converted, render_dir=render, bounds=BOUNDS)
    paths.cleanup_dir(render)
    assert pdf_outcome.qa_state == "passed", pdf_outcome.warnings

    # 5. Revise a price and the payment term in the DOCX (bounded ops).
    from docx import Document as open_docx

    revised = paths.allocate_revision_path(workspace, "docx", out_docx, None)
    doc = open_docx(str(out_docx))
    change_1 = docx_engine.apply_revision_op(
        doc, ReplaceTextOp(find="¥50,000", replacement="¥48,000"), workspace
    )
    change_2 = docx_engine.apply_revision_op(
        doc,
        UpdateTableCellOp(table_index=0, row=3, col=3, text="¥58,000"),
        workspace,
    )
    term = docx_engine.apply_revision_op(
        doc, ReplaceTextOp(find="签约后支付 50%", replacement="签约后支付 70%"), workspace
    )
    doc.save(str(revised))
    assert {change_1, change_2, term}

    reopened = open_docx(str(revised))
    all_text = "\n".join(p.text for p in reopened.paragraphs) + "\n" + "\n".join(
        cell.text for table in reopened.tables for row in table.rows for cell in row.cells
    )
    assert "¥48,000" in all_text, "revised price must be present"
    assert "签约后支付 70%" in all_text, "revised payment term must be present"
    assert "年度维保" in all_text, "unrelated content must survive the revision"

    # 6. Reconvert the revised document into the client PDF and revalidate.
    revised_pdf = paths.allocate_output_path(workspace, "pdf", None, default_stem="client")
    work = paths.allocate_work_dir(state, "scenario-reconvert")
    pdf_engine.convert_office_to_pdf(
        revised, revised_pdf, work_dir=work, timeout_seconds=BOUNDS.process_timeout_seconds
    )
    paths.cleanup_dir(work)
    render = paths.allocate_render_dir(state, "scenario-render-2")
    final_outcome = qa_pdf(revised_pdf, render_dir=render, bounds=BOUNDS)
    paths.cleanup_dir(render)
    assert final_outcome.qa_state == "passed", final_outcome.warnings
    # Final artifact folders contain deliverables only (J1).
    assert not list((workspace / "artifacts" / "docx").glob("*.png"))
    assert not list((workspace / "artifacts" / "pdf").glob("*.png"))


def test_p3_unsupported_revision_fails_without_corrupting(home_workspace):
    """C5: an unsupported edit fails clearly and leaves the file untouched."""
    workspace, _ = home_workspace
    doc = docx_engine.build_document(_proposal_spec(), workspace)
    target = paths.allocate_output_path(workspace, "docx", "c5.docx", default_stem="doc")
    doc.save(str(target))
    before = target.read_bytes()

    from docx import Document as open_docx
    from zuaef_artifacts.engines.errors import UnsupportedOperation

    reopened = open_docx(str(target))
    with pytest.raises(UnsupportedOperation, match="heading not found"):
        docx_engine.apply_revision_op(
            reopened,
            docx_engine.InsertAfterHeadingOp(
                heading_text="不存在的标题",
                blocks=[ParagraphBlock(text="新段落")],
            ),
            workspace,
        )
    assert target.read_bytes() == before


def test_p3_render_dependency_absent_degrades(tmp_path, monkeypatch):
    """A missing renderer must degrade to passed_with_warnings, never fake
    a pass and never a crash."""
    from zuaef_artifacts import qa

    monkeypatch.setattr(
        "zuaef_artifacts.qa.office_convert",
        lambda *a, **k: (_ for _ in ()).throw(MissingDependency("LibreOffice absent")),
    )
    from docx import Document as open_docx

    docx_path = tmp_path / "a.docx"
    open_docx().save(str(docx_path))
    outcome = qa.qa_docx(
        docx_path,
        inspect={"paragraphs": 1, "tables": [], "headings": [], "images": 0},
        work_dir=tmp_path,
        render_dir=tmp_path,
        bounds=BOUNDS,
    )
    assert outcome.qa_state == "passed_with_warnings"
    assert "LibreOffice" in outcome.warnings[0]


def test_p3_bad_pdf_returns_recoverable_error(home_workspace):
    """D5: a malformed PDF is a recoverable format-local error (a raised
    exception the tool layer maps to a failed ArtifactResult, never a crash
    of the caller and never a fabricated success)."""
    workspace, _ = home_workspace
    bad = workspace / "artifacts" / "pdf" / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(Exception):  # noqa: B017 - pypdf error types vary
        pdf_engine.inspect_pdf(bad)
