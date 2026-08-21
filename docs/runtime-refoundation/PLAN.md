# PLAN — Controlled Re-foundation

Current state (2026-08-21): Phase 2 diagnosis, the technique-only A/B, one
reverse-order variance check and both B1/B2 blind judgments are complete.
Control/ON clearly beat Candidate/OFF in B1, while the first runtime delta
was not reproduced in reverse order and is not a causal speed claim. In B2,
the model-owned Candidate selected three IDs from a neutral 18-row catalog
and was preferred to the Host-selected Control. Both B2 drafts nevertheless
failed the no-outside-facts evidence gate, and the Candidate reached the
Harness usage boundary after repeated `save_article` calls. The M002/M008
and irrelevant-material checks passed in B2 but remain separately unclear in
the older B1 review. Neither technique path has earned final production
authority. Phase 2 is therefore **not complete**; the next evidence is a
current-main real-corpus input comparison, and T007 remains deferred. B2 does
not establish that model ownership causes more unsupported completion than
Host selection because the Host-selected draft contained the more severe
invented details. Do not pre-fix Candidate evidence or add Host
technique/scene/schema judgment before the comparison. A repeated
model-owned quality win plus factual-boundary failure would justify a later,
separate factual-boundary experiment.

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

T006-B2 status:
- execution and human judgment recorded under
  `experiments/T006-B2-wcase2-model-owned-technique-selection.md`;
- model-owned Candidate preferred over Host-selected Control;
- no-outside-facts gate failed for both drafts;
- Candidate ended `limit_reached`;
- verdict `REFINE`; no promotion.

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
