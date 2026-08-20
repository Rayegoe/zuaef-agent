"""Document-first learning case packet tests (v1.2 T009/T010/T011).

The case packet is Markdown files + a minimal addressing manifest. The tests
assert what the spec protects: real request/context/output/sources/revised
text survive the round trip verbatim, and no mandatory derived taxonomy
(trigger_signal / action / weight / approved_by) is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "learning" / "cases"

CASE_ID = "summer-nail-rewrite-20260819"
CASE_DIR = CASES / CASE_ID


@pytest.fixture(scope="module")
def packet() -> dict:
    manifest = json.loads((CASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    return {"manifest": manifest, "dir": CASE_DIR}


def test_packet_layout_documents_not_fields(packet: dict):
    """T009: the packet is document-first — real prose files + a minimal
    manifest that only addresses files. It must NOT require a semantic
    taxonomy."""
    for key in ("request", "context", "output", "sources", "revised"):
        rel = packet["manifest"][key]
        assert (packet["dir"] / rel).is_file(), f"missing packet file: {rel}"
    assert "case_id" in packet["manifest"]
    assert not any(
        key in packet["manifest"]
        for key in ("trigger_signal", "action", "weight", "approved_by", "score")
    ), "manifest must not carry a mandatory derived taxonomy (QUALITY_LOOP §3)"


def test_request_preserves_raw_feedback(packet: dict):
    """The original request keeps the raw human feedback chain (老板反馈 /
    太模板化 / 开头还是有点AI) — judgment stays rich, not reduced to a label."""
    text = (packet["dir"] / packet["manifest"]["request"]).read_text(encoding="utf-8")
    assert "结论前置" in text or "先看到结论" in text
    assert "价格" in text
    assert "模板" in text or "模板味" in text
    assert "开头还是有点 AI" in text


def test_output_and_revised_are_real_full_text(packet: dict):
    """The output and revised files carry the FULL before/after prose — the
    raw texts this case exists to preserve (QUALITY_LOOP §11: preserve
    original before/after text and human comments; they are authoritative)."""
    output = (packet["dir"] / packet["manifest"]["output"]).read_text(encoding="utf-8")
    revised = (packet["dir"] / packet["manifest"]["revised"]).read_text(encoding="utf-8")
    assert output.startswith("李姐，这篇我按您老板的口味现场改了一版")
    assert "夏天的指尖，不必太热闹" in output
    assert "今年我把美甲的标准改了" in revised or "我们做平价彩妆" in revised
    assert len(output) > 100 and len(revised) > 100


def test_sources_trace_real_material_locations(packet: dict):
    """Sources are concrete pointers a human can follow (private material
    paths for a writing case vs URLs for a research case) — never a fake
    public URL pretending to prove support."""
    text = (packet["dir"] / packet["manifest"]["sources"]).read_text(encoding="utf-8")
    assert "trajectory.jsonl" in text
    assert "msg-004" in text
    assert "workspace/cases/stillevo-beauty" in text


def test_llm_reviewer_prompt_only_is_prose_driven(tmp_path):
    """T010: the reviewer produces prose, not a fixed classification; it must
    include the 'no reusable lesson' option and the review questions."""
    from importlib.util import find_spec

    if find_spec("zuaef_agent") is None:
        sys.path.insert(0, str(REPO / "src"))
    # Load the reviewer module directly from source to avoid a subprocess
    # dependency on the venv wrapper.
    spec = __import__("importlib.util").util.spec_from_file_location(
        "llm_reviewer", REPO / "tools" / "llm_reviewer.py"
    )
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    packet = mod.load_packet(CASE_DIR)
    prompt_text = mod.render_prompt(packet)
    assert "no reusable lesson should be promoted" in prompt_text
    assert "What did the output actually accomplish" in prompt_text
    assert "Which factual claims" in prompt_text
    assert "What should be preserved" in prompt_text
    assert "generalizable lesson" in prompt_text


def test_promotion_script_requires_explicit_human_action(tmp_path):
    """T011: promotion is not automatic. The promotion tool must fail loudly
    unless a human-review file explicitly accepts a lesson."""

    spec = __import__("importlib.util").util.spec_from_file_location(
        "promote_lesson", REPO / "tools" / "promote_lesson.py"
    )
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    # Temp case dir with a manifest but NO human-review.md => must refuse.
    tmp_case = tmp_path / "no-review-case"
    tmp_case.mkdir()
    (tmp_case / "manifest.json").write_text(
        json.dumps(
            {"case_id": "no-review-case", "output": "out.md", "revised": "rev.md"}
        ),
        encoding="utf-8",
    )
    (tmp_case / "out.md").write_text("output", encoding="utf-8")
    (tmp_case / "rev.md").write_text("revised", encoding="utf-8")
    assert not (tmp_case / "human-review.md").exists()
    with pytest.raises(SystemExit):
        mod.promote(tmp_case, dry_run=True)


def test_promotion_script_accepts_explicit_human_review(tmp_path):
    """T011: with an explicit ACCEPT review, promotion produces a candidate;
    the accepted human text survives verbatim (no label compression)."""

    spec = __import__("importlib.util").util.spec_from_file_location(
        "promote_lesson", REPO / "tools" / "promote_lesson.py"
    )
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    tmp_case = tmp_path / "accepted-case"
    tmp_case.mkdir()
    (tmp_case / "manifest.json").write_text(
        json.dumps(
            {"case_id": "accepted-case", "output": "out.md", "revised": "rev.md"}
        ),
        encoding="utf-8",
    )
    (tmp_case / "out.md").write_text("output", encoding="utf-8")
    (tmp_case / "rev.md").write_text("revised text\n第二行", encoding="utf-8")
    (tmp_case / "human-review.md").write_text(
        "Decision: ACCEPT\n\n第一条评审意见。\n", encoding="utf-8"
    )
    target = mod.promote(tmp_case, dry_run=True)
    assert target.name == "accepted-case.json"
    # The underlying files still carry the full human text verbatim.
    assert "第一条评审意见" in (tmp_case / "human-review.md").read_text(
        encoding="utf-8"
    )
    assert "第二行" in (tmp_case / "rev.md").read_text(encoding="utf-8")