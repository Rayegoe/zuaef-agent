"""Acceptance tests for the mechanical internal Supervisor Git bus."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from tools import supervisor_loop as loop


def _command(
    cwd: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _command(cwd, "git", *args, check=check)


def _git_text(cwd: Path, *args: str) -> str:
    return _git(cwd, *args).stdout.strip()


def _configure_author(repo: Path) -> None:
    _git(repo, "config", "user.name", "Supervisor Loop Test")
    _git(repo, "config", "user.email", "supervisor-loop@example.invalid")


@dataclass
class Repository:
    root: Path
    remote: Path
    config: loop.LoopConfig
    base: str


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    remote = tmp_path / "remote.git"
    root = tmp_path / "primary"
    remote.mkdir()
    root.mkdir()
    _git(remote, "init", "--bare")
    _git(root, "init", "--initial-branch=main")
    _configure_author(root)
    (root / "payload.txt").write_text("baseline\n", encoding="utf-8")
    prompt = root / "prompts" / "internal-loop" / "CODEX_WORKER_PROMPT.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("Execute only the supplied NEXT.md and STOP.\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "baseline")
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "push", "-u", "origin", "main")
    base = _git_text(root, "rev-parse", "HEAD")
    config = loop.LoopConfig(
        repo=root,
        remote="origin",
        data_root=tmp_path / "local-data",
        state_root=tmp_path / "local-state",
        codex_bin="codex",
    )
    loop.bootstrap(config, base=base, expected_remote_url=str(remote))
    _configure_author(config.report_worktree)
    _configure_author(config.control_worktree)
    return Repository(root=root, remote=remote, config=config, base=base)


def _primary_snapshot(root: Path) -> tuple[str, str, str, bytes]:
    return (
        _git_text(root, "branch", "--show-current"),
        _git_text(root, "status", "--short"),
        _git_text(root, "rev-parse", "main"),
        (root / "payload.txt").read_bytes(),
    )


def _dirty_primary(root: Path) -> None:
    (root / "payload.txt").write_text("unrelated human edit\n", encoding="utf-8")
    (root / "untracked-human-note.txt").write_text("keep me\n", encoding="utf-8")


def _report(base: str, control: str = "NONE") -> str:
    return f"""CONTROL_COMMIT: {control}
WORKER_BASE_COMMIT: {base}

# Supervisor Report

## Subject
Test evidence

## Outcome
Observed test outcome.

## Protected outcome
Transport only.

## What changed
Fixture payload.

## What stayed unchanged
Primary worktree.

## Observed result
Report written.

## Acceptance result
Deterministic test only.

## Evidence / artifacts
Fixture evidence.

## Files changed
payload.txt

## Unknowns / conflicts
None observed.

## Worker stop
STOP.
"""


def _next(base: str, report: str, *, subject: str = "Canary") -> str:
    return f"""BASE_COMMIT: {base}
REPORT_COMMIT: {report}

# Supervisor Instruction

## Decision
NEW_ITERATION

## Protected outcome
Transport canary.

## Observed failure / unmet outcome
Canary not yet observed.

## Primary causal hypothesis
One merged instruction exercises transport.

## Fixed instruction
{subject}; write a no-change report and stop.

## Hold constant
Production code.

## Observable acceptance condition
One report is published.

## Business / evidence guard
Public-safe evidence only.

## Out of scope
Production changes.

## Stop condition
After the report is written, STOP.
"""


def _worker(repository: Repository, name: str) -> Path:
    path = repository.root.parent / name
    _git(repository.root, "worktree", "add", "--detach", str(path), repository.base)
    return path


def _write_outbox(worker: Path, report: str) -> Path:
    outbox = worker / ".zuaef-supervisor"
    outbox.mkdir(parents=True)
    (outbox / "REPORT.md").write_text(report, encoding="utf-8")
    return outbox


def _bare_show(remote: Path, revision_path: str) -> str:
    return _git(remote, "show", revision_path).stdout


def _push_control(
    repository: Repository,
    clone: Path,
    next_text: str,
    *,
    message: str,
) -> str:
    if not clone.exists():
        _git(
            repository.root.parent,
            "clone",
            "--branch",
            loop.CONTROL_BRANCH,
            str(repository.remote),
            str(clone),
        )
        _configure_author(clone)
    target = clone / ".supervisor" / "NEXT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(next_text, encoding="utf-8")
    _git(clone, "add", ".supervisor/NEXT.md")
    _git(clone, "commit", "-m", message)
    _git(clone, "push", "origin", loop.CONTROL_BRANCH)
    return _git_text(clone, "rev-parse", "HEAD")


def test_gate_b_bootstrap_creates_isolated_bus_without_mutating_primary(
    repository: Repository,
) -> None:
    config = repository.config
    assert (
        _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH) == repository.base
    )
    assert (
        _git_text(repository.remote, "rev-parse", loop.CONTROL_BRANCH)
        == repository.base
    )
    assert _git_text(config.report_worktree, "rev-parse", "HEAD") == repository.base
    assert _git_text(config.control_worktree, "rev-parse", "HEAD") == repository.base
    assert (
        config.last_started_file.read_text(encoding="utf-8").strip() == repository.base
    )
    assert _primary_snapshot(repository.root) == (
        "main",
        "",
        repository.base,
        b"baseline\n",
    )
    _dirty_primary(repository.root)
    dirty_snapshot = _primary_snapshot(repository.root)
    loop.bootstrap(
        config,
        base=repository.base,
        expected_remote_url=str(repository.remote),
    )
    assert _primary_snapshot(repository.root) == dirty_snapshot


def test_gate_b_bootstrap_rejects_wrong_fetch_or_push_remote(
    repository: Repository,
) -> None:
    report_before = _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH)
    wrong = repository.root.parent / "different-remote.git"

    with pytest.raises(loop.LoopError, match="expected"):
        loop.bootstrap(
            repository.config,
            base=repository.base,
            expected_remote_url=str(wrong),
        )
    assert (
        _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH) == report_before
    )

    _git(repository.root, "remote", "set-url", "--push", "origin", str(wrong))
    try:
        with pytest.raises(loop.LoopError, match="push URL"):
            loop.bootstrap(
                repository.config,
                base=repository.base,
                expected_remote_url=str(repository.remote),
            )
    finally:
        _git(
            repository.root,
            "remote",
            "set-url",
            "--delete",
            "--push",
            "origin",
            str(wrong),
            check=False,
        )
    assert (
        _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH) == report_before
    )


def test_gate_b_rejects_primary_or_overlapping_supervisor_roots(
    repository: Repository,
) -> None:
    with pytest.raises(loop.LoopError, match="primary worktree"):
        loop._ensure_worktree(
            repository.root,
            repository.root,
            repository.base,
        )
    bad_config = replace(
        repository.config,
        data_root=repository.root / ".supervisor-local-data",
    )
    with pytest.raises(loop.LoopError, match="inside the primary worktree"):
        loop.bootstrap(
            bad_config,
            base=repository.base,
            expected_remote_url=str(repository.remote),
        )
    assert not bad_config.data_root.exists()


def test_gates_b_c_publish_report_patch_and_only_explicit_attachments(
    repository: Repository,
) -> None:
    _dirty_primary(repository.root)
    before = _primary_snapshot(repository.root)
    worker = _worker(repository, "report-worker")
    (worker / "payload.txt").write_text("worker tracked edit\n", encoding="utf-8")
    (worker / "ignored-untracked-secret.txt").write_text(
        "do not publish\n", encoding="utf-8"
    )
    outbox = _write_outbox(worker, _report(repository.base))
    attachments = outbox / "attachments"
    attachments.mkdir()
    (attachments / "evidence.txt").write_text("bounded evidence\n", encoding="utf-8")

    report_commit = loop.publish_report(repository.config, worker_root=worker)

    assert report_commit == _git_text(
        repository.remote, "rev-parse", loop.REPORT_BRANCH
    )
    assert _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/REPORT.md",
    ) == _report(repository.base)
    patch = _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/WORKTREE.patch",
    )
    assert "-baseline" in patch
    assert "+worker tracked edit" in patch
    assert "ignored-untracked-secret" not in patch
    assert (
        _bare_show(
            repository.remote,
            f"{loop.REPORT_BRANCH}:.supervisor/latest/attachments/evidence.txt",
        )
        == "bounded evidence\n"
    )
    tree = _git_text(
        repository.remote,
        "ls-tree",
        "-r",
        "--name-only",
        loop.REPORT_BRANCH,
        ".supervisor/latest",
    )
    assert "ignored-untracked-secret.txt" not in tree
    assert _primary_snapshot(repository.root) == before


def test_gate_c_no_tracked_change_omits_patch(repository: Repository) -> None:
    worker = _worker(repository, "clean-report-worker")
    _write_outbox(worker, _report(repository.base))

    loop.publish_report(repository.config, worker_root=worker)

    tree = _git_text(
        repository.remote,
        "ls-tree",
        "-r",
        "--name-only",
        loop.REPORT_BRANCH,
        ".supervisor/latest",
    )
    assert ".supervisor/latest/REPORT.md" in tree
    assert ".supervisor/latest/WORKTREE.patch" not in tree


def test_gate_c_rejects_environment_and_symlink_attachments(
    repository: Repository,
) -> None:
    worker = _worker(repository, "unsafe-attachment-worker")
    outbox = _write_outbox(worker, _report(repository.base))
    attachments = outbox / "attachments"
    attachments.mkdir()
    report_before = _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH)
    (attachments / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

    with pytest.raises(loop.LoopError, match="environment files"):
        loop.publish_report(repository.config, worker_root=worker)
    assert (
        _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH) == report_before
    )

    (attachments / ".env").unlink()
    outside = worker.parent / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (attachments / "link.txt").symlink_to(outside)
    with pytest.raises(loop.LoopError, match="symlinks"):
        loop.publish_report(repository.config, worker_root=worker)
    assert (
        _git_text(repository.remote, "rev-parse", loop.REPORT_BRANCH) == report_before
    )


def test_gate_d_unchanged_then_one_launch_then_no_duplicate(
    repository: Repository,
) -> None:
    _dirty_primary(repository.root)
    before = _primary_snapshot(repository.root)
    launches: list[tuple[Path, str, str]] = []

    def launcher(
        config: loop.LoopConfig,
        *,
        worker_root: Path,
        control_commit: str,
        base_commit: str,
    ) -> int:
        assert config is repository.config
        launches.append((worker_root, control_commit, base_commit))
        return 0

    assert loop.sync_control(repository.config, launcher=launcher) == 0
    assert launches == []

    control = _push_control(
        repository,
        repository.root.parent / "control-proposer",
        _next(repository.base, repository.base),
        message="authorize canary",
    )
    assert loop.sync_control(repository.config, launcher=launcher) == 0
    assert len(launches) == 1
    worker_root, launched_control, launched_base = launches[0]
    assert launched_control == control
    assert launched_base == repository.base
    assert _git_text(worker_root, "rev-parse", "HEAD") == repository.base
    assert (worker_root / ".supervisor" / "NEXT.md").read_text(
        encoding="utf-8"
    ) == _next(repository.base, repository.base)
    assert (
        repository.config.last_started_file.read_text(encoding="utf-8").strip()
        == control
    )

    assert loop.sync_control(repository.config, launcher=launcher) == 0
    assert len(launches) == 1
    assert _git_text(repository.remote, "rev-parse", "main") == repository.base
    assert _primary_snapshot(repository.root) == before


def test_gate_d_lock_contention_is_a_noop(repository: Repository) -> None:
    launches: list[Path] = []
    with loop._sync_lock(repository.config) as acquired:
        assert acquired is True
        assert (
            loop.sync_control(
                repository.config,
                launcher=lambda *args, **kwargs: launches.append(kwargs["worker_root"]),
            )
            == 0
        )
    assert launches == []


def test_gate_d_launcher_failure_remains_recorded_and_is_not_retried(
    repository: Repository,
) -> None:
    control = _push_control(
        repository,
        repository.root.parent / "crash-proposer",
        _next(repository.base, repository.base),
        message="authorize crashing launcher",
    )
    launches: list[str] = []

    def crashing_launcher(
        config: loop.LoopConfig,
        *,
        worker_root: Path,
        control_commit: str,
        base_commit: str,
    ) -> int:
        del worker_root, base_commit
        launches.append(control_commit)
        assert config.last_started_file.read_text(encoding="utf-8").strip() == control
        raise RuntimeError("simulated launcher crash")

    with pytest.raises(RuntimeError, match="simulated launcher crash"):
        loop.sync_control(repository.config, launcher=crashing_launcher)
    assert launches == [control]

    assert loop.sync_control(repository.config, launcher=crashing_launcher) == 0
    assert launches == [control]


def test_gate_d_control_commit_must_change_next_and_stale_file_is_ignored(
    repository: Repository,
) -> None:
    stale = repository.config.control_worktree / ".supervisor" / "NEXT.md"
    stale.parent.mkdir(parents=True)
    stale.write_text(_next(repository.base, repository.base), encoding="utf-8")
    proposer = repository.root.parent / "non-instruction-proposer"
    _git(
        repository.root.parent,
        "clone",
        "--branch",
        loop.CONTROL_BRANCH,
        str(repository.remote),
        str(proposer),
    )
    _configure_author(proposer)
    (proposer / "CONTROL-NOTE.md").write_text("not an instruction\n", encoding="utf-8")
    _git(proposer, "add", "CONTROL-NOTE.md")
    _git(proposer, "commit", "-m", "control metadata only")
    _git(proposer, "push", "origin", loop.CONTROL_BRANCH)

    with pytest.raises(loop.LoopError, match="CONTROL_COMMIT_HAS_NO_NEW_INSTRUCTION"):
        loop.sync_control(repository.config, launcher=lambda *args, **kwargs: 0)
    assert (
        repository.config.last_started_file.read_text(encoding="utf-8").strip()
        == repository.base
    )


def test_gate_d_missing_base_header_does_not_launch(repository: Repository) -> None:
    baseline = repository.config.last_started_file.read_text(encoding="utf-8")
    invalid_next = _next(repository.base, repository.base).replace(
        f"BASE_COMMIT: {repository.base}\n", ""
    )
    _push_control(
        repository,
        repository.root.parent / "missing-base-proposer",
        invalid_next,
        message="missing base",
    )
    launches: list[Path] = []

    with pytest.raises(loop.LoopError, match="BASE_COMMIT"):
        loop.sync_control(
            repository.config,
            launcher=lambda *args, **kwargs: launches.append(kwargs["worker_root"]),
        )

    assert launches == []
    assert repository.config.last_started_file.read_text(encoding="utf-8") == baseline


def test_gate_d_unavailable_base_does_not_launch(repository: Repository) -> None:
    missing = "f" * 40
    baseline = repository.config.last_started_file.read_text(encoding="utf-8")
    _push_control(
        repository,
        repository.root.parent / "unavailable-base-proposer",
        _next(missing, repository.base),
        message="unavailable base",
    )
    launches: list[Path] = []

    with pytest.raises(loop.LoopError, match="BASE_COMMIT_UNAVAILABLE"):
        loop.sync_control(
            repository.config,
            launcher=lambda *args, **kwargs: launches.append(kwargs["worker_root"]),
        )

    assert launches == []
    assert repository.config.last_started_file.read_text(encoding="utf-8") == baseline


def test_gate_d_multiple_unconsumed_commits_stop_with_control_gap(
    repository: Repository,
) -> None:
    proposer = repository.root.parent / "gap-proposer"
    _push_control(
        repository,
        proposer,
        _next(repository.base, repository.base, subject="First"),
        message="first pending control",
    )
    _push_control(
        repository,
        proposer,
        _next(repository.base, repository.base, subject="Second"),
        message="second pending control",
    )
    launches: list[Path] = []

    with pytest.raises(loop.LoopError, match="CONTROL_GAP"):
        loop.sync_control(
            repository.config,
            launcher=lambda *args, **kwargs: launches.append(kwargs["worker_root"]),
        )

    assert launches == []
    assert (
        repository.config.last_started_file.read_text(encoding="utf-8").strip()
        == repository.base
    )


def test_gate_c_missing_worker_report_publishes_mechanical_facts_only(
    repository: Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    control_commit = _push_control(
        repository,
        repository.root.parent / "failed-worker-proposer",
        _next(repository.base, repository.base),
        message="authorize failed worker",
    )
    monkeypatch.setattr(loop, "_invoke_codex", lambda *args, **kwargs: 17)

    exit_code = loop.sync_control(repository.config)

    assert exit_code == 17
    report = _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/REPORT.md",
    )
    assert f"CONTROL_COMMIT: {control_commit}" in report
    assert "Observed process exit code: 17." in report
    assert "Not evaluated by the mechanical launcher." in report
    assert "No automatic retry was attempted." in report
    assert "ACCEPT\n" not in report


def test_gate_c_process_launch_failure_publishes_mechanical_fact(
    repository: Repository,
) -> None:
    control_commit = _push_control(
        repository,
        repository.root.parent / "missing-codex-proposer",
        _next(repository.base, repository.base),
        message="authorize missing executable test",
    )
    config = replace(
        repository.config,
        codex_bin=str(repository.root.parent / "does-not-exist"),
    )

    assert loop.sync_control(config) == 127

    report = _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/REPORT.md",
    )
    assert f"CONTROL_COMMIT: {control_commit}" in report
    assert "Codex process launch failed: FileNotFoundError" in report
    assert "No automatic retry was attempted." in report


def test_gates_c_d_real_subprocess_handoff_uses_exact_prompt_and_next(
    repository: Repository,
) -> None:
    control_commit = _push_control(
        repository,
        repository.root.parent / "successful-worker-proposer",
        _next(repository.base, repository.base, subject="Successful handoff"),
        message="authorize successful worker",
    )
    fake_codex = repository.root.parent / "fake-codex"
    fake_codex.write_text(
        '''#!/usr/bin/env python3
import re
import sys
from pathlib import Path

root = Path.cwd()
stdin = sys.stdin.read()
(root / "codex-capture.txt").write_text(
    "ARGS=" + repr(sys.argv[1:]) + "\\n---STDIN---\\n" + stdin,
    encoding="utf-8",
)
next_text = (root / ".supervisor" / "NEXT.md").read_text(encoding="utf-8")
base = re.search(r"^BASE_COMMIT: (\\S+)$", next_text, re.MULTILINE).group(1)
control = root.name
outbox = root / ".zuaef-supervisor"
outbox.mkdir()
(outbox / "REPORT.md").write_text(
    f"""CONTROL_COMMIT: {control}
WORKER_BASE_COMMIT: {base}

# Supervisor Report
## Subject
Fake Codex success
## Outcome
Observed success.
## Protected outcome
Transport only.
## What changed
No tracked change.
## What stayed unchanged
Production code.
## Observed result
Exact handoff captured.
## Acceptance result
Pass.
## Evidence / artifacts
codex-capture.txt
## Files changed
None tracked.
## Unknowns / conflicts
None.
## Worker stop
STOP.
""",
    encoding="utf-8",
)
''',
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    config = replace(repository.config, codex_bin=str(fake_codex))

    assert loop.sync_control(config) == 0

    worker = config.workers_root / control_commit
    capture = (worker / "codex-capture.txt").read_text(encoding="utf-8")
    assert "'exec'" in capture
    assert f"'--cd', '{worker}'" in capture
    assert "'--sandbox', 'workspace-write'" in capture
    assert "'--approve-for-me', '-'" in capture
    assert "Execute only the supplied NEXT.md and STOP." in capture
    assert (
        _next(repository.base, repository.base, subject="Successful handoff") in capture
    )
    published = _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/REPORT.md",
    )
    assert f"CONTROL_COMMIT: {control_commit}" in published


def test_run_next_rejects_unmerged_control_sha(repository: Repository) -> None:
    worker = repository.config.workers_root / ("a" * 40)
    _git(repository.root, "worktree", "add", "--detach", str(worker), repository.base)
    next_path = worker / ".supervisor" / "NEXT.md"
    next_path.parent.mkdir(parents=True)
    next_path.write_text(_next(repository.base, repository.base), encoding="utf-8")

    with pytest.raises(loop.LoopError, match="not reachable"):
        loop.run_next(
            repository.config,
            worker_root=worker,
            control_commit="a" * 40,
            base_commit=repository.base,
        )


def test_gate_e_authority_files_stop_after_one_instruction() -> None:
    project_root = Path(__file__).resolve().parents[1]
    agents = (project_root / "AGENTS.md").read_text(encoding="utf-8")
    prompt = (
        project_root / "prompts" / "internal-loop" / "CODEX_WORKER_PROMPT.md"
    ).read_text(encoding="utf-8")
    operations = (project_root / "docs" / "internal-loop" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "instruction is the worker's execution authority" in agents
    assert "`TASKS.md` remains\nbacklog/evidence" in agents
    assert "does not authorize the\nnext task" in agents
    assert "execution authority is the exact `.supervisor/NEXT.md`" in prompt
    assert "begin a follow-up iteration" in prompt
    assert "When complete: STOP." in prompt
    assert "`STOP` and non-executable `ACCEPT` create no control PR" in operations


# ── Telegram operator notification wiring (zuaef-telegram REVISE) ───────────


def _stub_notifier(monkeypatch, calls: list) -> None:
    import zuaef_telegram.notify as tg_notify

    def _record(message: str) -> dict:
        calls.append(message)
        return {"ok": True}

    monkeypatch.setattr(tg_notify, "notify_operator", _record)


def test_publish_report_notifies_operator_exactly_once(repository, monkeypatch):
    calls: list[str] = []
    _stub_notifier(monkeypatch, calls)
    worker = _worker(repository, "notify-worker")
    _write_outbox(worker, _report(repository.base))

    loop.publish_report(repository.config, worker_root=worker)

    assert len(calls) == 1
    assert calls[0] == (
        "ZUAEF Supervisor report published. Open the Supervisor Project and send 继续."
    )


def test_publish_report_duplicate_does_not_notify_again(repository, monkeypatch):
    calls: list[str] = []
    _stub_notifier(monkeypatch, calls)
    worker = _worker(repository, "notify-dup-worker")
    _write_outbox(worker, _report(repository.base))
    loop.publish_report(repository.config, worker_root=worker)

    loop.publish_report(repository.config, worker_root=worker)  # unchanged

    assert len(calls) == 1, "an unchanged report is not a new publication"


def test_publish_report_survives_notification_failure(repository, monkeypatch):
    import zuaef_telegram.notify as tg_notify

    def _boom(message: str) -> dict:
        raise tg_notify.TelegramError("telegram sendMessage failed: HTTP 500")

    monkeypatch.setattr(tg_notify, "notify_operator", _boom)
    worker = _worker(repository, "notify-fail-worker")
    _write_outbox(worker, _report(repository.base))

    report_commit = loop.publish_report(repository.config, worker_root=worker)

    assert report_commit == _git_text(
        repository.remote, "rev-parse", loop.REPORT_BRANCH
    )
    assert _bare_show(
        repository.remote,
        f"{loop.REPORT_BRANCH}:.supervisor/latest/REPORT.md",
    ) == _report(repository.base)
