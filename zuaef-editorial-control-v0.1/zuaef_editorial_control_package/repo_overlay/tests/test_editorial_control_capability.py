from __future__ import annotations

from pathlib import Path

from zuaef_ace_writing.editorial_control import detect_trajectory
from zuaef_ace_writing.editorial_evidence import (
    EditorialEvidence,
    EditorialEvidenceStore,
    append_approved_evidence,
)


def test_detects_template_and_summary_pressure() -> None:
    text = "\n\n".join(
        [
            "首先，这是一段关于行业趋势和价值升级的解释。" * 8,
            "其次，这意味着企业需要重新理解增长逻辑。" * 8,
            "再次，这说明新的模式正在形成。" * 8,
            "最后，总的来说，这意味着整个生态都需要完成转型。" * 8,
            "综上，这说明方法论本身也需要升级。" * 8,
        ]
    )
    names = {signal.name for signal in detect_trajectory(text)}
    assert "template_connectors" in names
    assert "summary_pressure" in names


def test_short_text_is_not_overcontrolled() -> None:
    assert detect_trajectory("一个很短的段落。") == ()


def test_evidence_selection_requires_signal_match() -> None:
    store = EditorialEvidenceStore.load(None)
    selected = store.select(
        signals={"summary_pressure"},
        situation_tags={"drafting", "nonfiction"},
        run_id="r1",
        run_step=2,
        limit=3,
    )
    assert selected
    assert all("summary_pressure" in item.trigger_signals for item in selected)


def test_human_evidence_overrides_builtin_by_id(tmp_path: Path) -> None:
    path = tmp_path / "evidence.jsonl"
    append_approved_evidence(
        path,
        EditorialEvidence(
            id="builtin.delay-thesis",
            source_type="human_patch",
            source_ref="patch:42",
            situation_tags=["drafting"],
            trigger_signals=["summary_pressure"],
            action="delay_interpretation",
            directive="Use the approved human version of this decision.",
            rationale="The human editor chose to delay the explanation.",
            weight=9.0,
            approved_by="barry",
        ),
    )
    store = EditorialEvidenceStore.load(path)
    record = next(item for item in store.evidence if item.id == "builtin.delay-thesis")
    assert record.source_type == "human_patch"
    assert record.approved_by == "barry"
