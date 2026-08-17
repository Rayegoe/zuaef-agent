"""Store tests over the synthetic fixture (SPEC v0.1 §56 Phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from zuaef_client_service.models import InteractionReceipt
from zuaef_client_service.store import ClientServiceStore, CorpusError

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_client_service"


@pytest.fixture()
def store(tmp_path: Path) -> ClientServiceStore:
    # copy fixture into an isolated tmp root so writes never touch the
    # checked-in fixture
    import shutil

    root = tmp_path / "slice"
    shutil.copytree(FIXTURE, root)
    return ClientServiceStore(root)


class TestCorpusReads:
    def test_evidence_ledger_loaded(self, store: ClientServiceStore) -> None:
        records = store.evidence_records()
        assert len(records) == 3
        assert records[0]["evidence_id"] == "EVD-SYN-001"

    def test_knowledge_loaded(self, store: ClientServiceStore) -> None:
        items = store.knowledge_items()
        assert len(items) == 1
        assert items[0].knowledge_id == "KNO-SYN-001"

    def test_semantics_loaded(self, store: ClientServiceStore) -> None:
        items = store.semantic_preferences()
        assert len(items) == 1
        assert items[0].preference_id == "SEM-SYN-001"

    def test_evidence_by_ids(self, store: ClientServiceStore) -> None:
        refs = store.evidence_by_ids(["EVD-SYN-001", "EVD-NOPE"])
        assert [r.evidence_id for r in refs] == ["EVD-SYN-001"]

    def test_search_evidence_lexical(self, store: ClientServiceStore) -> None:
        refs = store.search_evidence("你们做过类似项目吗", limit=8)
        assert any(r.evidence_id == "EVD-SYN-001" for r in refs)

    def test_missing_slice_root_raises(self, tmp_path: Path) -> None:
        with pytest.raises(CorpusError):
            ClientServiceStore(tmp_path / "nope")

    def test_corrupt_jsonl_raises(self, tmp_path: Path) -> None:
        import shutil

        root = tmp_path / "slice"
        shutil.copytree(FIXTURE, root)
        (root / "evidence" / "evidence_ledger.jsonl").write_text(
            "not json\n", encoding="utf-8"
        )
        with pytest.raises(CorpusError, match="corrupt"):
            ClientServiceStore(root).evidence_records()


class TestCustomerState:
    def test_default_state_when_missing(self, store: ClientServiceStore) -> None:
        state = store.load_customer_state("CASE-NEW-001")
        assert state.customer_id == "CASE-NEW-001"
        assert state.authority == "unknown"
        assert state.budget == "unknown"

    def test_load_existing(self, store: ClientServiceStore) -> None:
        state = store.load_customer_state("CASE-SYN-001")
        assert state.stage == "qualification"

    def test_write_keeps_history(self, store: ClientServiceStore) -> None:
        state = store.load_customer_state("CASE-SYN-001")
        state.next_best_action = "updated"
        store.write_customer_state(state)
        state2 = store.load_customer_state("CASE-SYN-001")
        assert state2.next_best_action == "updated"
        history = list(
            (store.slice_root / "state/customers/CASE-SYN-001.history").glob("*.yaml")
        )
        assert len(history) == 1  # the pre-update snapshot


class TestInteractionReceipts:
    def test_append_writes_file(self, store: ClientServiceStore) -> None:
        receipt = InteractionReceipt(
            interaction_id="INT-SYN-001",
            customer_id="CASE-SYN-001",
            incoming_message="hello",
            matched_policies=["POL-C-006"],
            strategy="QUALIFY_BEFORE_DISCLOSE",
            run_id="run-1",
        )
        result = store.append_interaction(receipt)
        assert result["written"] is True
        assert result["sha256"]
        path = store.slice_root / "state" / "interactions" / "INT-SYN-001.json"
        assert path.is_file()

    def test_write_boundary_state_only(self, store: ClientServiceStore) -> None:
        """§54: runtime may write state/ but never doctrine files."""
        from zuaef_client_service.store import _CUSTOMERS_ROOT, _INTERACTIONS_ROOT

        assert _CUSTOMERS_ROOT.startswith("state/")
        assert _INTERACTIONS_ROOT.startswith("state/")
