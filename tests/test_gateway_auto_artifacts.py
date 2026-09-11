"""P6 Feishu automatic artifact delivery gates (spec pack 08 / 10 H3–H6).

The gateway is transport only: auto-delivery sends the settled completed
run's receipt-listed artifacts through the same generic send loop as the
manual ``/artifacts`` recovery command, under the same containment and
size rules. A send failure never rewrites the settled execution truth.

These tests drive GatewayService directly with a fake surface adapter —
no model, no real surface.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from zuaef_agent.gateway.service import GatewayService
from zuaef_agent.gateway.store import GatewayStore
from zuaef_agent.models import ArtifactFact, RunReceipt
from zuaef_agent.receipt_store import ReceiptStore


class FakeSurface:
    surface_name = "feishu"

    def __init__(self, fail_documents: bool = False):
        self.texts: list[tuple[str, str]] = []
        self.documents: list[tuple[str, Path, str | None]] = []
        self.fail_documents = fail_documents

    def poll_once(self, *, timeout_seconds):
        return []

    def pending_cursor(self):
        return None

    def send_text(self, channel_id: str, text: str) -> None:
        self.texts.append((channel_id, text))

    def send_document(self, channel_id: str, path: Path, *, caption=None) -> None:
        if self.fail_documents:
            raise RuntimeError("feishu upload unavailable (test)")
        self.documents.append((channel_id, path, caption))

    def send_approval(self, *args, **kwargs):  # pragma: no cover - unused here
        raise AssertionError("approval path not exercised")

    def send_keyboard(self, *args, **kwargs):  # pragma: no cover - unused here
        raise AssertionError("keyboard path not exercised")

    def answer_callback(self, *args, **kwargs):  # pragma: no cover - unused
        raise AssertionError("callback path not exercised")

    def probe(self):  # pragma: no cover - unused here
        return {}

    def set_offset(self, value):  # pragma: no cover - unused here
        pass

    def close(self):  # pragma: no cover - unused here
        pass

    def last_text(self) -> str:
        return self.texts[-1][1] if self.texts else ""


def _service(tmp_path: Path, surface: FakeSurface, *, auto: bool) -> GatewayService:
    workspace = tmp_path / "workspace"
    (workspace / "artifacts").mkdir(parents=True)
    return GatewayService(
        settings=type(
            "Settings",
            (),
            {
                "workspace_root": workspace,
                "state_root": tmp_path / "state",
                "delivery_root": None,
            },
        )(),
        store=GatewayStore(tmp_path / "gateway.sqlite3"),
        surface=surface,
        max_artifact_bytes=1024,
        auto_artifacts=auto,
    )


def _completed_receipt(run_id: str, artifacts: list[ArtifactFact]) -> RunReceipt:
    now = datetime.now(UTC)
    return RunReceipt(
        run_id=run_id,
        model="test",
        started_at=now,
        finished_at=now,
        execution_state="completed",
        outcome="done",
        artifact_facts=artifacts,
    )


def _session(channel: str = "oc_demo"):
    return type(
        "Session",
        (),
        {"channel_id": channel, "model_copy": lambda self, update: self},
    )()


def test_auto_delivery_sends_completed_artifact_without_second_command(
    tmp_path: Path,
):
    """H3: enabled + completed + eligible artifact → exactly one send."""
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=True)
    receipt = _completed_receipt(
        "run-auto-1",
        [
            ArtifactFact(
                path="artifacts/pdf/客户方案.pdf",
                size=10,
                sha256="a" * 64,
                change="created",
            )
        ],
    )
    (service.settings.workspace_root / "artifacts" / "pdf").mkdir(parents=True)
    (service.settings.workspace_root / "artifacts" / "pdf" / "客户方案.pdf").write_bytes(
        b"pdf-bytes"
    )

    service._auto_deliver_artifacts(_session(), receipt)

    assert len(surface.documents) == 1
    channel, path, caption = surface.documents[0]
    assert channel == "oc_demo"
    assert path.name == "客户方案.pdf"
    assert caption == "artifacts/pdf/客户方案.pdf"


def test_auto_delivery_disabled_by_default(tmp_path: Path):
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=False)
    receipt = _completed_receipt("run-auto-2", [])
    receipt = receipt.model_copy(
        update={
            "artifact_facts": [
                ArtifactFact(
                    path="artifacts/a.md", size=1, sha256="b" * 64, change="created"
                )
            ]
        }
    )
    (service.settings.workspace_root / "artifacts" / "a.md").write_text("x", encoding="utf-8")

    service._auto_deliver_artifacts(_session(), receipt)
    assert surface.documents == []


def test_auto_delivery_skips_failed_runs(tmp_path: Path):
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=True)
    receipt = _completed_receipt("run-auto-3", []).model_copy(
        update={"execution_state": "failed"}
    )
    receipt = receipt.model_copy(
        update={
            "artifact_facts": [
                ArtifactFact(
                    path="artifacts/a.md", size=1, sha256="c" * 64, change="created"
                )
            ]
        }
    )
    (service.settings.workspace_root / "artifacts" / "a.md").write_text("x", encoding="utf-8")

    service._auto_deliver_artifacts(_session(), receipt)
    assert surface.documents == []


def test_auto_delivery_oversize_artifact_is_not_uploaded(tmp_path: Path):
    """H6: artifact above the configured surface limit is never uploaded."""
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=True)  # limit is 1024 bytes
    big = b"x" * 4096
    (service.settings.workspace_root / "artifacts" / "big.docx").write_bytes(big)
    receipt = _completed_receipt(
        "run-auto-4",
        [
            ArtifactFact(
                path="artifacts/big.docx",
                size=len(big),
                sha256="d" * 64,
                change="created",
            )
        ],
    )

    service._auto_deliver_artifacts(_session(), receipt)
    assert surface.documents == []
    assert "artifacts/big.docx" in surface.last_text()


def test_auto_delivery_never_sends_outside_or_missing_files(tmp_path: Path):
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=True)
    receipt = _completed_receipt(
        "run-auto-5",
        [
            ArtifactFact(
                path="../../etc/passwd", size=1, sha256="e" * 64, change="created"
            ),
            ArtifactFact(
                path="artifacts/ghost.docx", size=5, sha256="f" * 64, change="created"
            ),
        ],
    )

    service._auto_deliver_artifacts(_session(), receipt)
    assert surface.documents == []
    noticed = [text for _, text in surface.texts]
    assert any("../../etc/passwd" in text for text in noticed)
    assert any("artifacts/ghost.docx" in text for text in noticed)


def test_auto_delivery_failure_does_not_rewrite_execution_truth(tmp_path: Path):
    """H5: an upload failure is a logged transport problem plus a short
    notice — the settled receipt stays exactly as it was."""
    surface = FakeSurface(fail_documents=True)
    settings_state = tmp_path / "state"
    settings_state.mkdir(parents=True)
    service = _service(tmp_path, surface, auto=True)
    # Replace the ad-hoc state dir with a real ReceiptStore-backed one.
    service.receipts = ReceiptStore(settings_state)
    receipt = _completed_receipt(
        "run-auto-6",
        [
            ArtifactFact(
                path="artifacts/ok.docx", size=2, sha256="9" * 64, change="created"
            )
        ],
    )
    service.receipts.write(receipt)
    (service.settings.workspace_root / "artifacts" / "ok.docx").write_bytes(b"ok")

    service._auto_deliver_artifacts(_session(), receipt)

    assert surface.documents == []
    assert "delivery failed" in surface.last_text().lower()
    reread = service.receipts.read("run-auto-6")
    assert reread.execution_state == "completed"
    assert len(reread.artifact_facts) == 1


def test_manual_artifacts_command_remains_recovery_path(tmp_path: Path):
    """H4/H2: the manual command still sends with auto-delivery disabled."""
    surface = FakeSurface()
    service = _service(tmp_path, surface, auto=False)
    (service.settings.workspace_root / "artifacts" / "final.pdf").write_bytes(b"pdf")
    receipt = _completed_receipt(
        "run-auto-7",
        [
            ArtifactFact(
                path="artifacts/final.pdf", size=3, sha256="7" * 64, change="created"
            )
        ],
    )

    session = _session()
    service._send_receipt_artifacts(session, receipt)

    assert len(surface.documents) == 1
    assert surface.documents[0][1].name == "final.pdf"
