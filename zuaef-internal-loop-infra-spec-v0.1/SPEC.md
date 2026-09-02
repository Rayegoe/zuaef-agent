# SPEC — ZUAEF Four-Component Internal Improvement Loop Infrastructure v0.1

**Status:** READY TO FREEZE  
**Date:** 2026-08-24  
**Repository:** `Rayegoe/zuaef-agent`  
**Baseline inspected:** `main@1b0e46bbf5e67de00a194c3e5b68638b230434f7`

## 1. Protected outcome

Close the existing Project + GitHub + Worker + Console improvement loop with the smallest reliable bidirectional handoff infrastructure.

The result must let a human operate the loop remotely from phone/web while preserving the existing authority boundaries:

- ChatGPT Project = Supervisor.
- GitHub = current repository authority and handoff bus.
- Codex/ZUAEF worker = bounded executor.
- Console/Run Analysis = Observation Plane.
- Human = final authorization authority.

The infrastructure must remove manual copy/paste transport without creating a second Supervisor, workflow engine, self-modifying production Agent, or semantic host controller.

## 2. Current missing capability

Today:

```text
local worker
→ terminal/workspace report
→ human copy/paste
→ Project Supervisor
→ chat instruction
→ human copy/paste
→ local worker
```

The missing mechanism is mechanical transport in both directions.

A second reproduced requirement is local concurrency isolation: unrelated uncommitted work can coexist in the primary checkout. Report publication and instruction pickup must not switch/reset/stash/clean that checkout.

## 3. Target loop

```text
local worker finishes
→ local completion hook publishes report
→ GitHub supervisor-report branch
→ human activates Project from phone/web
→ Supervisor reads report + current GitHub
→ exactly one decision
→ if executable: Supervisor opens control PR
→ human reviews/merges PR from phone
→ GitHub supervisor-control branch advances
→ local watcher detects merged instruction
→ fresh isolated Codex worktree executes NEXT.md
→ worker writes report and stops
→ report is automatically pushed
```

`STOP` and non-executable `ACCEPT` create no control PR.

## 4. v0.1 product boundary

v0.1 retains one human activation step:

```text
human sends "继续" / "review latest report" in the existing Project
```

The Project can be used from phone/web, so the operator does not need to be in the office.

v0.1 does not assume:

```text
GitHub push → automatically wake this exact ChatGPT Project conversation
```

Do not replace that missing trigger with a second API-launched Supervisor.

## 5. Non-goals

Do not implement:

- automatic ChatGPT Project wakeup;
- a second Supervisor service;
- workflow/state-machine framework;
- task database or queue service;
- custom event bus;
- report/instruction registry;
- parallel handoff hashes/manifests;
- long-term memory;
- automatic worker retry;
- automatic next `TASKS.md` selection;
- automatic worker-code merge into `main`;
- production ZUAEF self-modification;
- Console/Run Analysis code-change authority;
- inbound webhook/tunnel on the office workstation;
- self-hosted GitHub Actions runner;
- branch-protection redesign;
- confidential/customer-data transport through the current public repository.

## 6. Authority

### Supervisor

Owns protected outcome, evidence interpretation, causal hypothesis, acceptance and one of:

`ACCEPT` / `STOP` / `REVISE` / `NEW_ITERATION`.

For an executable decision it writes one bounded instruction.

### Human

Merging the Supervisor control PR is the default v0.1 authorization event.

The human may reject/close/revise instead.

### GitHub

Owns current code facts and handoff history using native commits/branches/PRs.

No parallel workflow ID is needed.

### Worker

Executes the exact merged instruction only. It may choose implementation details within scope but may not redefine objective, acceptance, next task or promotion.

### Console / Run Analysis

Remains evidence only. v0.1 must not modify its semantic authority.

## 7. GitHub bus

Create two dedicated branches:

```text
supervisor-report
supervisor-control
```

### 7.1 Report branch

Direction:

```text
local → Supervisor
```

Canonical tree:

```text
.supervisor/latest/
  REPORT.md
  WORKTREE.patch       # optional, tracked worker diff only
  attachments/         # optional, explicitly supplied bounded evidence
```

The latest branch tree is the current report. Git history is the archive.

No report PR is required because a report is evidence, not authority.

### 7.2 Control branch

Direction:

```text
Supervisor/human → local
```

Canonical tree:

```text
.supervisor/NEXT.md
```

A new executable instruction reaches `supervisor-control` only through a Supervisor PR.

### 7.3 PR semantics

```text
open control PR = Supervisor proposal
merged control PR = human-authorized worker instruction
closed PR = not authorized
```

Local automation watches only `supervisor-control`, not open PRs.

### 7.4 Main

No report/control operation may:

- merge into `main`;
- switch the operator's primary worktree branch;
- reset, clean, stash or rebase the primary worktree.

## 8. Minimal Markdown contracts

These are human-readable contracts, not a workflow schema.

### REPORT.md

Only two fixed correlation headers are required:

```text
CONTROL_COMMIT: <full sha or NONE>
WORKER_BASE_COMMIT: <full sha>
```

Required sections:

```markdown
# Supervisor Report

## Subject
## Outcome
## Protected outcome
## What changed
## What stayed unchanged
## Observed result
## Acceptance result
## Evidence / artifacts
## Files changed
## Unknowns / conflicts
## Worker stop
```

The host publisher transports this content and must not invent a semantic verdict.

If a worker process exits without a report, the launcher may create a mechanical failure report containing only observed transport/process facts.

### NEXT.md

Only two fixed correlation headers are required:

```text
BASE_COMMIT: <full sha>
REPORT_COMMIT: <full supervisor-report sha>
```

Required sections:

```markdown
# Supervisor Instruction

## Decision
## Protected outcome
## Observed failure / unmet outcome
## Primary causal hypothesis
## Fixed instruction
## Hold constant
## Observable acceptance condition
## Business / evidence guard
## Out of scope
## Stop condition
```

Do not add task-state JSON, workflow databases, sequence registries or content hashes.

## 9. Repository implementation footprint

Implement the smallest surface:

```text
AGENTS.md
docs/internal-loop/README.md
prompts/internal-loop/CODEX_WORKER_PROMPT.md
tools/supervisor_loop.py
ops/systemd/zuaef-supervisor-sync.service
ops/systemd/zuaef-supervisor-sync.timer
tests/test_supervisor_loop.py
```

Small packaging/test adjustments are allowed only if required by existing repo conventions.

Do not modify production runtime, business plugins, Agent composition, StepPersistence or Console/Run Analysis semantics.

## 10. AGENTS authority amendment

Add one narrow rule:

> When a worker is launched from a merged `.supervisor/NEXT.md`, that exact instruction is the worker's execution authority. `TASKS.md` remains backlog/evidence. Completing the authorized instruction does not authorize the next task.

Do not otherwise rewrite runtime-refoundation doctrine.

## 11. One mechanical tool

Implement:

```text
tools/supervisor_loop.py
```

Prefer Python stdlib and existing dependencies.

Bounded commands:

```text
bootstrap
publish-report
sync-control
run-next
```

Do not create a framework package unless implementation evidence proves one file is insufficient.

## 12. Local isolation

Default roots:

```text
/home/barry/zuaef-agent
    primary operator worktree

~/.local/share/zuaef-supervisor/report
    supervisor-report worktree

~/.local/share/zuaef-supervisor/control
    supervisor-control worktree

~/.local/share/zuaef-supervisor/workers/<control-sha>/
    isolated worker worktree

~/.local/state/zuaef-supervisor/
    local mechanical polling state
```

Paths may be configurable without introducing a project-wide config framework.

## 13. Bootstrap

`bootstrap` must:

1. verify the target Git remote;
2. create/ensure `supervisor-report` from the chosen current Git commit;
3. create/ensure `supervisor-control` from the same commit;
4. create/update dedicated report/control worktrees;
5. create the local state directory;
6. print/install guidance for the user-level timer.

It must not:

- touch the primary worktree state;
- start a worker;
- create fake reports;
- create fake instructions;
- modify `main`.

## 14. Report publication

`publish-report` operates only on the dedicated report worktree.

It:

1. fetches `supervisor-report`;
2. updates the report worktree to remote head;
3. replaces `.supervisor/latest/` with the explicit worker outbox;
4. when tracked worker changes exist, generates `WORKTREE.patch` against `WORKER_BASE_COMMIT`;
5. commits;
6. pushes `supervisor-report`.

Do not recursively copy the full worker worktree.

Do not auto-copy ignored/untracked files except explicit `.zuaef-supervisor/attachments/`.

A patch is evidence, not promotion.

## 15. Control polling

Use outbound mechanical polling rather than inbound webhook.

Default:

```text
systemd --user timer
→ every 60 seconds
→ supervisor_loop.py sync-control
→ process exits
```

The cadence is operational only.

Use one local process lock so only one watcher/worker launch happens at once.

Store exactly one polling fact:

```text
~/.local/state/zuaef-supervisor/last-started-control
```

No repository/model-facing state is required.

## 16. Instruction pickup

`sync-control`:

1. fetches `supervisor-control`;
2. reads remote head;
3. no-ops if it equals `last-started-control`;
4. refuses to silently skip multiple unconsumed control commits (`CONTROL_GAP`);
5. reads exact `.supervisor/NEXT.md`;
6. parses the required `BASE_COMMIT`;
7. normal-fetches that commit if needed;
8. stops if unavailable;
9. records the new control head before launch to prevent duplicate automatic execution;
10. creates a fresh isolated worker worktree at exactly `BASE_COMMIT`;
11. invokes `run-next`.

No automatic semantic retry is added.

If a crash occurs after a control commit has been recorded as started, human/Supervisor decides whether to issue another instruction.

## 17. Worker launch

During implementation, inspect the installed Codex CLI and use its currently supported non-interactive invocation. Do not hardcode obsolete flags from this spec.

The launcher passes:

- `prompts/internal-loop/CODEX_WORKER_PROMPT.md`;
- exact merged `NEXT.md`;
- isolated worktree as working directory.

The worker must write:

```text
.zuaef-supervisor/REPORT.md
```

Optional bounded evidence:

```text
.zuaef-supervisor/attachments/
```

After worker exit, launcher calls `publish-report`.

The worker stops. The launcher does not ask it for another task.

## 18. Worker code state

v0.1 does not require every failed/experimental result to become a normal code commit.

If tracked files changed, the report channel may publish `WORKTREE.patch`.

This allows the Supervisor to inspect exact implementation evidence without promoting it or contaminating `main`.

If a later decision needs accepted code to become repository authority, use the normal engineering commit/PR flow separately.

## 19. Supervisor activation

Stable mobile/web trigger:

```text
继续
```

On activation the Project Supervisor must:

1. read latest `supervisor-report` head and `REPORT.md`;
2. read current `main` and only relevant evidence needed to verify;
3. separate Observed / Supported inference / Hypothesis / Unknown;
4. protect the business/engineering outcome;
5. choose exactly one decision.

For `STOP` / non-executable `ACCEPT`:
- no control PR.

For executable `REVISE` / `NEW_ITERATION`:
1. choose exact `BASE_COMMIT`;
2. use exact report commit as `REPORT_COMMIT`;
3. create one instruction branch from current `supervisor-control`;
4. write one `NEXT.md`;
5. open one PR targeting `supervisor-control`;
6. stop.

Do not merge by default in v0.1.

If the human explicitly asks the Supervisor to merge an already-reviewed control PR and the connected environment permits it, that explicit request may authorize the merge.

## 20. Human remote operation

Normal phone loop:

```text
1. open ZUAEF Internal Supervisor Project
2. send "继续"
3. review Supervisor decision
4. if control PR exists, review PR on phone
5. merge if approved
6. office poller automatically starts fresh worker
7. worker automatically publishes report
8. later send "继续" again
```

No office terminal interaction is required in the normal path.

## 21. Console relationship

Run Analysis remains the Observation Plane.

v0.1 does not change:

- analysis model/tool boundary;
- RunFacts;
- analysis projection;
- analysis persistence;
- production Agent tool surface.

A report may reference or explicitly attach bounded `analysis.md` evidence.

A direct Console "publish to Supervisor" adapter is a possible later transport convenience, not required by v0.1.

## 22. Public repository boundary

The current repo is public.

Therefore the report/control branches may contain only public-safe engineering-loop material.

Never automatically publish:

- secrets/tokens;
- `.env`;
- customer data;
- private corpora;
- private business documents;
- private conversations;
- arbitrary home-directory files.

If confidential business-run transport is later required, move the same protocol to an authorized private GitHub repository. Do not add encryption machinery to make a public branch act private.

## 23. Failure behavior

Prefer explicit stop over retry/fallback stacks.

### Git push/fetch failure
Exit non-zero and preserve local evidence. Human may retry transport.

### Missing base commit
Do not execute. Do not substitute a different base.

### Dirty primary worktree
Ignore for transport; never mutate it.

### Missing worker report
Publish a minimal mechanical process/transport failure report if possible. Do not fabricate semantic interpretation.

### Multiple pending control commits
Stop with `CONTROL_GAP`; do not skip.

### GitHub write unavailable in the actual mobile Project experience
Remote-control acceptance is not complete. Do not silently create a second Supervisor service as a workaround.

## 24. Removal criteria

Disable/remove this mechanism if it:

- duplicates worker launches;
- mutates the primary worktree;
- launches without a merged control instruction;
- lets worker select the next task;
- publishes confidential data;
- requires a second semantic Supervisor;
- materially worsens reliability relative to manual handoff.

## 25. Acceptance

Implementation is accepted only when all gates in `ACCEPTANCE.md` pass, including one live phone→Supervisor→PR→phone merge→office worker→report canary.

Unit tests alone are insufficient.

## 26. Completion boundary

When infrastructure acceptance passes:

- record evidence;
- STOP;
- do not automatically start T006/T007 or another runtime-refoundation item;
- return to the Project Supervisor for the next explicit decision.
