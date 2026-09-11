# 11 — Implementation Tasks

Execute in causal order.

## P0 — Baseline

### T001
Read current `AGENTS.md`, Gateway runner/service/renderer, web projector/readers, relevant tests.

### T002
Capture current behavior: ACK + fixed 25/50 pings, one thread per checkpoint, no progress token fields.

## P1 — Pure schedule

### T003
Implement smallest pure helper for checkpoint calculation.

Do not create a scheduler framework/class hierarchy.

### T004
Add validation for first/second seed values.

### T005
Add schedule tests.

## P2 — One-thread watchdog

### T006
Change watchdog registry from list of Events per run to one stop Event per run.

### T007
Implement one loop with absolute monotonic deadlines.

### T008
Add stop/settle race checks.

### T009
Ensure stop cleanup on all run exits.

## P3 — Progress facts

### T010
Add unique tool-call count.

### T011
Keep completed request count/current-tool semantics.

### T012
Expose activity internally for stale-ping suppression.

## P4 — Shared live usage

### T013
Inspect actual pinned PydanticAI `RequestUsage` fields.

### T014
Extend shared projector response-usage extraction for cache fields when public API supports them.

### T015
Implement conservative settled snapshot aggregate.

### T016
Preserve receipt aggregate priority.

## P5 — Renderer

### T017
Implement compact token formatter.

### T018
Extend progress renderer to requests/tools/current tool/input/cache/output/elapsed.

### T019
Keep ACK and terminal renderers unchanged.

## P6 — Config/docs

### T020
Keep existing env variable names.

### T021
Document arithmetic seed semantics and 0-disable behavior.

### T022
Update `.env.example` / existing ops docs where appropriate.

## P7 — Verification

### T023
Run focused Gateway renderer/service/projector tests.

### T024
Run full regression and lint policy.

### T025
Update BUILD_MANIFEST surgically.

## P8 — Deployment

### T026
Deploy with existing OPi5 procedure.

### T027
Restart existing Feishu Gateway because imported Python changed.

### T028
Run real >3-minute Feishu canary.

### T029
Use `/inspect` and compare final usage against last progress usage.

### T030
Produce implementation report and local commit.
