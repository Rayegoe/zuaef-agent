from datetime import UTC, datetime
from pathlib import Path

import pytest

from zuaef_agent.models import RunReceipt
from zuaef_agent.receipt_store import ReceiptStore


def test_receipt_roundtrip(tmp_path: Path):
    now = datetime.now(UTC)
    store = ReceiptStore(tmp_path / ".zuaef-state")
    receipt = RunReceipt(
        run_id="run-1",
        model="test:model",
        started_at=now,
        finished_at=now,
        execution_state="completed",
        outcome="done",
        knowledge_updates=["knowledge/concepts/x.md"],
        step_store=".state/steps",
        tool_result_store=".state/tool-results",
    )
    rel = store.write(receipt)
    assert rel.endswith(".zuaef-state/receipts/run-1.json")
    loaded = store.read("run-1")
    assert loaded.run_id == "run-1"
    assert loaded.knowledge_updates == ["knowledge/concepts/x.md"]
    with pytest.raises(FileExistsError):
        store.write(receipt)


def test_receipt_rejects_unsafe_run_id(tmp_path: Path):
    store = ReceiptStore(tmp_path / ".zuaef-state")
    with pytest.raises(ValueError):
        store.path_for("../escape")
