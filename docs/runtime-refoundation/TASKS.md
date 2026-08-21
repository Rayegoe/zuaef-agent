# TASKS — Coding Agent Work Queue

Rule: execute in order. Do not pre-build later phases.

Every task is a failure hypothesis, not a contract. Before executing a task,
re-derive its failure premise from current code and a fresh trace; the queue
can lag behind evidence. If the premise no longer reproduces, close the task
with a recorded verdict and zero code change. Zero-code verdicts are
first-class results:

- `CURRENT_PATH_ALREADY_MINIMAL`
- `NO_REMOVAL_JUSTIFIED`
- `PROBLEM_NOT_REPRODUCED`
- `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`

Never fabricate an outcome/evidence verdict to unblock a task.

## Queue state (after T006-A / T006-B2 execution)

- T000–T005 complete.
- T004/T004G final verdict: `CURRENT_PATH_ALREADY_MINIMAL` — the current
  WCASE-1 path (2 requests / 1 tool call, generic capabilities OFF) produced
  an accepted article and preserved the imperfect source evidence. No
  one-request terminal mechanism is introduced merely to improve metrics.
- The pre-re-foundation WCASE-1 diagnosis (plan/status cycles, repeated
  claim checks, ~16 requests / ~27 tools) is expired evidence about older
  code. Do not drive new work from it.
- T005 final verdict: `NO_REMOVAL_JUSTIFIED` — no current failure is caused by
  the remaining WCASE-1-visible surfaces; unused exposure alone is not a
  removal reason.
- T006-A diagnosis complete: `SEMANTIC_PRESELECTION_REPRODUCED /
  OUTCOME_IMPACT_UNMEASURED`.
- T006-B1 execution, one reverse-order variance check and the blind quality
  review are complete: Control/ON (anonymous A) clearly beat Candidate/OFF
  (anonymous B) on the target editorial outcome. The first pair's runtime
  delta was not reproduced in reverse order and is not a causal speed claim.
  The M002/M008 conflict and irrelevant-material evidence subchecks were not
  separately marked pass/fail and remain `unclear`.
- T006-B2 execution is recorded: the model-owned Candidate saw a neutral
  18-row ACE catalog and selected three IDs different from the Control's
  Host-selected three. It produced an artifact but reached the Harness usage
  boundary after repeated `save_article` calls; quality and narrow evidence
  review are pending. This is a runtime observation, not a promotion verdict.
- Phase 2 is not complete. T007 is deferred until the observation design is
  justified by quality and runtime data.
- Next: record the T006-B2 blind quality/evidence judgment. Do not start an
  experience-selection experiment, thinking A/B or T007 before that gate is
  adjudicated.

## T000 — Coach installation
Status: complete (ADR-RF-004).
- add this coach pack;
- do not change runtime code;
- confirm paths and repository tests still work.

## T001 — Metrics normalization
Status: complete.
- identify existing WCASE record format;
- implement/adapt normalization into the coach metric schema;
- preserve raw provider fields.

Acceptance:
- one command can emit comparable JSON for an existing WCASE record.

## T002 — Wall-clock instrumentation
Status: complete.
- add per-request and per-tool timing only where measurement is missing;
- avoid custom telemetry framework.

Acceptance:
- timestamps/latencies can explain where time is spent.

## T003 — WCASE-1 current baseline
Status: complete — baseline frozen in
`experiments/T003-wcase1-current-baseline.md`.
- capture current accepted baseline;
- list model-visible capabilities/tools;
- classify every tool call as semantic, mechanical, validation or control.

No code optimization happened in T003.

## T004 — WCASE-1 minimality + outcome proof
Status: complete — final verdict `CURRENT_PATH_ALREADY_MINIMAL`; see
`experiments/T004-wcase1-minimality-outcome-proof.md`.
- re-derive minimality from the current path, not the historical diagnosis;
- current loop: request 1 writes and submits, request 2 is a
  protocol/presentation continuation with a native explanation;
- `pull_context` unused in this run is an admitted surface fact, not a
  failure;
- human outcome/evidence gate: `outcome_pass=true`, `evidence_pass=true`.
- code change: NO. The current path is kept as minimal enough for this
  profile.

## T004G — Human outcome/evidence verdict gate
Status: complete — human verdict recorded in the T004 experiment record.

- adjudicate the frozen T003/T004 artifact against the WCASE-1 source and
  constraints;
- explicit values recorded: `outcome_pass=true`, `evidence_pass=true`;
- accepted reference: `final(3).md` / local canonical `final.md`;
- rejected comparator: `final-revised.md` as a prose-quality regression.

## T005 — WCASE-1 surface admission proof
Status: complete — `NO_REMOVAL_JUSTIFIED`; see
`experiments/T005-wcase1-surface-admission-proof.md`.

For each remaining model-visible surface in the writing profile:
- admission evidence or remove from this profile.

Already settled by composition — do not re-litigate: Planning, Skills,
FileSystem, Knowledge, ToolOutputLimits and generalist are OFF in the
writing profile. Removing an exposed-but-unused tool requires evidence that
the exposure itself costs a decision or degrades output.

## T006 — WCASE-2 semantic-selection boundary
Status: T006-A diagnosis complete; T006-B1 A/B execution, reverse variance
check and blind quality verdict complete, with evidence subchecks unclear;
T006-B2 execution recorded with blind quality/evidence verdict pending. See
`experiments/T006-wcase2-observation-proof.md`,
`experiments/T006-B1-wcase2-technique-ownership-ab.md` and
`experiments/T006-B2-wcase2-model-owned-technique-selection.md`.

The question is not transport shape first. It is:

> Did reducing model turns move semantic selection into host heuristics?

Step 1 — audit current host preselection in `build_writer_context()`
(`plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py`):
- per-paragraph lexical `_relevance` ranking;
- bounded per-material excerpt selection;
- keyword-driven `_technique_tags`;
- lexically selected past human review (`_experience_section`).

With the multi-material case, enumerate what the host decides and what it
drops; measure whether dropped content was materially relevant to the
accepted article.

Step 2 — A/B observation designs:
- item-by-item regular tool calls;
- bounded batch transport;
- CodeMode only if the experiment specifically tests it.

Measure: quality, requests, total input, latency, selection correctness.

Do not host-preselect relevance. Efficiency bought with host-side semantic
selection is a regression (SPEC RUNTIME-5), not a win.

Current T006-B2 boundary:
- Control keeps production `_technique_tags()` and its 3/18 projection;
- Candidate exposes only the existing 18-row metadata catalog and one
  mechanical ID-addressed batch retrieval action;
- the model selected `ex-scene-pause-001`, `ex-prose-object-001` and
  `ex-final-quote-001` in the recorded run;
- Candidate reached `limit_reached` after producing an artifact, so the
  terminal/runtime behavior must remain part of the human review record;
- no promotion, experience follow-up or T007 follows until the narrow gate
  is complete.

## T007 — WCASE-3 convergence (premise check first)
Status: deferred — Phase 2 has not exited; do not run until T006-B2 has a
quality/evidence verdict and the selected observation design is justified.

- the historical repeated `check_claim` loop is not exposed by the current
  writing surface (`pull_context`, `save_article` only);
- run the fresh case first; if repeated equivalent observation does not
  reproduce, close `PROBLEM_NOT_REPRODUCED`;
- otherwise implement narrow unknown-state convergence and prove no
  hallucinated long-term/reorder facts.

## T008 — WCASE-4 bounded revision (premise check first)
Status: pending — current code may already satisfy the contract.

- current revision already passes current article + human feedback + bounded
  writer context through a fresh `execute_run()` with no message-history
  replay;
- first produce a fresh WCASE-4 proof: context growth draft→revision,
  history-search / `read_tool_result` usage, revision quality;
- if boundedness holds, close `PASS` with zero code change;
- otherwise make the narrowest change toward SPEC RUNTIME-7.

## T009 — Capability ledger
Status: pending.
- classify every current capability:
  REQUIRED_INVARIANT / ADMITTED_PROFILE / EXPERIMENTAL / QUARANTINED / DELETE_CANDIDATE.

Include the global `AgentSettings` defaults
(`src/zuaef_agent/config.py`: planning, skills, filesystem, knowledge,
tool-output limits and step persistence default to True). For each default
answer: platform availability or default production admission?
Writing-profile OFF does not settle the generic default.

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
