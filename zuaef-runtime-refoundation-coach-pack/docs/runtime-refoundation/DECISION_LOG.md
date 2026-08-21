# Decision Log

Append decisions. Do not rewrite history.

## ADR-RF-001 — Preserve repository, re-found runtime path

Decision:
- no greenfield rewrite;
- retain validated assets;
- construct minimal runtime path from zero optional capabilities;
- re-admit complexity through benchmarks.

Reason:
- current failure is architectural assumption/runtime fitness, not unusable codebase state.

Status: accepted by coach pack.

## ADR-RF-002 — Writing is canary, not architecture owner

Decision:
- WCASE exposes runtime failures;
- Writing-specific fixes remain domain-local unless demonstrated cross-domain.

Status: accepted by coach pack.

## ADR-RF-003 — Capability availability is not production admission

Decision:
- upstream existence/reuse never justifies default model exposure.

Status: accepted by coach pack.

## ADR-RF-004 — T000 Coach pack installed

Decision:
- coach pack installed per INSTALL.md (skill, docs/runtime-refoundation, prompts, templates);
- AGENTS.md amended with runtime-complexity rules and coach routing per AGENTS_AMENDMENT.md;
- BUILD_MANIFEST.json regenerated; no runtime code changed.

Evidence:
- pack verified against its own MANIFEST.json before install (29/29 sha256);
- skill script tests pass (1/1);
- repository suite after install: 599 passed, 2 pre-existing failures in tests/test_production_writing.py caused by uncommitted in-flight edits to examples/production_writing.py, unrelated to this installation.

Status: accepted; T000 complete. Next: T001 metrics normalization.

## ADR-RF-005 — Recalibrate task queue and taxonomy after T003/T004 evidence

Decision:
- T003 shows the current WCASE-1 path at 2 requests / 1 tool call with
  generic capabilities OFF; the pre-re-foundation ~16-request diagnosis is
  expired evidence and must not drive new work;
- T004 closes as `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`: the current path
  is a credible minimal candidate, and no runtime change is justified while
  the article outcome/evidence verdict is unrecorded;
- TASKS.md reframed accordingly: proof-first tasks with zero-code verdicts
  (`CURRENT_PATH_ALREADY_MINIMAL`, `NO_REMOVAL_JUSTIFIED`,
  `PROBLEM_NOT_REPRODUCED`, `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`), a
  human-owned T004G verdict gate, premise checks before T007/T008
  implementation, and availability-vs-admission scrutiny of global
  `AgentSettings` defaults in T009;
- T006 (WCASE-2) promoted to the primary architectural question: whether
  `build_writer_context()` lexical heuristics (relevance ranking, excerpt
  bounding, technique tags, experience selection) moved semantic selection
  from the model to the host; BENCHMARKS B2 gains a step-0 preselection
  audit, REVIEW_GATES gains G13/G14;
- taxonomy erratum: `save_article` is `ARTIFACT_SUBMISSION` (local
  deliverable persistence), not `EXTERNAL_ACTION`; SKILL.md taxonomy
  corrected and the T003 record annotated, history not rewritten.

Reason:
- executing stale task assumptions would manufacture the over-engineering
  the coach pack exists to prevent; the queue must follow measured evidence,
  not the reverse.

Status: accepted by coach pack recalibration. Next: T004G human verdict
gate, then fresh WCASE-2/3/4 baselines.

