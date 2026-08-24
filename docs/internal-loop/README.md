# ZUAEF Internal Supervisor Loop

This is the mechanical Git transport between the existing ChatGPT Project
Supervisor and a bounded local Codex worker. The canonical engineering contract
is `zuaef-internal-loop-infra-spec-v0.1/SPEC.md`; this document is operational
guidance only.

## Authority and channels

- `main` remains current repository authority.
- `supervisor-report` carries evidence in `.supervisor/latest/` by direct push.
- `supervisor-control` carries human-authorized instructions in
  `.supervisor/NEXT.md`; executable instructions arrive only through merged
  control PRs.
- An open control PR is a proposal, a merged PR is authorization, and a closed
  PR is not authorized.
- `STOP` and non-executable `ACCEPT` create no control PR.
- Run Analysis remains evidence only. This transport does not change production
  Agent, plugin, StepPersistence, Console, or Run Analysis semantics.

The current repository is public. Reports and attachments must contain only
public-safe engineering evidence. Never place secrets, `.env` files, customer
data, private corpora, private business documents, or private conversations in
the outbox.

## Commands

All commands run from the repository root. Defaults use `origin` and:

```text
~/.local/share/zuaef-supervisor/report
~/.local/share/zuaef-supervisor/control
~/.local/share/zuaef-supervisor/workers/<control-sha>/
~/.local/state/zuaef-supervisor/
```

Bootstrap verifies the expected GitHub remote, ensures both branches from the
chosen current commit, creates/updates the dedicated worktrees, and records the
current control head as the polling baseline. It does not start a worker or
modify the primary worktree:

```bash
uv run python tools/supervisor_loop.py bootstrap \
  --expected-remote-url https://github.com/Rayegoe/zuaef-agent.git
```

Publish an explicit worker outbox (`REPORT.md` and optional `attachments/`)
from `<worker-root>/.zuaef-supervisor/`:

```bash
uv run python tools/supervisor_loop.py publish-report \
  --worker-root /absolute/path/to/worker
```

Poll once manually:

```bash
uv run python tools/supervisor_loop.py sync-control
```

The normal launcher uses the installed Codex CLI's supported non-interactive
form, `codex exec --cd <worker> --sandbox workspace-write --approve-for-me -`.
It materializes the exact merged instruction inside the fresh worktree, passes
the fixed prompt plus exact `NEXT.md`, publishes the report after process exit,
and never asks the worker for another task. A missing report produces only a
mechanical process-failure report; there is no automatic semantic retry.

## User timer

Install and start the outbound 60-second poller only after bootstrap succeeds:

```bash
mkdir -p ~/.config/systemd/user
cp ops/systemd/zuaef-supervisor-sync.service ~/.config/systemd/user/
cp ops/systemd/zuaef-supervisor-sync.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now zuaef-supervisor-sync.timer
systemctl --user status zuaef-supervisor-sync.timer
```

Each service invocation takes the local process lock, polls once, and exits.
The only polling fact is
`~/.local/state/zuaef-supervisor/last-started-control`. It is written before a
worker launch, so a crash is not silently retried. A new Supervisor/human
decision is required.

The shipped service pins the Codex executable path inspected on this machine
(`~/.local/share/pi-node/node-v22.23.1-linux-x64/bin/codex`) and disables the
oneshot start timeout so a bounded worker is not terminated at systemd's normal
service-start limit. If Codex is upgraded or moved, run `command -v codex` and
update the unit before enabling the timer.

Stop or disable the watcher with:

```bash
systemctl --user stop zuaef-supervisor-sync.timer
systemctl --user disable --now zuaef-supervisor-sync.timer
```

Fetch/push failures exit non-zero and preserve the worker outbox. A missing
base commit stops execution. `CONTROL_GAP` means more than one first-parent
control commit is unconsumed; inspect the branch and state rather than skipping
instructions.

## ChatGPT Project instruction amendment

Add the following behavior to the existing `ZUAEF Internal Supervisor`
Project. It does not authorize a second Supervisor:

1. On `继续`, `review latest report`, or equivalent, read the current
   `supervisor-report` head, `REPORT.md`, bounded attachments, current `main`,
   and only relevant verification evidence.
2. Treat the worker report as evidence, separate Observed / Supported inference
   / Hypothesis / Unknown, and choose exactly one decision: `ACCEPT`, `STOP`,
   `REVISE`, or `NEW_ITERATION`.
3. For `STOP` or non-executable `ACCEPT`, create no control PR.
4. For executable `REVISE` or `NEW_ITERATION`, choose exact `BASE_COMMIT` and
   current report commit, create one instruction branch from current
   `supervisor-control`, replace `.supervisor/NEXT.md`, and open exactly one PR
   targeting `supervisor-control`. Do not merge by default; stop and report the
   PR to the human.
5. Do not select a `TASKS.md` item merely because a worker finished, create a
   follow-up iteration without one reproduced unmet outcome and one primary
   causal hypothesis, modify `main` merely to publish control, or give Run
   Analysis execution authority.

## Gate F: live mobile canary

Gate F must be real; unit tests or locally simulated PR/phone behavior do not
satisfy it. After Gates A–E, begin with this safe no-op report from a disposable
worktree at the chosen `main` commit:

```bash
BASE_COMMIT=$(git rev-parse HEAD)
CANARY_ROOT=$(mktemp -d /tmp/zuaef-supervisor-canary.XXXXXX)
git worktree add --detach "$CANARY_ROOT" "$BASE_COMMIT"
mkdir -p "$CANARY_ROOT/.zuaef-supervisor"
```

Write a contract-complete public-safe `REPORT.md` whose
`CONTROL_COMMIT: NONE` and `WORKER_BASE_COMMIT` is the printed full
`BASE_COMMIT`, then publish it:

```bash
uv run python tools/supervisor_loop.py publish-report \
  --worker-root "$CANARY_ROOT"
```

From the phone, open the existing Project and send `继续`. The Supervisor must
create a harmless no-production-change control PR. Review and merge it from the
phone. With no SSH or terminal action, observe:

```bash
systemctl --user status zuaef-supervisor-sync.timer
journalctl --user -u zuaef-supervisor-sync.service --since today
git fetch origin supervisor-report supervisor-control
git log -1 --oneline origin/supervisor-report
git log -1 --oneline origin/supervisor-control
```

Then send `继续` again from the phone. The Supervisor must read the new report
and return `ACCEPT` or `STOP`; no worker may start without another merged
instruction. Remove the disposable worktree only after retaining any required
evidence:

```bash
git worktree remove "$CANARY_ROOT"
```
