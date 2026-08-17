"""Validation-case showcase contract tests — zero model calls.

Covers the deterministic parts of ``case_showcase.py``: the expected-signals
gate (forbidden assertions / required soft signals) and the case workbench
(host-authored plan + per-file ledger + binding hash).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from examples.case_showcase import (
    TASK,
    WRITING_PLAN,
    check_expected_signals,
    project_case_context,
)
from examples.host_fixture import load_material_case

CLEAN = (
    "客户说他们大概三千个号。编辑反复提到“同质化”，但说不出标准，"
    "只说“大概看起来像真人吧”。"
)


def test_signal_gate_passes_clean_text():
    result = check_expected_signals(CLEAN)
    assert result["pass"] is True
    assert result["forbidden_hits"] == []
    assert "客户" in result["required_present"]
    assert "同质化" in result["required_present"]


def test_signal_gate_blocks_forbidden_assertions():
    for phrase in ("指纹", "识别AI", "AI识别", "算法识别", "算法检测"):
        result = check_expected_signals(f"{CLEAN} 平台通过{phrase}检测内容。")
        assert result["pass"] is False, phrase
        assert phrase in result["forbidden_hits"]


def test_signal_gate_requires_soft_signals():
    result = check_expected_signals("平台提示内容质量需提升。编辑说结构都差不多。")
    assert result["pass"] is False  # 客户/同质化/像真人 all missing
    assert len(result["required_missing"]) >= 2


def test_writing_plan_encodes_expected_signals():
    """The editorial brief becomes host-authored release constraints."""
    constraints = WRITING_PLAN["release_constraints"]
    joined = "\n".join(constraints)
    assert "客户报数" in joined  # numbers are client-reported
    assert "指纹" in joined and "没有证据" in joined  # no mechanism assertion
    assert "不补写" in joined  # no invented scene details
    assert WRITING_PLAN["target_length"] == "1200-1800 Chinese chars"
    assert TASK["id"] == "case-01-content-team"


def test_case_bundle_binds_projected_material_hash(tmp_path: Path):
    """writing_context.source_sha256 must equal the sha of the EXACT text
    projected into the context (the ledger rows carry per-file hashes)."""
    raw = tmp_path / "case-x" / "raw"
    raw.mkdir(parents=True)
    (raw / "a.txt").write_text("素材甲\n", encoding="utf-8")
    (raw / "b.txt").write_text("素材乙\n", encoding="utf-8")
    case = load_material_case(tmp_path / "case-x", rights="user-provided")
    bundle = project_case_context(case, techniques=[], memory=[])
    expected = hashlib.sha256(bundle["material"].encode("utf-8")).hexdigest()
    assert bundle["source_sha256"] == expected
    assert len(bundle["sources"]) == 2
    assert [s["id"] for s in bundle["sources"]] == ["S1", "S2"]
    # every projected file text appears verbatim inside the material block
    assert "素材甲" in bundle["material"] and "素材乙" in bundle["material"]
