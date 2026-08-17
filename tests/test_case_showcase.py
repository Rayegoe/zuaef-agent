"""Validation-case showcase contract tests — zero model calls.

Covers the deterministic parts of ``case_showcase.py``: the case brief
loader (data-driven, no case specifics in code), the expected-signals gate
driven by the brief's rules, and the case workbench (per-file ledger +
binding hash). All case data is built in tmp dirs — no external paths.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from examples.case_showcase import (
    DEFAULT_CASE,
    check_expected_signals,
    load_case_brief,
    project_case_context,
    signal_rules_from_brief,
    task_from_brief,
)
from examples.host_fixture import load_material_case

MINIMAL_BRIEF = {
    "id": "case-test-1",
    "title": "测试案例",
    "audience": "测试读者",
    "assignment": "根据素材写一篇短文。",
    "writing_plan": {
        "angle": "从具体的人和话进入。",
        "questions": ["谁在判断？"],
        "outline": ["进入", "展开", "收束"],
        "target_length": "300-500 Chinese chars",
        "release_constraints": ["只用素材里已有的内容"],
    },
    "signal_gate": {
        "forbidden": ["指纹", "识别AI"],
        "required": ["客户", "同质化"],
        "required_min": 1,
    },
    "run_base": "ctest",
    "showcase_name": "case-test-1",
    "rights": "user-provided",
}


@pytest.fixture
def case_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "case-test-1" / "raw"
    raw.mkdir(parents=True)
    (raw / "a.txt").write_text("素材甲：客户说大概三千个号。\n", encoding="utf-8")
    (raw / "b.txt").write_text("素材乙：编辑提到同质化。\n", encoding="utf-8")
    (tmp_path / "case-test-1" / "case.json").write_text(
        json.dumps(MINIMAL_BRIEF, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path / "case-test-1"


def test_load_case_brief_from_disk(case_dir: Path):
    brief = load_case_brief(case_dir)
    assert brief["id"] == "case-test-1"
    assert brief["writing_plan"]["target_length"] == "300-500 Chinese chars"
    assert signal_rules_from_brief(brief)["forbidden"] == ["指纹", "识别AI"]
    assert task_from_brief(brief) == {
        "id": "case-test-1",
        "title": "测试案例",
        "audience": "测试读者",
        "assignment": "根据素材写一篇短文。",
    }


def test_load_case_brief_missing_file_raises(tmp_path: Path):
    with pytest.raises(SystemExit, match="case brief missing"):
        load_case_brief(tmp_path / "nope")


def test_load_case_brief_validates_required_keys(tmp_path: Path):
    raw = tmp_path / "c" / "raw"
    raw.mkdir(parents=True)
    (raw / "a.txt").write_text("x\n", encoding="utf-8")
    broken = dict(MINIMAL_BRIEF)
    del broken["writing_plan"]
    (tmp_path / "c" / "case.json").write_text(
        json.dumps(broken, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(SystemExit, match="missing required key"):
        load_case_brief(tmp_path / "c")


def test_signal_gate_driven_by_brief_rules(case_dir: Path):
    rules = signal_rules_from_brief(load_case_brief(case_dir))
    clean = "客户说大概三千个号，编辑提到同质化。"
    assert check_expected_signals(clean, rules)["pass"] is True
    blocked = "平台通过指纹识别AI内容。" + clean
    result = check_expected_signals(blocked, rules)
    assert result["pass"] is False
    assert result["forbidden_hits"] == ["指纹", "识别AI"]
    missing = "只有一句话。"
    assert check_expected_signals(missing, rules)["pass"] is False


def test_signal_gate_with_empty_rules_is_lenient():
    result = check_expected_signals("任意文本。", {})
    assert result["pass"] is True  # no rules -> nothing to trip
    assert result["forbidden_hits"] == []


def test_case_bundle_binds_projected_material_hash(case_dir: Path):
    """writing_context.source_sha256 must equal the sha of the EXACT text
    projected into the context (the ledger rows carry per-file hashes)."""
    brief = load_case_brief(case_dir)
    case = load_material_case(case_dir, rights="user-provided")
    bundle = project_case_context(case, brief, techniques=[], memory=[])
    expected = hashlib.sha256(bundle["material"].encode("utf-8")).hexdigest()
    assert bundle["source_sha256"] == expected
    assert bundle["task"]["id"] == "case-test-1"  # brief-driven task
    assert bundle["writing_plan"]["angle"] == "从具体的人和话进入。"
    assert len(bundle["sources"]) == 2
    assert [s["id"] for s in bundle["sources"]] == ["S1", "S2"]
    assert "素材甲" in bundle["material"] and "素材乙" in bundle["material"]


def test_real_case_brief_encodes_expected_signals():
    """The 01-content-team brief (data) carries the editorial constraints."""
    path = DEFAULT_CASE / "case.json"
    if not path.is_file():
        pytest.skip(f"real case brief not present: {path}")
    brief = load_case_brief(DEFAULT_CASE)
    joined = "\n".join(brief["writing_plan"]["release_constraints"])
    assert "客户报数" in joined  # numbers are client-reported
    assert "指纹" in joined and "没有证据" in joined  # no mechanism assertion
    assert "不补写" in joined  # no invented scene details
    assert brief["writing_plan"]["target_length"] == "1200-1800 Chinese chars"
    assert brief["signal_gate"]["required_min"] == 2
