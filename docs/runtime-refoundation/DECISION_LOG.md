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

## ADR-RF-006 — Close WCASE-1 outcome gate and surface admission review

Decision:
- the human outcome gate accepts `final(3).md` as the reference-quality
  candidate and rejects `final-revised.md` as a prose-quality regression;
- the accepted candidate preserves concrete human presence, scene-level
  material, imperfect trial evidence (including 2 with no obvious change and
  4 withdrawals), narrative paragraph movement and a restrained ending;
- normalized WCASE-1 values are now explicit: `outcome_pass=true` and
  `evidence_pass=true`;
- T004 closes `CURRENT_PATH_ALREADY_MINIMAL`: 2 requests / 1
  `save_article` call is retained, and no one-request terminal mechanism is
  added solely for metric improvement;
- T005 closes `NO_REMOVAL_JUSTIFIED`: the remaining model-visible surfaces
  (`pull_context`, `save_article`, and the writing toolset instructions/code
  mode metadata) have no demonstrated WCASE-1 failure caused by their
  presence. Generic capabilities remain OFF in the writing profile.

Reason:
- current outcome quality is now human-adjudicated; optimizing request count
  without an outcome gain would risk changing the artifact-submission
  contract, while removing an unused semantic observation tool would remove
  optional model authority without evidence of harm.

Status: accepted. T004/T005 complete. Stop here; T006 is the next separate
experiment and is not started by this decision.

## ADR-RF-007 — T006 semantic preselection diagnosis and technique-only A/B

Decision:
- correct the T006 diagnosis from the overbroad
  `HOST_SEMANTIC_PRESELECTION_CAUSES_MEASURED_RISK` label to
  `SEMANTIC_PRESELECTION_REPRODUCED / OUTCOME_IMPACT_UNMEASURED`;
- record T006-A as diagnosis complete, not Phase 2 complete;
- run only the T006-B1 technique preselection experiment: control keeps the
  current host-selected technique projection, candidate disables it while
  keeping raw materials, experience projection, model, thinking setting,
  prompt, tools and save semantics fixed;
- keep T007 deferred until blind human quality/evidence evaluation justifies
  the selected observation design.

Evidence:
- WCASE-2 raw-material transport remains broad on the fixture: 9/9 bodies,
  including irrelevant M005/M006/M009 and conflicting M002/M008, reached the
  first request;
- the host still exposed only 3 of 18 active technique records and selected
  technique tags before the model's choice;
- T006-B1 control: 8 requests, 7 tool calls, 93,387 input tokens,
  198,575.356 ms, artifact sha256
  `64f8625ebf79c89bd4400470a8664c5f4197062f0821a0a3387ba6c32dcf5e38`;
- T006-B1 candidate: 4 requests, 3 tool calls, 29,591 input tokens,
  119,244.722 ms, artifact sha256
  `0233b5b293e0fbaa6c640fd8d5ecd73ecb6fa43627d5f4673411b1e14ffc84da`;
- both executions completed, but both outcome and evidence evaluations are
  `null`; runtime deltas cannot promote the candidate.

Status: T006-A complete; T006-B1 human gate pending. Phase 2 remains open.

## ADR-RF-008 — T006-B1 reverse pair does not establish runtime causality

Decision:
- complete one reverse-order T006-B1 pair (`Candidate/OFF → Control/ON`) to
  test whether the first pair's `8/7` versus `4/3` trajectory difference
  persists;
- treat the first pair's runtime delta as unconfirmed provider/model
  trajectory variance, not as a technique-off speedup;
- keep the human blind quality/evidence gate as the only remaining B1
  promotion gate; do not start T006-B2 or T007.

Evidence:
- reverse Candidate/OFF: 2 requests, 1 `save_article`, 8,156 input tokens,
  1,584 reasoning tokens, 66,045.186 ms;
- reverse Control/ON: 2 requests, 1 `save_article`, 10,896 input tokens,
  2,951 reasoning tokens, 89,034.352 ms;
- first-pair tool sequences were `pull_context → save_article × 6` for ON
  and `pull_context → save_article × 2` for OFF; both reverse sequences were
  only `save_article`;
- reverse first-request identities preserved M001–M009 and the experience
  projection on both sides. Prompt hashes were
  `95d3e69945ca1a5f52153bb1c2c47f1191e520a29dc3fef83cfd50cec398436b` (OFF)
  and `b63cc5ab4ef5f3021f31026efbd661a8a323fad2ad8ded84a70756c85e66664a`
  (ON), with the expected technique projection present only on ON;
- both reverse runs still have `outcome=null` and `evidence=null`.

Interpretation:
- the reverse pair does not reproduce a stable ON-long/OFF-short trajectory;
- repeated `save_article` calls in the first ON run are an observed trace
  difference, but their quality meaning is unknown;
- no causal runtime claim or promotion follows from these runs.

Status: T006-A complete; T006-B1 reverse variance check complete and human
gate pending. Phase 2 remains open; T007 remains deferred.

## ADR-RF-009 — T006-B1 human review rejects technique-off removal

Decision:
- record the blind result as **A clearly preferred over B**;
- map A to the first Control/ON artifact and B to the first Candidate/OFF
  artifact by artifact hash;
- reject promotion of the technique-off candidate for the target editorial
  outcome;
- keep the current ON path as the comparison baseline only. Do not treat this
  result as proof that the host keyword selector is the correct long-term
  semantic authority;
- keep Phase 2 open and T007 deferred while designing a model-owned technique
  observation experiment.

Evidence:
- A / Control ON scored 8.2 overall; B / Candidate OFF scored 6.4;
- A led on reading flow, human feel, scene, natural information embedding,
  rhythm, restraint and human-business narrative potential; B led only on
  commercial-information completeness (8.7 vs 8.2);
- the reviewer identified B's recurring
  `material → explanation → summary → brand meaning` closure as the main
  quality failure, while A more often let concrete actions and objects stand
  without an explanatory summary;
- the reviewer found no material factual-quality regression and noted highly
  overlapping facts, but did not separately mark the M002/M008 conflict or
  M005/M006/M009 handling fields pass/fail. Those evidence subchecks remain
  `unclear` rather than being fabricated as a full evidence pass;
- the reverse paired runtime check already established that the first
  `8/7` versus `4/3` request/tool delta was not a stable causal runtime
  difference.

Interpretation:
- the OFF candidate demonstrates a quality regression when technique
  projection is simply removed;
- the experiment does not validate `_technique_tags()` or the host's 3/18
  record choice as the final architecture;
- the useful next question is how to preserve the needed writing behavior
  while returning the timing/selection judgment to the model, rather than
  adding more generic style prohibitions.

Status: T006-A complete; T006-B1 quality verdict complete, evidence
subchecks unclear. Phase 2 remains open; T007 remains deferred.

## ADR-RF-010 — T006-B2 model-owned technique selection execution

Decision:
- keep the current production Control unchanged: it still projects the
  Host-selected 3/18 technique shards;
- run a benchmark-only Candidate that exposes an 18-row neutral ACE metadata
  catalog and one batch `pull_techniques(ids)` action, with no Host ranking,
  keyword tagging, fallback or semantic top-k selection;
- record the Candidate's actual model selection as
  `ex-scene-pause-001`, `ex-prose-object-001`, `ex-final-quote-001`, which is
  different from the Control's Host-selected IDs;
- do not infer quality, evidence correctness or promotion from the runtime
  trace. The Candidate produced an artifact but reached the Harness usage
  boundary after repeated `save_article` calls.

Evidence:
- Control: 2 requests, 1 `save_article`, 12,141 input tokens,
  113,050.284 ms, artifact sha256
  `0b590cac84ce8b4b1c91e1972eca4ba770a4e5bfcac64569d86ba17eb4d3f31a`;
- Candidate: 12 requests, 12 tools (`pull_techniques` once plus 11
  `save_article` calls), 175,569 input tokens, 399,771.416 ms, final
  artifact sha256
  `0f899f13e64734a4a41e56aa516d5b3ad9cb8433cb6e0624a2866f1b2fc47704`,
  execution state `limit_reached`;
- both first requests contained M001–M009 and the same experience section;
  only the Candidate contained the neutral 18-row catalog;
- first-request hashes are recorded in the B2 experiment record, together
  with the fixture identity, composition IDs and source hashes.

Interpretation:
- the model-owned seam is mechanically real and returned different choices;
- the run exposed a non-terminal repeated-save trajectory that must be
  included in the runtime/outcome assessment, not hidden as a cost metric;
- no decision yet answers whether model-owned selection preserves B1's
  editorial quality or evidence correctness.

Status: T006-B2 execution recorded; human blind quality/evidence verdict
pending. Phase 2 remains open; T007 remains deferred.
