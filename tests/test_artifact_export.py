"""Generic caller-side durable delivery exporter tests.

Candidate C acceptance: after ``execute_run`` returns a completed
``TerminalRun``, the host copies exactly the receipt-listed artifacts
(``artifact_facts``) to a caller-owned durable root — with zero CI/profile
branching. Includes the decisive proof: run the shared execution path, export,
delete the runtime workspace, verify the durable bytes remain.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_competitive_intelligence import build_plugin

from zuaef_agent import cli
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import ArtifactFact, CoreDeps, ExecutionState, RunReceipt
from zuaef_agent.plugin_api import PluginEnv
from zuaef_agent.runtime import (
    DeliveryExportError,
    RuntimeOutcome,
    TerminalRun,
    execute_run,
    export_receipt_artifacts,
)

models.ALLOW_MODEL_REQUESTS = False


def _terminal(
    workspace: Path,
    *rel_paths: str,
    execution_state: ExecutionState = "completed",
    run_id: str | None = None,
) -> TerminalRun:
    facts: list[ArtifactFact] = []
    for rel in rel_paths:
        target = workspace / rel
        # Some receipts declare invalid/absent paths (escape/symlink/failure
        # tests); the exporter re-validates them, so the fact's size is only a
        # placeholder here.
        data = target.read_bytes() if target.is_file() else b""
        facts.append(
            ArtifactFact(path=rel, size=len(data), sha256="0" * 64, change="created")
        )
    receipt = RunReceipt(
        run_id=run_id or uuid4().hex,
        model="test",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execution_state=execution_state,
        outcome="done",
        artifact_facts=facts,
    )
    return TerminalRun(presentation="done", receipt=receipt)


def _run_args(workspace: Path, delivery_root: Path | None) -> argparse.Namespace:
    return argparse.Namespace(
        task="task",
        profile=None,
        delivery_root=delivery_root,
        model=None,
        workspace=workspace,
        request_limit=None,
        tool_calls_limit=None,
        total_tokens_limit=None,
    )


# ── 1. copies only receipt-listed artifacts ────────────────────────────────


def test_exporter_copies_only_receipt_listed_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    delivery = tmp_path / "delivery"
    (workspace / "artifacts" / "nested").mkdir(parents=True)
    listed_top = workspace / "artifacts" / "report.md"
    listed_top.write_text("# report\n", encoding="utf-8")
    listed_nested = workspace / "artifacts" / "nested" / "data.csv"
    listed_nested.write_text("a,b\n", encoding="utf-8")
    (workspace / "artifacts" / "stray.txt").write_text("stray", encoding="utf-8")

    outcome = _terminal(workspace, "artifacts/report.md", "artifacts/nested/data.csv")
    result = export_receipt_artifacts(outcome, workspace, delivery)

    assert result["status"] == "delivered"
    assert result["files"] == ["artifacts/nested/data.csv", "artifacts/report.md"]
    assert result["promoted"] == 2
    assert (
        delivery / "artifacts" / "report.md"
    ).read_bytes() == listed_top.read_bytes()
    assert (
        delivery / "artifacts" / "nested" / "data.csv"
    ).read_bytes() == listed_nested.read_bytes()
    # only receipt-listed files were transported
    assert not (delivery / "artifacts" / "stray.txt").exists()


# ── 2. path validation rejects escapes and symlinks ────────────────────────


def test_exporter_rejects_escapes_and_symlinks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    delivery = tmp_path / "delivery"
    (workspace / "artifacts").mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    leaker = workspace / "artifacts" / "link.txt"
    leaker.symlink_to(outside)
    (workspace / "artifacts" / "ok.txt").write_text("ok", encoding="utf-8")

    # Escape path (..) — normalize_artifact_path rejects it.
    escape_outcome = _terminal(workspace, "artifacts/../outside.txt")
    with pytest.raises(DeliveryExportError) as escape_error:
        export_receipt_artifacts(escape_outcome, workspace, delivery)
    assert "artifact path not workspace-relative" in str(escape_error.value)

    # Absolute path — rejected by the same containment logic.
    absolute_outcome = _terminal(
        workspace, str((workspace / "artifacts" / "ok.txt").resolve())
    )
    with pytest.raises(DeliveryExportError) as absolute_error:
        export_receipt_artifacts(absolute_outcome, workspace, delivery)
    assert "artifact path not workspace-relative" in str(absolute_error.value)

    # Symlink — never followed. The existing containment logic resolves the
    # link and rejects the escape outright (or the regular-file guard does);
    # the target outside the tree is never copied.
    symlink_outcome = _terminal(workspace, "artifacts/link.txt")
    with pytest.raises(DeliveryExportError) as symlink_error:
        export_receipt_artifacts(symlink_outcome, workspace, delivery)
    assert "artifacts/link.txt" in str(symlink_error.value)
    assert outside.read_text(encoding="utf-8") == "secret"
    assert not (delivery / "artifacts" / "link.txt").exists()


# ── 3. no delivery root configured: clean no-op ────────────────────────────


def test_no_delivery_root_is_a_clean_noop(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "artifacts").mkdir(parents=True)
    (workspace / "artifacts" / "report.md").write_text("x", encoding="utf-8")
    outcome = _terminal(workspace, "artifacts/report.md")

    assert export_receipt_artifacts(outcome, workspace, None) == {
        "status": "disabled",
        "reason": "no delivery root configured",
    }
    assert export_receipt_artifacts(outcome, workspace, "") == {
        "status": "disabled",
        "reason": "no delivery root configured",
    }
    # nothing was written anywhere
    assert not (tmp_path / "delivery").exists()

    # non-terminal / non-completed outcomes are skipped, never exported
    failure_outcome = _terminal(
        workspace, "artifacts/report.md", execution_state="failed"
    )
    assert (
        export_receipt_artifacts(failure_outcome, workspace, tmp_path / "delivery")[
            "status"
        ]
        == "skipped"
    )
    assert (
        export_receipt_artifacts(
            cast(RuntimeOutcome, object()), workspace, tmp_path / "delivery"
        )["status"]
        == "skipped"
    )


# ── 7. no CI assumptions ───────────────────────────────────────────────────


def test_exporter_has_no_ci_assumptions(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    delivery = tmp_path / "delivery"
    (workspace / "artifacts" / "writing").mkdir(parents=True)
    target = workspace / "artifacts" / "writing" / "article.md"
    target.write_text("# article\n", encoding="utf-8")

    outcome = _terminal(workspace, "artifacts/writing/article.md")
    result = export_receipt_artifacts(outcome, workspace, delivery)

    assert result["status"] == "delivered"
    assert result["files"] == ["artifacts/writing/article.md"]
    assert (delivery / "artifacts" / "writing" / "article.md").read_text(
        encoding="utf-8"
    ) == "# article\n"


# ── 8. delivery failure: truth untouched, failure surfaced separately ───────


def test_delivery_failure_leaves_receipt_untouched_and_surfaces_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"
    delivery = tmp_path / "delivery"
    (workspace / "artifacts").mkdir(parents=True)
    # receipt declares a file that no longer exists on disk
    receipt = RunReceipt(
        run_id="cli-fail",
        model="test",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execution_state="completed",
        outcome="done",
        artifact_facts=[
            ArtifactFact(
                path="artifacts/missing.pdf", size=3, sha256="0" * 64, change="created"
            )
        ],
    )
    outcome = TerminalRun(presentation="done", receipt=receipt)
    before = receipt.model_dump()

    # the exporter surfaces the failure (raises) without mutating the receipt
    with pytest.raises(DeliveryExportError) as exc_info:
        export_receipt_artifacts(outcome, workspace, delivery)
    assert "cli-fail" in str(exc_info.value)
    assert "artifacts/missing.pdf" in str(exc_info.value)
    assert receipt.model_dump() == before  # in-memory execution truth untouched
    assert not (delivery / "artifacts").exists()

    # the CLI host surfaces delivery failure at the host boundary while
    # preserving the actual run execution result (exit code + receipt).
    monkeypatch.setattr(cli, "run_task", lambda task, settings: outcome)
    code = cli._run(_run_args(workspace, delivery))
    assert code == cli.EXIT_COMPLETED  # the run itself still completed
    captured = capsys.readouterr()
    assert "delivery failure notice" in captured.err
    assert "cli-fail" in captured.err
    assert captured.out.count('"execution_state": "completed"') >= 1
    assert outcome.receipt.execution_state == "completed"  # never rewritten


# ── 4. CLI real caller path + decisive acceptance ──────────────────────────


def test_cli_run_caller_path_exports_after_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "workspace"
    delivery = tmp_path / "delivery"
    (workspace / "artifacts").mkdir(parents=True)
    source = workspace / "artifacts" / "report.md"
    source.write_text("# cli report\n", encoding="utf-8")
    outcome = _terminal(workspace, "artifacts/report.md", run_id="cli-run-1")

    monkeypatch.setattr(cli, "run_task", lambda task, settings: outcome)
    code = cli._run(_run_args(workspace, delivery))

    assert code == cli.EXIT_COMPLETED
    assert (delivery / "artifacts" / "report.md").read_bytes() == source.read_bytes()
    captured = capsys.readouterr()
    assert "delivery failure notice" not in captured.err
    assert '"run_id": "cli-run-1"' in captured.out  # receipt still printed


def test_acceptance_run_export_delete_workspace_bytes_remain(
    tmp_path: Path,
) -> None:
    """Decisive acceptance: the shared production execution path produces the
    report artifact, the host exports it after settlement, deleting the
    runtime workspace can never destroy the durable bytes."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    delivery = tmp_path / "delivery"
    run_id = uuid4().hex
    bundle = build_plugin(
        PluginEnv(
            plugin_id="competitive-intelligence",
            plugin_version="0.1.0",
            workspace_root=workspace.resolve(),
            state_root=tmp_path / ".state",
        ),
        {
            "domain": "ebike",
            "search_backend": "fixture",
            "output_language": "zh-CN",
            "max_search_results": 10,
            "max_fetch_bytes": 5_000_000,
            "max_preview_chars": 2000,
            "fixture_hits": {},
        },
    )
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".state",
        enable_skills=False,
        enable_knowledge=False,
        delivery_root=delivery,
    )

    content = "# Final Charger5 Report\n\nDas 800Wh-Flaggschiff.\n"
    steps: list[str] = []

    def fn(messages, info):  # type: ignore[no-untyped-def]
        if "save" not in steps:
            steps.append("save")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="save_work_product",
                        args=(
                            '{"kind": "report", "content": ' + json.dumps(content) + "}"
                        ),
                    )
                ]
            )
        return ModelResponse(parts=[TextPart("research complete")])

    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=list(bundle.toolsets),
        extra_skill_dirs=bundle.skill_dirs,
    )
    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(
            agent,
            deps=CoreDeps(workspace_root=workspace.resolve(), run_id=run_id),
            prompt="生成竞品报告。",
            settings=settings,
        )
    assert isinstance(outcome, TerminalRun)
    assert outcome.receipt.execution_state == "completed"
    assert any("report.md" in f.path for f in outcome.receipt.artifact_facts)

    # host exports (the exact call cli._run / gateway settlement make)
    result = export_receipt_artifacts(
        outcome, settings.workspace_root, settings.delivery_root
    )
    assert result["status"] == "delivered"
    assert result["files"]
    rel = next(rel for rel in result["files"] if "report.md" in rel)
    durable = delivery / Path(*Path(rel).parts)

    # the reproduced failure mode: the runtime workspace is cleaned up
    shutil.rmtree(workspace)
    assert not workspace.exists()

    # durable artifact bytes still exist and are readable
    assert durable.is_file()
    assert durable.read_bytes() == content.encode("utf-8")
