# T019 — Run Analysis admission record

Status: `KEEP_CHANGE` for the Console/Analysis profile only. This is not a
production capability admission for the business Agent.

## Reproduced failure

Real subject run:

```text
run_id: 4ecaba058fef4de7bb2300706b17b88c
execution_state: failed
error: Brave search returned HTTP 429
artifacts: 0
```

The deterministic Inspection layer describes the trajectory, but it cannot
decide whether the failure is primarily a transport failure, a late
research-to-persistence transition, or context pressure. That missing causal
interpretation is the concrete reason to admit a separate analysis action.

## Narrow mechanism

Use the existing `build_agent` and `execute_run` seam with a dedicated,
read-only toolset bound to the subject run:

```text
inspect_run
read_run_projection
```

The analysis profile disables Planning, Skills, FileSystem, Knowledge,
ToolOutputLimits and all generalist capabilities. StepPersistence remains on
for the analysis run's own operational facts. The subject run is never
modified.

The terminal Markdown is handed off to:

```text
workspace/analysis/<subject_run_id>/analysis.md
```

An existing `analysis.md` is never silently overwritten.

## Current evidence boundary

The inspection tools are deliberately fact-only. They do not expose raw
prompt/response/tool-result bodies or arbitrary workspace files. Artifact
facts are visible; bounded artifact content remains an explicit unknown until
a receipt-bound reader is separately admitted and tested.

## Next experiment

Run the same subject through `POST /api/runs/{run_id}/analysis`, then compare
the produced hypothesis and one proposed intervention against the human
operator judgment. Do not auto-edit a Skill or rerun the business Agent from
the analysis action.
