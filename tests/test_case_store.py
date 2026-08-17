"""CaseStore tests — SPEC v0.4 Stage 1 gate: case file layer, schema
validation, provenance enforcement, append-only trajectory, drafts, and the
core-protected control-plane paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from zuaef_case.models import (
    CaseDoc,
    CaseError,
    Situation,
    TrajectoryEntry,
    validate_case_id,
)
from zuaef_case.store import CaseStore

from zuaef_agent.core import FILESYSTEM_PROTECTED_PATTERNS


@pytest.fixture
def store(tmp_path: Path) -> CaseStore:
    return CaseStore(tmp_path / "workspace" / "cases")


def _doc(**overrides) -> CaseDoc:
    base = {
        "case_id": "beauty-003",
        "goal": "证明我们能够改善客户公众号 AI 内容同质化问题，并推动至付费 Pilot。",
        "status": "active",
        "stakeholders": {"supervisor": "barry"},
        "supervisor_chat_id": "111",
        "customer_chat_id": "222",
    }
    base.update(overrides)
    return CaseDoc(**base)


# ── BusinessCase ────────────────────────────────────────────────────────────


def test_case_roundtrip_with_notes(store: CaseStore):
    doc = _doc(notes="第一阶段：现场 demo。")
    store.create_case(doc)
    loaded = store.load_case("beauty-003")
    assert loaded == doc
    assert loaded.goal == doc.goal
    text = (store.case_dir("beauty-003") / "case.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "第一阶段：现场 demo。" in text


def test_case_doc_requires_goal():
    with pytest.raises(ValueError):
        CaseDoc(case_id="x", goal="")


def test_create_twice_fails(store: CaseStore):
    store.create_case(_doc())
    with pytest.raises(CaseError, match="already exists"):
        store.create_case(_doc())


def test_load_missing_case_fails(store: CaseStore):
    with pytest.raises(CaseError, match="not found"):
        store.load_case("ghost-case")


def test_case_id_rejects_traversal(store: CaseStore):
    with pytest.raises(CaseError):
        store.create_case(_doc(case_id="../../etc"))
    with pytest.raises(CaseError):
        validate_case_id("a/b")


def test_case_doc_id_must_match_directory(store: CaseStore):
    store.create_case(_doc())
    target = store.case_dir("beauty-003") / "case.md"
    target.write_text(
        target.read_text(encoding="utf-8").replace("beauty-003", "other-1"),
        encoding="utf-8",
    )
    with pytest.raises(CaseError, match="declares"):
        store.load_case("beauty-003")


# ── Situation provenance ────────────────────────────────────────────────────


def test_situation_substantive_facts_require_provenance(store: CaseStore):
    store.create_case(_doc())
    situation = Situation(
        case_id="beauty-003",
        updated_by="run:r1",
        state={"customer": {"confidence": "medium"}},
    )
    with pytest.raises(CaseError, match="provenance"):
        store.write_situation(situation)


def test_situation_with_evidence_ids_writes(store: CaseStore):
    store.create_case(_doc())
    situation = Situation(
        case_id="beauty-003",
        updated_by="run:r1",
        state={"problem": {"template_similarity": "confirmed"}},
        evidence_ids=["EVD-G-1"],
    )
    stored = store.write_situation(situation)
    assert store.read_situation("beauty-003") == stored


def test_situation_with_barry_override_writes(store: CaseStore):
    store.create_case(_doc())
    situation = Situation(
        case_id="beauty-003",
        updated_by="barry",
        state={"commercial": {"stage": "solution_validation"}},
        barry_override="先验证价值再资格审定",
    )
    store.write_situation(situation)
    assert store.read_situation("beauty-003").barry_override == "先验证价值再资格审定"


def test_situation_unknown_only_needs_no_provenance(store: CaseStore):
    store.create_case(_doc())
    situation = Situation(
        case_id="beauty-003",
        updated_by="run:r1",
        state={"customer": {"authority": "unknown", "budget": "unknown"}},
    )
    store.write_situation(situation)
    assert store.read_situation("beauty-003").state["customer"]["authority"] == "unknown"


def test_situation_requires_writer_identity(store: CaseStore):
    store.create_case(_doc())
    situation = Situation(case_id="beauty-003", updated_by="")
    with pytest.raises(CaseError, match="updated_by"):
        store.write_situation(situation)


def test_missing_situation_reads_default(store: CaseStore):
    store.create_case(_doc())
    situation = store.read_situation("beauty-003")
    assert situation.case_id == "beauty-003"
    assert situation.state == {}


# ── Trajectory append-only ──────────────────────────────────────────────────


def _entry(kind="event", role="customer", run_id="", summary="hi", **kw):
    return TrajectoryEntry(kind=kind, role=role, run_id=run_id, summary=summary, **kw)


def test_trajectory_sequences_and_reads_tail(store: CaseStore):
    store.create_case(_doc())
    first = store.append_trajectory_for_case("beauty-003", _entry(summary="第一条"))
    second = store.append_trajectory_for_case("beauty-003", _entry(summary="第二条"))
    third = store.append_trajectory_for_case("beauty-003", _entry(summary="第三条"))
    assert (first.seq, second.seq, third.seq) == (1, 2, 3)

    tail = store.read_trajectory("beauty-003", tail=2)
    assert [entry.seq for entry in tail] == [2, 3]
    assert [entry.summary for entry in tail] == ["第二条", "第三条"]


def test_decision_entry_requires_run_id(store: CaseStore):
    store.create_case(_doc())
    with pytest.raises(CaseError, match="run_id"):
        store.append_trajectory_for_case(
            "beauty-003", _entry(kind="decision", role="agent")
        )
    ok = store.append_trajectory_for_case(
        "beauty-003", _entry(kind="decision", role="agent", run_id="r1")
    )
    assert ok.seq == 1


def test_trajectory_has_no_mutation_api(store: CaseStore):
    """The store exposes append + read only — no update/delete methods."""
    store.create_case(_doc())
    public = [
        name for name in dir(CaseStore)
        if not name.startswith("_") and callable(getattr(CaseStore, name, None))
    ]
    assert not any(("update" in name or "delete" in name or "remove" in name) for name in public)


# ── Drafts ──────────────────────────────────────────────────────────────────


def test_drafts_are_numbered_and_readable(store: CaseStore):
    store.create_case(_doc())
    one = store.write_draft("beauty-003", "您好，这是第一版。", meta="seq=1")
    two = store.write_draft("beauty-003", "第二版草稿。")
    assert one.name == "msg-001.md"
    assert two.name == "msg-002.md"
    assert store.list_drafts("beauty-003") == [one, two]
    assert "第一版" in one.read_text(encoding="utf-8")


# ── Control-plane file protection (core) ────────────────────────────────────


def test_case_control_files_are_core_protected():
    assert "cases/*/case.md" in FILESYSTEM_PROTECTED_PATTERNS
    assert "cases/*/policy-overrides.md" in FILESYSTEM_PROTECTED_PATTERNS


def test_private_claims_rejected_only_for_substantive_values(store: CaseStore):
    """Bool flags are structural, not claims — they never demand provenance."""
    store.create_case(_doc())
    situation = Situation(
        case_id="beauty-003",
        updated_by="run:r1",
        state={"commercial": {"paid": False, "repeat_consulting": False}},
    )
    store.write_situation(situation)
