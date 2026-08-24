BASE_COMMIT: a4a1c71b7713be1d9fa7fde7c4e8a9a61bba3990
REPORT_COMMIT: bf070154315b7af0e582e01f4ceaeffb81744765

# Supervisor Instruction

## Decision
REVISE

## Protected outcome
Complete the real Gate F control → local worker → report round trip without changing production behavior.

## Observed failure / unmet outcome
The previous Gate F control instruction was merged and detected correctly, but the Codex process exited with code 127 because the systemd execution environment could not resolve the `node` interpreter required by the installed Codex executable.

The mechanical launcher correctly published the failure report and did not retry automatically.

## Primary causal hypothesis
The previous worker launch failed only because the systemd service PATH omitted the directory containing `node`.

The local systemd execution environment now resolves node successfully.

With that one condition corrected, an otherwise identical no-op control canary will launch Codex successfully and complete the report round trip.

## Fixed instruction
Perform the Gate F no-op control canary only.

Verify that you are running at the exact authorized BASE_COMMIT.

Make no tracked repository change.

Write the required `.zuaef-supervisor/REPORT.md` stating:
- the observed base commit;
- that no production files were changed;
- whether this bounded canary completed;
- any exact mechanical failure encountered.

Then STOP.

## Hold constant
Production Agent behavior; business plugins; Run Analysis; StepPersistence; runtime-refoundation tasks and experiments; repository code and configuration; business/model semantics; main branch contents.

## Observable acceptance condition
Exactly one fresh worker is launched for this new merged control instruction at the authorized BASE_COMMIT.

The Codex process starts successfully.

The worker makes no tracked repository change.

It writes a contract-complete Supervisor Report whose CONTROL_COMMIT equals this new merged supervisor-control commit and whose WORKER_BASE_COMMIT equals the authorized BASE_COMMIT.

The report is successfully published to supervisor-report.

## Business / evidence guard
Transport/infrastructure evidence only.

No production or business behavior may change.

## Out of scope
Telegram notifier repair; runtime-refoundation work; production code changes; infrastructure redesign; automatic retry; follow-up task selection.

## Stop condition
After the no-change Supervisor Report is written, STOP.

Do not choose or begin another task.
