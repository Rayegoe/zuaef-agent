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

## Queue state (after T006-B4 human judgment)

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
- T006-B2 human judgment is complete. Anonymous A was the model-owned
  Candidate and was preferred over anonymous B, the Host-selected Control.
  M002 handling, M008 priority and M005/M006/M009 exclusion passed. The
  no-outside-facts check failed for both drafts: Control added several
  unsupported concrete scene facts and Candidate added lighter unsupported
  scene detail. Candidate also reached the Harness usage boundary after
  repeated `save_article` calls. Verdict: `REFINE`; no promotion.
- Phase 2 is not complete. T007 is deferred until the observation design is
  justified by quality and runtime data.
- The B2-locked next step was the smallest current-`main` real-corpus
  comparison using one fixed
  task/model/EPUB corpus across Host-selected, technique-off and model-owned
  input modes. Measure the actual section distribution and tail truncation;
  do not modify EPUB ingestion/retrieval, pre-fix Candidate evidence or add
  Host technique/scene/schema judgment before this converges. B2 alone does
  not prove model ownership causes more unsupported completion because the
  Host-selected draft contained the more severe invented details.
- T006-B3 execution is complete on current `main` with the real
  `REAL-AGENT-TRUST-1` fixture. All three modes completed. First-request
  task-material / human-learning / EPUB characters were identical; Host added
  995 technique-body characters, OFF added 0, and model-owned added 3,187
  catalog characters. Only the model-owned catalog tail was truncated. The
  model selected zero technique IDs; OFF made one additional `pull_context`
  observation. See
  `experiments/T006-B3-real-corpus-technique-ownership-abc.md`.
- T006-B3 blind judgment is complete: `Z > X > Y`, mechanically revealed as
  technique OFF > model-owned eager catalog > Host-selected. The reviewer
  judged OFF best at rebuilding a material relationship rather than repeating
  `understand -> summarize -> framework -> conclude`. Evidence remained
  `unclear` because the full desk pack was not available in the blind packet.
  Verdict: `REFINE`; no production promotion. See
  `experiments/T006-B3-human-judgment.md`.
- B1, B2 and B3 have different comparative winners. Do not turn the latest
  human preference into a global OFF rule. The next smallest experiment is a
  benchmark-only lazy model-owned catalog: initial context identical to OFF;
  the model may choose to observe the neutral catalog and then retrieve exact
  technique IDs. This tests the reproduced eager-catalog context cost without
  adding Host semantic judgment. T007 remains deferred.
- T006-B4 human judgment is complete. The mapping was P = model-lazy and Q =
  frozen technique OFF; the reviewer chose `Q > P`. Both drafts failed the
  evidence gate. P confused the PI execution framework with evaluation
  authorship and strengthened system importance into an exclusive cause; Q
  generalized one benchmark, strengthened jointly influencing layers into
  individually necessary conditions, and blurred traceable execution with
  organizational responsibility. The lazy mode exposed two optional technique
  actions, called neither, lost quality and did not improve evidence. Verdict:
  `REVERT`; its benchmark code/profile/tests were deleted. Production remains
  unchanged and OFF is only the frozen real-case reference, not a global rule.
  See `experiments/T006-B4-human-judgment.md`.
- The next T006 causal boundary is shared evidence interpretation, not another
  technique mode: preserve attribution roles, source/benchmark scope, logical
  strength and the responsibility subject. Do not add a claim checker, Host
  semantic gate or reward model. The agent may record the benchmark verdict
  but must not write an authoritative `learning/cases/*/human-review.md`; any
  durable lesson promotion must cross the existing human-authored gate. T007
  remains deferred until this evidence-boundary experiment is specified and
  reviewed one causal change at a time.

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
T006-B2 execution and blind judgment complete with verdict `REFINE`. See
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
- Candidate/A was preferred to Control/B, but both failed the
  no-outside-facts gate;
- Candidate reached `limit_reached` after producing an artifact, so the
  terminal/runtime failure remains part of the verdict;
- neither the Host selector nor the current model-owned seam has earned final
  production authority.

## T007 — WCASE-3 convergence (premise check first)
Status: deferred — Phase 2 has not exited; do not run until the current-main
real-corpus input comparison has converged and the selected observation
design is justified.

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
