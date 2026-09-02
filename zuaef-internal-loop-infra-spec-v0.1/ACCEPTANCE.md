# Acceptance

All gates must pass.

## Gate A — Scope

Expected implementation footprint:

```text
AGENTS.md
docs/internal-loop/README.md
prompts/internal-loop/CODEX_WORKER_PROMPT.md
tools/supervisor_loop.py
ops/systemd/zuaef-supervisor-sync.service
ops/systemd/zuaef-supervisor-sync.timer
tests/test_supervisor_loop.py
```

No production Agent semantics, business plugin semantics, StepPersistence semantics, or Console/Run Analysis semantics change.

Canonical lint/tests pass.

## Gate B — Worktree isolation

With unrelated uncommitted edits in the primary checkout:

- publishing a report does not change primary branch/status/files;
- control polling does not change primary branch/status/files;
- no stash/reset/clean/checkout is performed there;
- a worker starts in a fresh worktree at exact `BASE_COMMIT`.

## Gate C — Report channel

- worker-created report is committed/pushed to `supervisor-report`;
- tracked worker changes produce an inspectable `WORKTREE.patch`;
- no tracked changes means patch may be absent;
- missing worker report produces only a mechanical failure report;
- no PR is required to publish evidence.

## Gate D — Control channel

- unchanged control head → no worker;
- one new merged instruction → exactly one launch;
- second poll → no duplicate launch;
- missing `BASE_COMMIT` → no launch;
- multiple unconsumed control commits → `CONTROL_GAP`, no silent skip;
- no worker/control operation automatically changes `main`.

## Gate E — Authority

- worker prompt says merged `NEXT.md` is execution authority;
- `AGENTS.md` says `TASKS.md` is backlog/evidence under Supervisor launch;
- worker stops after instruction;
- Supervisor `STOP` creates no control PR;
- non-executable `ACCEPT` creates no control PR.

## Gate F — Live mobile canary

1. Office machine publishes a safe no-op report.
2. From phone, open `ZUAEF Internal Supervisor` and send:
   `继续`
3. Supervisor reads report + current GitHub.
4. Supervisor creates a harmless control PR.
5. Human reviews/merges the PR from phone.
6. Without SSH/manual terminal action:
   - office poller sees control branch;
   - fresh worker launches;
   - worker writes a report;
   - report is pushed automatically.
7. From phone send `继续` again.
8. Supervisor reads the new report and returns `ACCEPT` or `STOP`.
9. No next worker starts without a new merged control instruction.

The canary instruction must make no production/runtime code change.

## Verdict

Use `ACCEPT` only when A–F pass.

Otherwise return `REVISE` naming the smallest failing gate.

After acceptance, STOP. Do not automatically begin runtime-refoundation work.
