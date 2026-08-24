BASE_COMMIT: a4a1c71b7713be1d9fa7fde7c4e8a9a61bba3990
REPORT_COMMIT: bba4e27f17294afea21cc5433f29359d234f8dab

# Supervisor Instruction

## Decision
NEW_ITERATION

## Protected outcome
Prove the real Gate F GitHub control PR → human merge → local watcher → fresh Codex worker → GitHub report round trip without changing production behavior.

## Observed failure / unmet outcome
The local → supervisor-report → GitHub → Project Supervisor path is observed working, but the merged control instruction → automatic local worker → report publication half has not yet been exercised in the real environment.

## Primary causal hypothesis
If one harmless merged NEXT.md is published to supervisor-control, the installed local watcher will detect exactly one new control commit, launch exactly one fresh Codex worker at the authorized BASE_COMMIT, and that worker will publish a matching no-change Supervisor Report.

## Fixed instruction
Perform the Gate F no-op control canary only.

Inspect the current HEAD and the internal-loop authority files needed to establish that you are running at the exact authorized base commit.

Make no code, configuration, documentation, test, task, branch, or runtime-semantic changes.

Do not run a runtime-refoundation experiment.

Write the required `.zuaef-supervisor/REPORT.md` stating:
- the observed base commit;
- that no production files were changed;
- whether this bounded canary completed;
- any exact mechanical failure encountered.

Then STOP.

## Hold constant
Production Agent behavior; business plugins; Run Analysis; StepPersistence; runtime-refoundation tasks and experiments; repository code and configuration; model/business semantics; main branch contents.

Do not modify any tracked repository file.

## Observable acceptance condition
Exactly one fresh worker is launched from this merged control instruction at BASE_COMMIT `a4a1c71b7713be1d9fa7fde7c4e8a9a61bba3990`.

It makes no tracked repository change.

It writes a contract-complete Supervisor Report whose CONTROL_COMMIT equals the merged supervisor-control commit and whose WORKER_BASE_COMMIT equals this BASE_COMMIT.

The report is then published to supervisor-report and becomes readable by the Project Supervisor.

## Business / evidence guard
This is transport/infrastructure evidence only.

No production behavior, business artifact, runtime benchmark, or semantic mechanism may be changed or evaluated as part of this canary.

The report must contain only public-safe engineering facts.

## Out of scope
Any runtime-refoundation task; T006/T007 or later backlog work; production code changes; Telegram notifier repair; infrastructure redesign; retries; follow-up iteration selection; promotion of unrelated work.

## Stop condition
After the no-change Supervisor Report has been written for this one control instruction, STOP.

Do not choose or begin another task.
