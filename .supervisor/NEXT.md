BASE_COMMIT: 164a9140a3e0c467b3f2a3ef38590bbb56cec0c7
REPORT_COMMIT: 43a8213607efe1874ae7c54888792ac50b1aa54e

# Supervisor Instruction

## Decision
NEW_ITERATION

## Protected outcome
Complete the real Gate F GitHub control → local watcher → fresh Codex worker → GitHub report round trip without changing production behavior.

## Observed failure / unmet outcome
The previous live control instruction reached the Codex executable, but the installed Codex CLI rejected the launcher argument combination because --sandbox and --approve-for-me were mutually incompatible.

That reproduced launcher defect has now been corrected and merged into main at BASE_COMMIT 164a9140a3e0c467b3f2a3ef38590bbb56cec0c7.

The local systemd execution environment has also already demonstrated that node resolves successfully.

The remaining unmet outcome is one successful real worker round trip.

## Primary causal hypothesis
With the corrected launcher invocation now running from the updated operational runtime, one new merged no-op control instruction will launch exactly one fresh Codex worker, produce a contract-complete no-change report, and publish that report to supervisor-report.

## Fixed instruction
Perform the Gate F no-op transport canary only.

Verify that the worker is running at the exact authorized BASE_COMMIT.

Make no tracked repository change.

Do not perform implementation work.

Write `.zuaef-supervisor/REPORT.md` with the required Supervisor Report contract, stating:
- the exact observed worker base commit;
- that no tracked production file was changed;
- that this bounded Gate F canary completed successfully, or the exact mechanical failure if it did not;
- that no follow-up task was selected.

Then STOP.

## Hold constant
Production Agent behavior; business plugins; Run Analysis; StepPersistence; runtime-refoundation tasks and experiments; application semantics; GitHub authority semantics; worker isolation; at-most-once control consumption; no automatic retry.

## Observable acceptance condition
Exactly one fresh worker is launched from this newly merged supervisor-control commit.

WORKER_BASE_COMMIT equals:
164a9140a3e0c467b3f2a3ef38590bbb56cec0c7

The worker makes no tracked repository change.

Codex completes without the prior node-path or CLI-argument failures.

A contract-complete Supervisor Report is automatically published to supervisor-report.

Its CONTROL_COMMIT equals this newly merged supervisor-control commit.

No second worker is launched while supervisor-control remains unchanged.

## Business / evidence guard
This run is infrastructure transport evidence only.

No production behavior, runtime benchmark, semantic mechanism, or business output may be modified or evaluated.

Only public-safe engineering facts may be published.

## Out of scope
Telegram notifier repair; Project GitHub-write capability repair; T006/T007; runtime-refoundation; production changes; infrastructure redesign; retries; fallback invocation variants; follow-up task selection.

## Stop condition
After writing the one no-change Supervisor Report, STOP.

Do not choose or begin another task.
