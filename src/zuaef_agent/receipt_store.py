from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from .models import AnyReceipt, PauseReceipt, RunReceipt


class ReceiptStore:
    """Atomic JSON receipts under the runtime-state root, outside model-writable workspace."""

    def __init__(self, state_root: Path):
        self.state_root = state_root
        self.root = self.state_root / "receipts"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for ch in run_id):
            raise ValueError(f"invalid run_id: {run_id!r}")
        return self.root / f"{run_id}.json"

    def display_path_for(self, run_id: str) -> str:
        return str(self.path_for(run_id))

    def write(self, receipt: RunReceipt | PauseReceipt) -> str:
        target = self.path_for(receipt.run_id)
        if target.exists():
            raise FileExistsError(f"receipt already exists for run_id {receipt.run_id!r}")
        tmp = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        return str(target)

    def read(self, run_id: str) -> AnyReceipt:
        data = json.loads(self.path_for(run_id).read_text(encoding="utf-8"))
        if data.get("state") == "paused":
            return PauseReceipt.model_validate(data)
        return RunReceipt.model_validate(data)
