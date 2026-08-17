"""FDE Decision Loop contract tests — zero model calls.

Covers the deterministic parts of ``examples/fde_loop.py``: case fixture
setup (idempotent, files + ACE ingest), mechanical role binding, and the
seed context projection (goal/situation/policy/trajectory/event — no LLM
guessing). The live loop itself is proven by real runs, not by tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-case"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import DEFAULT_ACE_ROOT
from zuaef_case.models import CaseDoc
from zuaef_case.store import CaseStore

import examples.fde_loop as loop

ACE = Path(str(DEFAULT_ACE_ROOT))
ACE_AVAILABLE = (ACE / "tools" / "ctx.py").is_file()


@pytest.fixture
def cases_root(tmp_path: Path) -> Path:
    return tmp_path / "cases"


def test_setup_creates_case_fixture_once(cases_root: Path):
    store = CaseStore(cases_root)
    ids = loop.setup_case(cases_root, store, "stillevo-beauty")
    case_dir = store.case_dir("stillevo-beauty")
    for name in ("case.md", "policy.md", "situation.json", "material-ids.json"):
        assert (case_dir / name).is_file(), name
    assert sorted(p.name for p in (case_dir / "materials").iterdir()) == [
        "chat-history.md",
        "client-background.md",
        "product-notes.md",
    ]
    assert set(ids) == {"chat-history.md", "client-background.md", "product-notes.md"}
    # idempotent: re-running setup does not duplicate or crash
    ids2 = loop.setup_case(cases_root, store, "stillevo-beauty")
    assert ids == ids2
    doc = store.load_case("stillevo-beauty")
    assert isinstance(doc, CaseDoc)
    assert doc.stakeholders["customer"] == "wechat-li"


def test_mechanical_role_binding(cases_root: Path):
    store = CaseStore(cases_root)
    loop.setup_case(cases_root, store, "stillevo-beauty")
    assert loop.bind_event_role(store, "stillevo-beauty", "customer") == "customer"
    assert loop.bind_event_role(store, "stillevo-beauty", "barry") == "barry"
    with pytest.raises(SystemExit):
        loop.bind_event_role(store, "stillevo-beauty", "hacker")


def test_seed_context_projects_goal_situation_policy_event(cases_root: Path):
    store = CaseStore(cases_root)
    loop.setup_case(cases_root, store, "stillevo-beauty")
    seed = loop.seed_case_context(
        store, "stillevo-beauty", {"role": "customer", "text": "demo 什么时候能看？"}
    )
    assert "### goal" in seed and "云朵美妆" in seed
    assert "### policy" in seed and "send_to_customer" in seed
    assert "### situation" in seed and "方案讨论" in seed
    assert "### inbound event" in seed
    assert "role=customer: demo 什么时候能看？" in seed
    assert "### trajectory (tail)" in seed


def test_event_entries_are_host_appended_before_run(cases_root: Path):
    """The inbound event enters the trajectory as role=customer BEFORE the
    agent runs — the agent may not write its own inputs."""
    store = CaseStore(cases_root)
    loop.setup_case(cases_root, store, "stillevo-beauty")
    store.append_trajectory_for_case(
        "stillevo-beauty",
        loop.TrajectoryEntry(kind="event", role="customer", summary="第一条", refs={}),
    )
    seed = loop.seed_case_context(
        store, "stillevo-beauty", {"role": "customer", "text": "第二条"}
    )
    # the host-appended entry is in the trajectory tail; the run event is
    # projected ONLY in the inbound-event section (run_case_event appends it
    # to the trajectory itself, never via seed projection)
    assert "第一条" in seed
    before_event, after_event = seed.split("### inbound event", 1)
    assert "第二条" not in before_event
    assert "role=customer: 第二条" in after_event


def test_material_map_refs_are_case_relative(cases_root: Path):
    """source_refs are case-relative, never absolute host paths."""
    store = CaseStore(cases_root)
    ids = loop.setup_case(cases_root, store, "stillevo-beauty")
    for meta in ids.values():
        assert meta["source_ref"].startswith("cases/stillevo-beauty/materials/")
        assert not Path(meta["source_ref"]).is_absolute()


@pytest.mark.skipif(not ACE_AVAILABLE, reason=f"ACE repo not found at {ACE}")
def test_setup_ingests_materials_with_real_m_ids(cases_root: Path):
    """Setup binds each material to a REAL ACE M id via the workspace index."""
    store = CaseStore(cases_root)
    ids = loop.setup_case(cases_root, store, "stillevo-beauty")
    assert {v["material_id"] for v in ids.values()} == {"M001", "M002", "M003"}
    index = ACE / "workspaces" / loop.FDE_ARTICLE / "materials.jsonl"
    rows = [
        json.loads(line)
        for line in index.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 3
