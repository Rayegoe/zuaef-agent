"""P4 acceptance scenario (spec pack 09 P4 / 10 sections E & F):

- Generate a pricing workbook with editable input assumptions, formulas for
  three price scenarios, a summary area, and one chart.
- Generate a six-slide management deck from the same structured facts.
- Reopen and render both.
- Revise one assumption and verify dependent spreadsheet formulas remain.

Uses the same $HOME workspace fixture as the DOCX/PDF scenario (snap
LibreOffice confinement).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from zuaef_artifacts import paths, process
from zuaef_artifacts.contracts import ArtifactBounds
from zuaef_artifacts.engines import slides_engine, spreadsheet_engine
from zuaef_artifacts.engines.slides_engine import DeckSpec
from zuaef_artifacts.engines.spreadsheet_engine import (
    ChartBlock,
    FormatBlock,
    MatrixBlock,
    TableBlock,
    WidthsBlock,
    WorkbookSpec,
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
    if not RENDER_AVAILABLE:
        pytest.skip("LibreOffice not installed — render QA scenario skipped")
    base = Path(tempfile.mkdtemp(prefix="zuaef-artifacts-test-", dir=Path.home()))
    workspace = base / "workspace"
    state = base / "state"
    (workspace / "artifacts" / "slides").mkdir(parents=True)
    (workspace / "artifacts" / "spreadsheets").mkdir(parents=True)
    state.mkdir(parents=True)
    yield workspace, state
    shutil.rmtree(base, ignore_errors=True)


def _pricing_spec() -> WorkbookSpec:
    """Three suppliers × three price tiers: inputs stay editable, derived
    values are formulas referencing the inputs."""
    return WorkbookSpec(
        sheets=[
            spreadsheet_engine.SheetSpec(
                name="假设",
                blocks=[
                    MatrixBlock(
                        start_cell="A1",
                        values=[
                            ["参数", "数值"],
                            ["采购成本", 260],
                            ["运费", 25],
                            ["平台费率", 0.08],
                            ["目标毛利率", 0.35],
                        ],
                    ),
                    FormatBlock(range="B2:B5", number_format="0.00"),
                    FormatBlock(range="B5", number_format="0%"),
                    WidthsBlock(widths={"A": 18, "B": 12}),
                ],
            ),
            spreadsheet_engine.SheetSpec(
                name="报价测算",
                blocks=[
                    MatrixBlock(
                        start_cell="A1",
                        values=[
                            ["供应商", "售价", "成本", "毛利", "毛利率"],
                            ["供应商A", 399, "=假设!B2", "=B2-C2-假设!B3-B2*假设!B4", "=(B2-C2-假设!B3-B2*假设!B4)/B2"],
                            ["供应商A", 499, "=假设!B2", "=B3-C3-假设!B3-B3*假设!B4", "=(B3-C3-假设!B3-B3*假设!B4)/B3"],
                            ["供应商A", 599, "=假设!B2", "=B4-C4-假设!B3-B4*假设!B4", "=(B4-C4-假设!B3-B4*假设!B4)/B4"],
                            ["供应商B", 399, "=假设!B2+10", "=B5-C5-假设!B3-B5*假设!B4", "=(B5-C5-假设!B3-B5*假设!B4)/B5"],
                            ["供应商B", 499, "=假设!B2+10", "=B6-C6-假设!B3-B6*假设!B4", "=(B6-C6-假设!B3-B6*假设!B4)/B6"],
                            ["供应商B", 599, "=假设!B2+10", "=B7-C7-假设!B3-B7*假设!B4", "=(B7-C7-假设!B3-B7*假设!B4)/B7"],
                        ],
                    ),
                    FormatBlock(range="B2:C7", number_format="¥#,##0"),
                    FormatBlock(range="D2:D7", number_format="¥#,##0"),
                    FormatBlock(range="E2:E7", number_format="0.0%"),
                    FormatBlock(range="A1:E1", bold=True, fill_color="DCE6F1", border=True),
                    WidthsBlock(widths={"A": 12, "B": 10, "C": 10, "D": 10, "E": 10}),
                    TableBlock(range="A1:E7", name="PricingScenarios"),
                ],
            ),
            spreadsheet_engine.SheetSpec(
                name="汇总",
                blocks=[
                    MatrixBlock(
                        start_cell="A1",
                        values=[
                            ["售价档位", "供应商A毛利", "供应商B毛利"],
                            [399, "=报价测算!D2", "=报价测算!D5"],
                            [499, "=报价测算!D3", "=报价测算!D6"],
                            [599, "=报价测算!D4", "=报价测算!D7"],
                        ],
                    ),
                    FormatBlock(range="B2:C4", number_format="¥#,##0"),
                    ChartBlock(
                        chart_type="bar",
                        anchor="A7",
                        data_range="B1:C4",
                        categories_range="A2:A4",
                        title="三档售价毛利对比",
                    ),
                ],
            ),
        ]
    )


def _deck_spec() -> DeckSpec:
    return DeckSpec(
        title="供应商报价评审",
        subtitle="第 37 周",
        theme="business-light",
        slides=[
            slides_engine.TitleSlide(),
            slides_engine.KeyMessageSlide(message="三档售价均可达标,建议主推 499 档"),
            slides_engine.TitleBodySlide(
                title="要点",
                bullets=["成本可控", "毛利区间 120–230", "建议分档上架"],
            ),
            slides_engine.TableSlide(
                title="售价档位",
                headers=["档位", "供应商A毛利", "供应商B毛利"],
                rows=[["399", "¥58", "¥52"], ["499", "¥127", "¥121"], ["599", "¥195", "¥189"]],
            ),
            slides_engine.ChartSlide(
                title="毛利对比",
                chart_type="bar",
                categories=["399", "499", "599"],
                series_name="毛利",
                values=[58, 127, 195],
            ),
            slides_engine.ClosingSlide(title="下一步", bullets=["锁定 499 档", "两周后复盘"]),
        ],
    )


def test_p4_spreadsheet_acceptance(home_workspace):
    workspace, state = home_workspace
    spec = _pricing_spec()
    workbook = spreadsheet_engine.build_workbook(spec)
    out_xlsx = paths.allocate_output_path(
        workspace, "spreadsheet", "报价测算.xlsx", default_stem="wb"
    )
    workbook.save(str(out_xlsx))

    # F1/F6: two+ sheets, reopens; F2/F3: inputs editable, derived = formulas.
    facts = spreadsheet_engine.inspect_workbook(out_xlsx)
    assert facts["sheet_names"] == ["假设", "报价测算", "汇总"]
    assert facts["total_formulas"] > 0, "scenario values must be formulas"

    # F7: recalculation engine present → embed cached results, keep formulas.
    work = paths.allocate_work_dir(state, "xlsx-accept")
    recalc = paths.allocate_work_dir(state, "xlsx-recalc")
    spreadsheet_engine.recalculate(
        out_xlsx, recalc / "recalculated.xlsx", timeout_seconds=180, work_dir=work
    )
    recalc_facts = spreadsheet_engine.inspect_workbook(recalc / "recalculated.xlsx")
    paths.cleanup_dir(work)
    paths.cleanup_dir(recalc)
    assert recalc_facts["total_formulas"] > 0, "recalc must preserve formulas"
    cached = {
        sheet["name"]: sheet["cached_values"] for sheet in recalc_facts["sheets"]
    }
    gross = cached["报价测算"]
    assert any(
        isinstance(value, (int, float)) and value > 0
        for value in gross.values()
    ), f"recalculated cached values must contain real numbers: {gross}"

    # F5: summary chart present.
    summary = next(s for s in facts["sheets"] if s["name"] == "汇总")
    assert summary["charts"] == 1
    # Chart survives the recalc roundtrip (deliverable quality).
    summary_recalc = next(
        s for s in recalc_facts["sheets"] if s["name"] == "汇总"
    )
    assert summary_recalc["charts"] == 1, "chart must survive recalculation"

    # F4: number formats applied.
    from openpyxl import load_workbook

    reopened = load_workbook(str(out_xlsx))
    assert reopened["报价测算"]["B2"].number_format.startswith("¥")
    assert reopened["报价测算"]["E2"].number_format == "0.0%"

    # Revision: change one assumption, formulas must remain (P4 scenario).
    from zuaef_artifacts.engines.spreadsheet_engine import ApplyBlocksOp

    revised = paths.allocate_revision_path(workspace, "spreadsheet", out_xlsx, None)
    wb = load_workbook(str(out_xlsx))
    spreadsheet_engine.apply_sheet_op(
        wb,
        ApplyBlocksOp(
            sheet="假设",
            blocks=[MatrixBlock(start_cell="B2", values=[[280]])],
        ),
    )
    wb.save(str(revised))
    revised_facts = spreadsheet_engine.inspect_workbook(revised)
    assert revised_facts["total_formulas"] >= facts["total_formulas"], (
        "revision must not destroy dependent formulas"
    )
    assert revised_facts["sheets"][0]["cached_values"].get("B2") in (280, None)


def test_p4_slides_acceptance(home_workspace):
    workspace, state = home_workspace
    spec = _deck_spec()
    prs = slides_engine.build_deck(spec, workspace)
    out_pptx = paths.allocate_output_path(
        workspace, "slides", "周会汇报.pptx", default_stem="deck"
    )
    prs.save(str(out_pptx))

    # E3: reopen/inspect.
    facts = slides_engine.inspect_deck(out_pptx)
    assert facts["count"] == 6
    kinds = [len(s["texts"]) for s in facts["slides"]]
    assert kinds[1] >= 1  # key message slide has text
    assert facts["slides"][3]["tables"] == 1  # table slide
    assert facts["slides"][4]["charts"] == 1  # chart slide

    # E4: convert/render.
    from zuaef_artifacts.qa import qa_slides

    work = paths.allocate_work_dir(state, "slides-accept")
    render = paths.allocate_render_dir(state, "slides-accept")
    outcome = qa_slides(
        out_pptx,
        expected_slides=6,
        work_dir=work,
        render_dir=render,
        bounds=BOUNDS,
    )
    paths.cleanup_dir(work)
    paths.cleanup_dir(render)
    assert outcome.qa_state == "passed", outcome.warnings

    # E5: revise one slide without rebuilding the deck.
    from pptx import Presentation
    from zuaef_artifacts.engines.slides_engine import SetSlideTitleOp

    revised = paths.allocate_revision_path(workspace, "slides", out_pptx, None)
    deck = Presentation(str(out_pptx))
    change = slides_engine.apply_slide_op(
        deck, SetSlideTitleOp(slide_index=4, title="新的档位标题"), workspace
    )
    deck.save(str(revised))
    assert change
    revised_facts = slides_engine.inspect_deck(revised)
    assert revised_facts["count"] == 6, "revision must not change slide count"
    assert any(
        "新的档位标题" in text for text in revised_facts["slides"][3]["texts"]
    )


def test_p4_render_dependency_absent_degrades_to_structure(tmp_path, monkeypatch):
    """Without LibreOffice, spreadsheet QA degrades to structure with a
    warning (F8 discipline: preserve formulas, report the limitation)."""
    from zuaef_artifacts import qa

    monkeypatch.setattr(
        "zuaef_artifacts.qa.office_convert",
        lambda *a, **k: (_ for _ in ()).throw(MissingDependency("LibreOffice absent")),
    )
    workbook = spreadsheet_engine.build_workbook(_pricing_spec())
    path = tmp_path / "wb.xlsx"
    workbook.save(str(path))
    outcome = qa.qa_workbook(
        path,
        expected_sheet_names=["假设", "报价测算", "汇总"],
        work_dir=tmp_path,
        render_dir=tmp_path,
        bounds=BOUNDS,
    )
    assert outcome.qa_state == "passed_with_warnings"
    assert "LibreOffice" in outcome.warnings[0]
