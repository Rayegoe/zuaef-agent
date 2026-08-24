#!/usr/bin/env python3
"""Mechanical Git transport for the ZUAEF internal Supervisor loop.

This module deliberately owns transport only.  Git commits and branches are
the handoff record; semantic decisions remain with the Project Supervisor and
the human who merges a control PR.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

REPORT_BRANCH = "supervisor-report"
CONTROL_BRANCH = "supervisor-control"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTED_REMOTE = "https://github.com/Rayegoe/zuaef-agent.git"

REPORT_SECTIONS = (
    "# Supervisor Report",
    "## Subject",
    "## Outcome",
    "## Protected outcome",
    "## What changed",
    "## What stayed unchanged",
    "## Observed result",
    "## Acceptance result",
    "## Evidence / artifacts",
    "## Files changed",
    "## Unknowns / conflicts",
    "## Worker stop",
)
NEXT_SECTIONS = (
    "# Supervisor Instruction",
    "## Decision",
    "## Protected outcome",
    "## Observed failure / unmet outcome",
    "## Primary causal hypothesis",
    "## Fixed instruction",
    "## Hold constant",
    "## Observable acceptance condition",
    "## Business / evidence guard",
    "## Out of scope",
    "## Stop condition",
)


class LoopError(RuntimeError):
    """A bounded transport or launch failure."""


@dataclass(frozen=True)
class LoopConfig:
    repo: Path
    remote: str
    data_root: Path
    state_root: Path
    codex_bin: str = "codex"

    @property
    def report_worktree(self) -> Path:
        return self.data_root / "report"

    @property
    def control_worktree(self) -> Path:
        return self.data_root / "control"

    @property
    def workers_root(self) -> Path:
        return self.data_root / "workers"

    @property
    def last_started_file(self) -> Path:
        return self.state_root / "last-started-control"

    @property
    def lock_file(self) -> Path:
        return self.state_root / "sync.lock"


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        text=True,
        input=input_text,
        capture_output=capture_output,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "no command output").strip()
        raise LoopError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{detail}"
        )
    return result


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(("git", *args), cwd=cwd, check=check)


def _git_stdout(cwd: Path, *args: str) -> str:
    return _git(cwd, *args).stdout.strip()


def _validate_config_roots(config: LoopConfig) -> None:
    repo = config.repo.resolve()
    for label, root in (
        ("data root", config.data_root.resolve()),
        ("state root", config.state_root.resolve()),
    ):
        if root == repo or repo in root.parents:
            raise LoopError(f"{label} may not be inside the primary worktree: {root}")


def _full_commit(repo: Path, revision: str) -> str:
    commit = _git_stdout(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if not SHA_RE.fullmatch(commit):
        raise LoopError(f"Git did not resolve a full commit for {revision!r}")
    return commit


def _remote_identity(url: str) -> str:
    value = url.strip().rstrip("/").removesuffix(".git")
    if value.startswith("git@") and ":" in value:
        host, path = value[4:].split(":", 1)
        return f"{host.lower()}/{path.lower()}"
    match = re.match(r"^[a-z]+://(?:[^@/]+@)?([^/]+)/(.+)$", value, re.IGNORECASE)
    if match:
        return f"{match.group(1).lower()}/{match.group(2).lower()}"
    return str(Path(value).expanduser().resolve())


def _verify_remote(config: LoopConfig, expected_url: str) -> str:
    actual = _git_stdout(config.repo, "remote", "get-url", config.remote)
    if _remote_identity(actual) != _remote_identity(expected_url):
        raise LoopError(
            f"remote {config.remote!r} is {actual!r}, expected {expected_url!r}"
        )
    push_url = _git_stdout(config.repo, "remote", "get-url", "--push", config.remote)
    if _remote_identity(push_url) != _remote_identity(expected_url):
        raise LoopError(
            f"push URL for {config.remote!r} is {push_url!r}, expected {expected_url!r}"
        )
    return actual


def _remote_ref(config: LoopConfig, branch: str) -> str:
    return f"refs/remotes/{config.remote}/{branch}"


def _fetch_branch(config: LoopConfig, branch: str) -> str:
    refspec = f"+refs/heads/{branch}:{_remote_ref(config, branch)}"
    _git(config.repo, "fetch", "--no-tags", config.remote, refspec)
    return _full_commit(config.repo, _remote_ref(config, branch))


def _ensure_remote_branch(config: LoopConfig, branch: str, base: str) -> str:
    probe = _git(
        config.repo,
        "ls-remote",
        "--exit-code",
        "--heads",
        config.remote,
        branch,
        check=False,
    )
    if probe.returncode == 2:
        _git(config.repo, "push", config.remote, f"{base}:refs/heads/{branch}")
    elif probe.returncode != 0:
        detail = (probe.stderr or probe.stdout or "no command output").strip()
        raise LoopError(f"cannot inspect remote branch {branch}: {detail}")
    return _fetch_branch(config, branch)


def _common_git_dir(repo: Path) -> Path:
    raw = Path(_git_stdout(repo, "rev-parse", "--git-common-dir"))
    return (repo / raw).resolve() if not raw.is_absolute() else raw.resolve()


def _ensure_worktree(repo: Path, path: Path, revision: str) -> None:
    repo = repo.resolve()
    path = path.resolve()
    if path == repo:
        raise LoopError(
            "refusing to use the primary worktree as transport or worker state"
        )
    if path.exists():
        if not path.is_dir():
            raise LoopError(f"worktree target is not a directory: {path}")
        probe = _git(path, "rev-parse", "--show-toplevel", check=False)
        if probe.returncode != 0 or Path(probe.stdout.strip()).resolve() != path:
            raise LoopError(f"refusing to replace non-worktree directory: {path}")
        if _common_git_dir(path) != _common_git_dir(repo):
            raise LoopError(f"worktree belongs to a different repository: {path}")
        if _git(path, "symbolic-ref", "-q", "HEAD", check=False).returncode == 0:
            raise LoopError(f"transport/worker worktree must be detached: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        _git(repo, "worktree", "add", "--detach", str(path), revision)
    _git(path, "reset", "--hard", revision)


def _write_last_started(config: LoopConfig, commit: str) -> None:
    if not SHA_RE.fullmatch(commit):
        raise LoopError("refusing to record a non-canonical control commit")
    config.state_root.mkdir(parents=True, exist_ok=True)
    config.last_started_file.write_text(f"{commit}\n", encoding="utf-8")


def _read_last_started(config: LoopConfig) -> str | None:
    if not config.last_started_file.exists():
        return None
    value = config.last_started_file.read_text(encoding="utf-8").strip()
    if not SHA_RE.fullmatch(value):
        raise LoopError("invalid last-started-control state")
    return value


@contextmanager
def _sync_lock(config: LoopConfig) -> Iterator[bool]:
    config.state_root.mkdir(parents=True, exist_ok=True)
    with config.lock_file.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _header(text: str, name: str, *, allow_none: bool = False) -> str:
    matches = re.findall(rf"^{re.escape(name)}:\s*(\S+)\s*$", text, re.MULTILINE)
    if len(matches) != 1:
        raise LoopError(f"{name} must appear exactly once")
    value = matches[0]
    if allow_none and value == "NONE":
        return value
    if not SHA_RE.fullmatch(value):
        raise LoopError(f"{name} must contain a full lowercase Git commit")
    return value


def _require_report_contract(text: str) -> None:
    _header(text, "CONTROL_COMMIT", allow_none=True)
    _header(text, "WORKER_BASE_COMMIT")
    missing = [
        heading
        for heading in REPORT_SECTIONS
        if not re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE)
    ]
    if missing:
        raise LoopError(f"REPORT.md is missing required sections: {', '.join(missing)}")


def _require_next_contract(text: str) -> tuple[str, str]:
    base_commit = _header(text, "BASE_COMMIT")
    report_commit = _header(text, "REPORT_COMMIT")
    missing = [
        heading
        for heading in NEXT_SECTIONS
        if not re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE)
    ]
    if missing:
        raise LoopError(f"NEXT.md is missing required sections: {', '.join(missing)}")
    return base_commit, report_commit


def _commit_file(repo: Path, commit: str, path: str, *, label: str) -> str:
    result = _git(repo, "show", f"{commit}:{path}", check=False)
    if result.returncode != 0:
        raise LoopError(f"{label} is missing from control commit {commit}")
    return result.stdout


def _forbidden_attachment(path: Path) -> bool:
    return any(part == ".env" or part.startswith(".env.") for part in path.parts)


def _copy_attachments(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    if source.is_symlink() or not source.is_dir():
        raise LoopError("attachments must be a real directory")
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        if item.is_symlink():
            raise LoopError(f"attachments may not contain symlinks: {relative}")
        if _forbidden_attachment(relative):
            raise LoopError(
                f"attachments may not contain environment files: {relative}"
            )
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
        else:
            raise LoopError(f"attachments must contain regular files only: {relative}")


def bootstrap(config: LoopConfig, *, base: str, expected_remote_url: str) -> None:
    """Ensure both bus branches, detached transport worktrees, and local state."""

    _validate_config_roots(config)
    _verify_remote(config, expected_remote_url)
    base_commit = _full_commit(config.repo, base)
    report_head = _ensure_remote_branch(config, REPORT_BRANCH, base_commit)
    control_head = _ensure_remote_branch(config, CONTROL_BRANCH, base_commit)
    _ensure_worktree(config.repo, config.report_worktree, report_head)
    _ensure_worktree(config.repo, config.control_worktree, control_head)
    config.workers_root.mkdir(parents=True, exist_ok=True)
    config.state_root.mkdir(parents=True, exist_ok=True)
    if not config.last_started_file.exists():
        _write_last_started(config, control_head)
    print(f"remote: {_git_stdout(config.repo, 'remote', 'get-url', config.remote)}")
    print(f"base: {base_commit}")
    print(f"report worktree: {config.report_worktree}")
    print(f"control worktree: {config.control_worktree}")
    print("install the user timer with the commands in docs/internal-loop/README.md")


def _worker_diff(worker_root: Path, base_commit: str) -> str:
    _full_commit(worker_root, base_commit)
    return _git(worker_root, "diff", "--binary", base_commit, "--").stdout


def _notify_report_published() -> None:
    """Best-effort mechanical operator notification after a successful publish.

    The report publication is already durable by the time this runs; a
    Telegram failure — or an environment where zuaef-telegram is not
    installed — must never invalidate it, so every failure is a logged
    warning, never an error. The message is fixed and mechanical: no report
    body, no secrets, no semantic reinterpretation.
    """
    try:
        from zuaef_telegram.notify import notify_operator

        notify_operator(
            "ZUAEF Supervisor report published. "
            "Open the Supervisor Project and send 继续."
        )
    except Exception as exc:  # noqa: BLE001 - optional transport by contract
        print(
            f"supervisor-loop: telegram notification skipped: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )


def publish_report(config: LoopConfig, *, worker_root: Path) -> str:
    """Publish the explicit worker outbox through the dedicated report worktree."""

    _validate_config_roots(config)
    worker_root = worker_root.resolve()
    if _common_git_dir(worker_root) != _common_git_dir(config.repo):
        raise LoopError("worker root belongs to a different repository")
    outbox = worker_root / ".zuaef-supervisor"
    if outbox.is_symlink():
        raise LoopError("worker outbox must be a real directory")
    source_report = outbox / "REPORT.md"
    if not source_report.is_file() or source_report.is_symlink():
        raise LoopError(f"worker report is missing: {source_report}")
    report_text = source_report.read_text(encoding="utf-8")
    _require_report_contract(report_text)
    base_commit = _header(report_text, "WORKER_BASE_COMMIT")

    report_head = _fetch_branch(config, REPORT_BRANCH)
    _ensure_worktree(config.repo, config.report_worktree, report_head)
    supervisor_dir = config.report_worktree / ".supervisor"
    if supervisor_dir.exists() and (
        supervisor_dir.is_symlink() or not supervisor_dir.is_dir()
    ):
        raise LoopError("report branch .supervisor must be a real directory")
    latest = supervisor_dir / "latest"
    if latest.exists():
        if latest.is_symlink() or not latest.is_dir():
            raise LoopError("report destination must be a real directory")
        shutil.rmtree(latest)
    latest.mkdir(parents=True)
    (latest / "REPORT.md").write_text(report_text, encoding="utf-8")
    _copy_attachments(outbox / "attachments", latest / "attachments")

    patch = _worker_diff(worker_root, base_commit)
    if patch:
        (latest / "WORKTREE.patch").write_text(patch, encoding="utf-8")

    _git(
        config.report_worktree,
        "add",
        "--all",
        "--force",
        "--",
        ".supervisor/latest",
    )
    changed = _git(
        config.report_worktree,
        "diff",
        "--cached",
        "--quiet",
        check=False,
    )
    if changed.returncode == 0:
        print(f"report unchanged at {report_head}")
        return report_head
    if changed.returncode != 1:
        raise LoopError("unable to inspect staged report changes")

    control_commit = _header(report_text, "CONTROL_COMMIT", allow_none=True)
    subject = "NONE" if control_commit == "NONE" else control_commit[:12]
    _git(config.report_worktree, "commit", "-m", f"supervisor report: {subject}")
    report_commit = _full_commit(config.report_worktree, "HEAD")
    _git(
        config.report_worktree,
        "push",
        config.remote,
        f"HEAD:refs/heads/{REPORT_BRANCH}",
    )
    print(f"published report {report_commit}")
    _notify_report_published()
    return report_commit


def _ensure_base_commit(config: LoopConfig, base_commit: str) -> None:
    if not SHA_RE.fullmatch(base_commit):
        raise LoopError("BASE_COMMIT must contain a full lowercase Git commit")
    probe = _git(
        config.repo, "cat-file", "-e", f"{base_commit}^{{commit}}", check=False
    )
    if probe.returncode == 0:
        return
    fetched = _git(
        config.repo,
        "fetch",
        "--no-tags",
        config.remote,
        base_commit,
        check=False,
    )
    if fetched.returncode != 0:
        raise LoopError(f"BASE_COMMIT_UNAVAILABLE: {base_commit}")
    probe = _git(
        config.repo, "cat-file", "-e", f"{base_commit}^{{commit}}", check=False
    )
    if probe.returncode != 0:
        raise LoopError(f"BASE_COMMIT_UNAVAILABLE: {base_commit}")


def _mechanical_failure_report(
    *,
    control_commit: str,
    base_commit: str,
    exit_code: int,
    process_fact: str | None = None,
) -> str:
    observed = process_fact or f"Observed process exit code: {exit_code}."
    return f"""CONTROL_COMMIT: {control_commit}
WORKER_BASE_COMMIT: {base_commit}

# Supervisor Report

## Subject
Worker process exited without the required report.

## Outcome
{observed}

## Protected outcome
Not evaluated by the mechanical launcher.

## What changed
Not evaluated by the mechanical launcher.

## What stayed unchanged
Not evaluated by the mechanical launcher.

## Observed result
`.zuaef-supervisor/REPORT.md` was absent after process exit.

## Acceptance result
Not evaluated by the mechanical launcher.

## Evidence / artifacts
Launcher-observed process fact only: {observed}

## Files changed
Not evaluated by the mechanical launcher.

## Unknowns / conflicts
Worker semantic outcome and workspace changes are unknown to the launcher.

## Worker stop
The worker process has exited. No automatic retry was attempted.
"""


def _invoke_codex(config: LoopConfig, worker_root: Path, prompt: str) -> int:
    result = _run(
        (
            config.codex_bin,
            "exec",
            "--cd",
            str(worker_root),
            "--sandbox",
            "workspace-write",
            "--approve-for-me",
            "-",
        ),
        cwd=worker_root,
        check=False,
        input_text=prompt,
        capture_output=False,
    )
    return result.returncode


def run_next(
    config: LoopConfig,
    *,
    worker_root: Path,
    control_commit: str,
    base_commit: str,
) -> int:
    """Run exactly one materialized NEXT.md and publish the resulting report."""

    _validate_config_roots(config)
    worker_root = worker_root.resolve()
    workers_root = config.workers_root.resolve()
    if workers_root not in worker_root.parents:
        raise LoopError("run-next requires an isolated configured worker worktree")
    if _common_git_dir(worker_root) != _common_git_dir(config.repo):
        raise LoopError("worker worktree belongs to a different repository")
    if not SHA_RE.fullmatch(control_commit):
        raise LoopError("CONTROL_COMMIT must contain a full lowercase Git commit")
    next_path = worker_root / ".supervisor" / "NEXT.md"
    if not next_path.is_file() or next_path.is_symlink():
        raise LoopError(f"merged instruction is missing: {next_path}")
    next_text = next_path.read_text(encoding="utf-8")
    control_head = _fetch_branch(config, CONTROL_BRANCH)
    ancestor = _git(
        config.repo,
        "merge-base",
        "--is-ancestor",
        control_commit,
        control_head,
        check=False,
    )
    if ancestor.returncode != 0:
        raise LoopError("CONTROL_COMMIT is not reachable from supervisor-control")
    merged_next = _commit_file(
        config.repo,
        control_commit,
        ".supervisor/NEXT.md",
        label="merged NEXT.md",
    )
    if next_text != merged_next:
        raise LoopError("materialized NEXT.md is not the exact merged control blob")
    parsed_base, _ = _require_next_contract(next_text)
    if parsed_base != base_commit:
        raise LoopError("materialized NEXT.md does not match the selected BASE_COMMIT")
    if _full_commit(worker_root, "HEAD") != base_commit:
        raise LoopError("worker worktree is not at the exact BASE_COMMIT")
    worker_prompt = worker_root / "prompts" / "internal-loop" / "CODEX_WORKER_PROMPT.md"
    if not worker_prompt.is_file() or worker_prompt.is_symlink():
        raise LoopError(
            f"fixed worker prompt is missing from BASE_COMMIT: {worker_prompt}"
        )
    fixed_prompt = worker_prompt.read_text(encoding="utf-8")
    combined_prompt = (
        f"{fixed_prompt.rstrip()}\n\n"
        "--- BEGIN EXACT MERGED .supervisor/NEXT.md ---\n"
        f"{next_text.rstrip()}\n"
        "--- END EXACT MERGED .supervisor/NEXT.md ---\n"
    )
    outbox = worker_root / ".zuaef-supervisor"
    if outbox.exists() or outbox.is_symlink():
        raise LoopError("fresh worker already contains a Supervisor report outbox")
    process_fact: str | None = None
    try:
        exit_code = _invoke_codex(config, worker_root, combined_prompt)
    except OSError as exc:
        exit_code = 127
        process_fact = f"Codex process launch failed: {type(exc).__name__}: {exc}"
    report_path = outbox / "REPORT.md"
    if outbox.is_symlink() or (outbox.exists() and not outbox.is_dir()):
        outbox.unlink()
    if report_path.is_symlink():
        report_path.unlink()
        process_fact = "Worker produced a symlink instead of a regular REPORT.md."
    if not report_path.is_file():
        outbox.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            _mechanical_failure_report(
                control_commit=control_commit,
                base_commit=base_commit,
                exit_code=exit_code,
                process_fact=process_fact,
            ),
            encoding="utf-8",
        )
    report_text = report_path.read_text(encoding="utf-8")
    if _header(report_text, "CONTROL_COMMIT", allow_none=True) != control_commit:
        raise LoopError(
            "worker report CONTROL_COMMIT does not match the merged instruction"
        )
    if _header(report_text, "WORKER_BASE_COMMIT") != base_commit:
        raise LoopError("worker report WORKER_BASE_COMMIT does not match NEXT.md")
    publish_report(config, worker_root=worker_root)
    return exit_code


Launcher = Callable[..., int]


def sync_control(
    config: LoopConfig,
    *,
    launcher: Launcher = run_next,
) -> int:
    """Poll the merged control branch once and launch at most one worker."""

    _validate_config_roots(config)
    with _sync_lock(config) as acquired:
        if not acquired:
            print("sync already active; no-op")
            return 0

        control_head = _fetch_branch(config, CONTROL_BRANCH)
        _ensure_worktree(config.repo, config.control_worktree, control_head)
        last_started = _read_last_started(config)
        if last_started is None:
            _write_last_started(config, control_head)
            print(f"initialized control baseline at {control_head}; no worker launched")
            return 0
        if last_started == control_head:
            print(f"control unchanged at {control_head}; no worker launched")
            return 0

        ancestor = _git(
            config.repo,
            "merge-base",
            "--is-ancestor",
            last_started,
            control_head,
            check=False,
        )
        if ancestor.returncode != 0:
            raise LoopError(
                f"CONTROL_GAP: {last_started} is not an ancestor of {control_head}"
            )
        pending = int(
            _git_stdout(
                config.repo,
                "rev-list",
                "--first-parent",
                "--count",
                f"{last_started}..{control_head}",
            )
        )
        if pending != 1:
            raise LoopError(
                f"CONTROL_GAP: {pending} unconsumed first-parent control commits"
            )

        instruction_change = _git(
            config.repo,
            "diff",
            "--quiet",
            last_started,
            control_head,
            "--",
            ".supervisor/NEXT.md",
            check=False,
        )
        if instruction_change.returncode == 0:
            raise LoopError("CONTROL_COMMIT_HAS_NO_NEW_INSTRUCTION")
        if instruction_change.returncode != 1:
            raise LoopError("unable to verify the merged instruction change")
        next_text = _commit_file(
            config.repo,
            control_head,
            ".supervisor/NEXT.md",
            label="merged NEXT.md",
        )
        base_commit, _ = _require_next_contract(next_text)
        _ensure_base_commit(config, base_commit)

        # At-most-once automatic launch: a crash after this point requires a new
        # human/Supervisor decision, never a silent semantic retry.
        _write_last_started(config, control_head)
        worker_root = config.workers_root / control_head
        if worker_root.exists():
            raise LoopError(
                f"worker path already exists after control was recorded: {worker_root}"
            )
        _ensure_worktree(config.repo, worker_root, base_commit)
        supervisor_dir = worker_root / ".supervisor"
        if supervisor_dir.exists() and (
            supervisor_dir.is_symlink() or not supervisor_dir.is_dir()
        ):
            raise LoopError("worker .supervisor path must be a real directory")
        materialized = supervisor_dir / "NEXT.md"
        supervisor_dir.mkdir(parents=True, exist_ok=True)
        materialized.write_text(next_text, encoding="utf-8")
        return launcher(
            config,
            worker_root=worker_root,
            control_commit=control_head,
            base_commit=base_commit,
        )


def _default_data_root() -> Path:
    base = os.environ.get("XDG_DATA_HOME")
    return (
        Path(base).expanduser() / "zuaef-supervisor"
        if base
        else Path.home() / ".local" / "share" / "zuaef-supervisor"
    )


def _default_state_root() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    return (
        Path(base).expanduser() / "zuaef-supervisor"
        if base
        else Path.home() / ".local" / "state" / "zuaef-supervisor"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--data-root", type=Path, default=_default_data_root())
    parser.add_argument("--state-root", type=Path, default=_default_state_root())
    parser.add_argument("--codex-bin", default="codex")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap")
    bootstrap_parser.add_argument("--base", default="HEAD")
    bootstrap_parser.add_argument(
        "--expected-remote-url", default=DEFAULT_EXPECTED_REMOTE
    )

    publish_parser = subparsers.add_parser("publish-report")
    publish_parser.add_argument("--worker-root", type=Path, required=True)

    subparsers.add_parser("sync-control")

    run_parser = subparsers.add_parser("run-next")
    run_parser.add_argument("--worker-root", type=Path, required=True)
    run_parser.add_argument("--control-commit", required=True)
    run_parser.add_argument("--base-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = LoopConfig(
        repo=args.repo.resolve(),
        remote=args.remote,
        data_root=args.data_root.expanduser().resolve(),
        state_root=args.state_root.expanduser().resolve(),
        codex_bin=args.codex_bin,
    )
    try:
        if args.command == "bootstrap":
            bootstrap(
                config,
                base=args.base,
                expected_remote_url=args.expected_remote_url,
            )
            return 0
        if args.command == "publish-report":
            publish_report(config, worker_root=args.worker_root)
            return 0
        if args.command == "sync-control":
            return sync_control(config)
        if args.command == "run-next":
            return run_next(
                config,
                worker_root=args.worker_root,
                control_commit=args.control_commit,
                base_commit=args.base_commit,
            )
    except LoopError as exc:
        print(f"supervisor-loop: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
