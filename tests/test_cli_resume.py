"""CLI resume regression tests — SPEC v0.3 §24, §77.

``zuaef-agent resume --approve/--deny`` must keep its behavior and delegate
to the shared ``resume_paused_run`` seam — the CLI must not reimplement the
continuation orchestration.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from zuaef_agent import cli
from zuaef_agent.models import RunReceipt
from zuaef_agent.runtime import TerminalRun


def _args(run_id: str, *, approve: bool = False, deny: bool = False, reason: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        run_id=run_id,
        approve=approve,
        deny=deny,
        reason=reason,
        model=None,
        workspace=None,
        request_limit=None,
        tool_calls_limit=None,
        total_tokens_limit=None,
    )


def _terminal(state: str = "completed") -> TerminalRun:
    now = datetime.now(UTC)
    receipt = RunReceipt(
        run_id="new-run",
        model="m",
        started_at=now,
        finished_at=now,
        execution_state=state,  # type: ignore[arg-type]
        outcome="ok",
    )
    return TerminalRun(presentation=receipt.outcome, receipt=receipt)


def test_resume_requires_exactly_one_decision(tmp_path: Path, capsys):
    assert cli._resume(_args("r1")) == cli.EXIT_PROCESS_ERROR
    assert "exactly one of" in capsys.readouterr().err

    assert cli._resume(_args("r1", approve=True, deny=True)) == cli.EXIT_PROCESS_ERROR
    assert "exactly one of" in capsys.readouterr().err


def test_cli_resume_delegates_to_shared_continuation(tmp_path: Path, monkeypatch, capsys):
    calls: dict = {}

    def fake_resume(settings, paused_run_id, *, decision, reason=None):
        calls["paused_run_id"] = paused_run_id
        calls["decision"] = decision
        calls["reason"] = reason
        return _terminal("completed")

    monkeypatch.setattr(cli, "resume_paused_run", fake_resume)

    code = cli._resume(_args("paused-1", approve=True))
    assert code == cli.EXIT_COMPLETED
    assert calls == {"paused_run_id": "paused-1", "decision": "approve", "reason": None}
    assert '"run_id": "new-run"' in capsys.readouterr().out

    code = cli._resume(_args("paused-2", deny=True, reason="operator refused"))
    assert code == cli.EXIT_COMPLETED
    assert calls == {"paused_run_id": "paused-2", "decision": "deny", "reason": "operator refused"}


def test_cli_resume_keeps_exit_codes_for_shared_outcomes(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "resume_paused_run", lambda *a, **kw: _terminal("failed"))
    assert cli._resume(_args("r", approve=True)) == cli.EXIT_BLOCKED

    monkeypatch.setattr(cli, "resume_paused_run", lambda *a, **kw: _terminal("limit_reached"))
    assert cli._resume(_args("r", approve=True)) == cli.EXIT_PARTIAL


def test_cli_resume_prints_original_message_for_not_paused(tmp_path: Path, monkeypatch, capsys):
    def fake_resume(settings, paused_run_id, *, decision, reason=None):
        raise ValueError(f"run {paused_run_id} is not paused; resume needs a pause receipt")

    monkeypatch.setattr(cli, "resume_paused_run", fake_resume)

    code = cli._resume(_args("stale-run", approve=True))
    assert code == cli.EXIT_PROCESS_ERROR
    assert capsys.readouterr().err.strip() == "run stale-run is not paused; resume needs a pause receipt"


def test_cli_source_delegates_without_reimplementing_continuation():
    """Static guard: the CLI calls resume_paused_run and no longer owns
    StepPersistence/DeferredToolResults orchestration of its own."""
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "resume_paused_run" in source
    assert "continue_run" not in source
    assert "DeferredToolRequests" not in source
    assert "FileStepStore" not in source
