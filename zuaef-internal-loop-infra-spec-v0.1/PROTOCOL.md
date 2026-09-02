# Protocol

## Branches

### `supervisor-report`

```text
.supervisor/latest/
  REPORT.md
  WORKTREE.patch       # optional
  attachments/         # optional
```

Latest tree = current report. Git history = archive.

### `supervisor-control`

```text
.supervisor/NEXT.md
```

Only merged control PRs change executable authority.

## REPORT.md

Required mechanical headers:

```text
CONTROL_COMMIT: <full-sha-or-NONE>
WORKER_BASE_COMMIT: <full-sha>
```

Required semantic sections:

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

Host publication must not reinterpret the report.

If a worker exits without a report, the launcher may publish a minimal mechanical failure report containing only observable process/transport facts.

## NEXT.md

Required mechanical headers:

```text
BASE_COMMIT: <full-sha>
REPORT_COMMIT: <full-supervisor-report-sha>
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

## Supervisor PR

For an executable `REVISE` or `NEW_ITERATION`:

```text
read report
→ create branch from supervisor-control
→ replace NEXT.md
→ open PR into supervisor-control
→ stop
```

Recommended title:

```text
[SUPERVISOR] NEW_ITERATION — <subject>
```

The human normally merges from phone.

Local automation never needs to inspect open PRs; it watches only the merged control branch.

## Correlation without a registry

`REPORT_COMMIT` identifies the evidence that caused the instruction.

`CONTROL_COMMIT` identifies the merged instruction that caused the worker run.

Git SHA is sufficient identity. No custom iteration ID is required.
