# TASKS — Coding Agent Work Queue

Rule: execute in order. Do not pre-build later phases.

## T000 — Coach installation
- add this coach pack;
- do not change runtime code;
- confirm paths and repository tests still work.

## T001 — Metrics normalization
- identify existing WCASE record format;
- implement/adapt normalization into the coach metric schema;
- preserve raw provider fields.

Acceptance:
- one command can emit comparable JSON for an existing WCASE record.

## T002 — Wall-clock instrumentation
- add per-request and per-tool timing only where measurement is missing;
- avoid custom telemetry framework.

Acceptance:
- timestamps/latencies can explain where time is spent.

## T003 — WCASE-1 current baseline
- capture current accepted baseline;
- list model-visible capabilities/tools;
- classify every tool call as semantic, mechanical, validation or control.

No code optimization yet.

## T004 — Minimal WCASE-1 path
- compose smallest valid agent path;
- do not begin by copying current default capability stack;
- preserve required ACE/evidence/artifact invariants.

Acceptance:
- business output passes;
- runtime record exists;
- comparison against T003 exists.

## T005 — Remove unjustified WCASE-1 capabilities
For each exposed capability:
- admission evidence or remove from this profile.

Special scrutiny:
- Planning;
- broad Skills;
- ToolOutputLimits if no overflow occurred;
- StepPersistence if not required by the tested production contract.

## T006 — WCASE-2 observation A/B
- run item-by-item baseline;
- implement bounded transport candidate;
- optionally run CodeMode candidate;
- compare.

Do not host-preselect relevance.

## T007 — WCASE-3 convergence
- identify repeated equivalent observations;
- implement narrow unknown-state convergence;
- prove no hallucinated long-term/reorder facts.

## T008 — WCASE-4 bounded revision
- define explicit revision projection;
- exclude full history by default;
- pass current artifact + human delta + bounded authoritative evidence state;
- compare quality and cost.

## T009 — Capability ledger
- classify every current capability:
  REQUIRED_INVARIANT / ADMITTED_PROFILE / EXPERIMENTAL / QUARANTINED / DELETE_CANDIDATE.

## T010 — Non-Writing canary
Choose one real non-Writing slice and reproduce:
- unknown convergence or
- bounded revision or
- minimal loop.

## T011 — Core promotion review
Only mechanisms proven cross-domain may modify Core.

## T012 — Delete zombie architecture
- delete or quarantine superseded runtime path;
- remove stale flags, tests and docs;
- leave exactly one production authority per behavior.

## T013 — Final architecture review
Must answer:
- What is the minimal core?
- Which capabilities are admitted where?
- Why does each model turn exist?
- How do simple tasks stay simple?
- How does complexity progressively appear when needed?

