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

## Queue state (after T004)

- T000–T004 complete.
- T004 verdict: `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION` — the current
  WCASE-1 path (2 requests / 1 tool call, generic capabilities OFF) is a
  credible minimal candidate; the missing human outcome/evidence verdict
  blocks any optimization conclusion.
- The pre-re-foundation WCASE-1 diagnosis (plan/status cycles, repeated
  claim checks, ~16 requests / ~27 tools) is expired evidence about older
  code. Do not drive new work from it.
- Next: T004G (human verdict gate), then fresh WCASE-2/3/4 work that
  re-discovers current failures instead of inheriting old ones.

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
Status: complete — `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`; see
`experiments/T004-wcase1-minimality-outcome-proof.md`.
- re-derive minimality from the current path, not the historical diagnosis;
- current loop: request 1 writes and submits, request 2 is a
  protocol/presentation continuation with a native explanation;
- `pull_context` unused in this run is an admitted surface fact, not a
  failure;
- code change: NO. Nothing is optimized while the article outcome/evidence
  verdict is unrecorded.

## T004G — Human outcome/evidence verdict gate
Status: pending — owner: the human user. The coding agent must not
self-adjudicate article quality.

- adjudicate the frozen T003/T004 artifact against the WCASE-1 source and
  constraints;
- record explicit `outcome_pass` / `evidence_pass`, or explicitly preserve
  the unknown;
- this gate blocks optimization acceptance (KEEP_CHANGE) and the
  keep-current-path decision, not fresh baseline capture for T006+.

## T005 — WCASE-1 surface admission proof
Status: substantially answered inside T004; close `NO_REMOVAL_JUSTIFIED`
unless T004G surfaces a concrete failure.

For each remaining model-visible surface in the writing profile:
- admission evidence or remove from this profile.

Already settled by composition — do not re-litigate: Planning, Skills,
FileSystem, Knowledge, ToolOutputLimits and generalist are OFF in the
writing profile. Removing an exposed-but-unused tool requires evidence that
the exposure itself costs a decision or degrades output.

## T006 — WCASE-2 semantic-selection boundary
Status: pending — now the primary architectural question.

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

## T007 — WCASE-3 convergence (premise check first)
Status: pending — premise not yet reproduced on current code.

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
