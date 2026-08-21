# PLAN — Controlled Re-foundation

## Phase 0 — Freeze and instrument

Goal:
- establish reproducible current behavior.

Actions:
- do not redesign runtime yet;
- collect current WCASE records;
- add per-request/tool wall-clock where feasible;
- normalize run metrics into a comparable JSON record.

Exit:
- WCASE baseline metrics are inspectable.

## Phase 1 — Minimal Loop Canary

Target:
- WCASE-1.

Build the thinnest path from:
- PydanticAI;
- required Writing domain surface;
- artifact/evidence settlement needed for correctness.

Start from zero optional Harness capabilities unless a dependency is technically required.

Compare to current production path.

Exit:
- accepted WCASE-1 outcome;
- materially smaller trajectory, or a recorded zero-change proof
  (`CURRENT_PATH_ALREADY_MINIMAL` /
  `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`);
- no new framework.

## Phase 2 — Observation design

Target:
- WCASE-2.

First audit the current host preselection in `build_writer_context()`
(lexical relevance ranking, excerpt bounding, technique tags, experience
selection) before choosing among transport designs.

Experiment with:
- regular item-by-item calls;
- bounded batch transport;
- optionally CodeMode.

The model must retain semantic selection authority.

Exit:
- selected observation design justified by quality + runtime data.

## Phase 3 — Epistemic convergence

Target:
- WCASE-3.

Implement the narrowest mechanism by which unchanged evidence reaches a stable `unknown/unsupported` state.

Avoid creating a global convergence framework.

Exit:
- no evidence fabrication;
- no unbounded equivalent re-check loop;
- feasible artifact completed.

## Phase 4 — Delta revision

Target:
- WCASE-4.

Prove current revision boundedness on a fresh trace first: the current path
already revises through a fresh run with bounded inputs and no
message-history replay.

Define bounded revision state.

Compare:
- history reconstruction;
- artifact + delta + evidence state.

Exit:
- revision quality passes;
- context/token growth materially controlled.

## Phase 5 — Capability re-admission

For each previously default capability:
- apply admission protocol;
- admit only to necessary profiles;
- keep global default minimal.

## Phase 6 — Cross-domain transfer

Run at least one:
- negotiation unknown-state test;
- budget revision;
- WordPress revision;
- research conflict case.

Only now promote genuinely cross-domain runtime mechanisms.

## Phase 7 — Authority consolidation

- move production authority;
- quarantine/delete obsolete paths;
- remove stale flags/docs/tests;
- update AGENTS.md;
- update architecture guide and README only after runtime proof.

