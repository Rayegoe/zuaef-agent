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


def test_old_receipt_without_usage_limits_still_loads(tmp_path: Path):
    """T003: ``usage_limits`` is additive/optional — pre-M2 receipts stay
    readable without any migration, and an absent fact stays an empty dict."""
    import json

    store = ReceiptStore(tmp_path / ".zuaef-state")
    path = store.path_for("old-run")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "run_id": "old-run",
        "model": "test",
        "outcome": "done",
        "execution_state": "completed",
        "started_at": "2026-09-01T00:00:00Z",
        "finished_at": "2026-09-01T00:01:00Z",
    }), encoding="utf-8")
    receipt = store.read("old-run")
    assert receipt.execution_state == "completed"
    assert receipt.usage_limits == {}
