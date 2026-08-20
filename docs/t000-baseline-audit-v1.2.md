# T000 — Baseline Audit (spec pack v1.2: Architecture Subtraction & Evidence Reset)

Date: 2026-08-20
Baseline: `main@14e0df0` (+ P3B-3 checkpoint `dbfe1c3`, committed before this audit)
Auditor: coding agent

## 1. Current full test result

`python -m pytest -x -q`: **585 passed** (55.68s), 1 deprecation warning
(`test_gateway_service.py:898` asserts `receipt.summary.deliverable is None`, a
deprecated P3B-2 field scheduled for removal).

Ruff: not yet re-run in this audit (will run before each commit).

## 2. Semantic-field consumers (old receipt evidence fields)

Files that read/write `verified_artifacts`, `verified_knowledge`,
`verified_tool_effects`, `verified_evidence_refs`, `settled_evidence`,
`degraded`, `summary.evidence`, `summary.artifacts`, `summary.unknowns`:

| File | Usage |
| --- | --- |
| `src/zuaef_agent/runtime.py` | `finalize_terminal()` builds `verified_*` lists + `degraded` list + downgrades `completed→partial`; `_build_paused()` writes `settled_evidence` + `verified_*`; `_assert_pending_case_isolation()` rejects cross-case approvals at pause frontier |
| `src/zuaef_agent/models.py` | `RunSummary.artifacts/evidence/unknowns/next_action`, `ArtifactVerification`, `ToolEffectVerification`, `RunReceipt.verified_*`, `RunReceipt.degraded`, `PauseReceipt.settled_evidence`, `RunReceipt.status` (partial/blocked), `CoreDeps.case_id` |
| `src/zuaef_agent/verification.py` | `_EVIDENCE_RE`, `parse_evidence_ref`, `verify_knowledge` (semantic), `verify_tool_effect` (ref resolution), `verify_artifact` (integrity — keep) |
| `src/zuaef_agent/continuation.py` | reads `receipt.case_id` for resume; restore from pause receipt |
| `src/zuaef_agent/gateway/renderer.py` | `receipt.summary.outcome`, `receipt.verified_artifacts`, `receipt.verified_tool_effects` in terminal card fallback; `receipt.status` mapping |
| `src/zuaef_agent/gateway/service.py` | `outcome.receipt.status` for state labels (`LAST COMPLETED/PARTIAL/BLOCKED`) |
| `src/zuaef_agent/cli.py` | `outcome.summary.status` → exit code; `summary.outcome` in tests |
| `src/zuaef_agent/knowledge_capability.py` | `write_knowledge` tool requires `doc_type` + `SourceRef`; instructions claim "evidence-backed artifacts" |
| `src/zuaef_agent/knowledge_store.py` | `REQUIRED_SOURCE_TYPES`, `NO_SOURCE_TYPES`, `KNOWN_TYPES`, `SourceRef` import, frontmatter `sources` |
| `src/zuaef_agent/gateway/store.py` | comment only ("historical evidence") |
| `src/zuaef_agent/core.py` | comment only — no semantic verification call |

Tests consuming the fields: `test_execute_run_seam.py` (25 refs — the primary
receipt-semantics suite), `test_gateway_service.py` (15), `test_editorial_control.py`
(5), `test_client_service_store.py` (5), `test_budget_slice.py` (5),
`test_gateway_renderer.py` (4), `test_continuation.py` (4),
`test_cli_and_providers.py` (3), `test_receipt_store.py` (2),
`test_gateway_e2e_wordpress.py` (2), `test_cli_resume.py` (2),
`test_case_toolset.py` (2), `test_wordpress_plugin.py` (1),
`test_production_writing.py` (1), `test_gateway_bridge.py` (1),
`test_client_service_slice.py` (1), `test_client_service_policy.py` (1).

## 3. Case-specific kernel usages

| Location | Usage |
| --- | --- |
| `src/zuaef_agent/models.py` | `CoreDeps.case_id: str \| None` (3×: CoreDeps, RunReceipt, PauseReceipt) |
| `src/zuaef_agent/runtime.py` | `_assert_pending_case_isolation()` (lines 109–135); `case_id` threaded through `finalize_terminal`, `_build_paused`, `execute_run` |
| `src/zuaef_agent/continuation.py` | restores `case_id` from pause receipt |
| `src/zuaef_agent/gateway/bridge.py` | `start_profile_run(case_id=...)`, `project_case_context(...)` import + call, `CASE_CONTEXT_SEPARATOR` alias |
| `src/zuaef_agent/gateway/service.py` | session binding (`session.case_id`), `/bind`, `_outbound_draft_content` reads `case_id` arg — **gateway/surface concern, stays** |
| `src/zuaef_agent/gateway/renderer.py` | status/approval card shows `Case: {case_id}` — **surface concern, stays** |
| `src/zuaef_agent/gateway/models.py` | `InboundEnvelope.case_id` (session/binding) — **surface concern** |
| `src/zuaef_agent/context_projection.py` | `project_case_context` — **kernel tree module, must move into `zuaef-case` plugin (T005)** |

## 4. Editorial derived-label consumers

| File | Fields |
| --- | --- |
| `benchmarks/editorial-learning/evidence/human_patches.jsonl` | `trigger_signals`, `action`, `directive`, `weight`, `approved_by` (legacy derived rows) |
| `benchmarks/editorial-learning/evidence/seed_snapshot.jsonl`, `compiled/*`, `curated/techniques.jsonl` | same derived schema |
| `benchmarks/editorial-learning/scripts/run_benchmark.py`, `compile_learning_pack.py`, `host_projection_legacy.py`, `build_tasks.py` | consume derived fields |
| `benchmarks/editorial-learning/experiments/sequential-v1/scripts/{run_experiment,derive_patches}.py` | consume derived fields |
| `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py` | `EditorialLearningRecord` with `trigger_signals/action/weight/approved_by` + seeded rules (weight 1.0, approved_by `seed:v0.1`) — **business-plugin concern; must not leak into kernel** |

## 5. Other spec targets inventory

- `GENERALIST_FLAGS` in `config.py` (9 entries) — consumed by `composition.py:225`,
  `profiles.py:40`, `config.py:75`. P3B-3 already added CJK-aware ToolSearch via
  upstream capability seam (no new flag). → close as compatibility surface (T008).
- `context_projection.py` — bounded Case brief, no trajectory (P3B-2/P3B-3).
  Moves to `plugins/zuaef-case` (T005).
- `knowledge_store.py` — `write_doc(doc_type, sources)` gate → simplify (T007).
- `interaction_projection.py` — host-grounded, no workflow. **Compatible; keep.**
- `source_check`-able real evidence: currently zero source-URL-bearing artifacts
  in repo; the Stillevo case materials carry real content but no explicit
  source-URL sections (needed for Phase D proof).

## 6. Classification (Phase A §5)

| Occurrence class | Where |
| --- | --- |
| security/integrity (keep) | `sha256_file`, `normalize_artifact_path`, `snapshot_artifacts`, `verify_artifact` (byte facts), StepStore projection, path containment |
| runtime bookkeeping (keep, rename) | tool-effect ledger, artifact byte facts, usage, pause frontier |
| semantic claim (delete) | `_EVIDENCE_RE`, `parse_evidence_ref`, `verify_knowledge` as truth, `verify_tool_effect` as evidence resolution, `verified_*`, `settled_evidence`, `degraded` as semantic downgrade |
| business-domain leak (move) | `case_id` in CoreDeps/receipts, `project_case_context` in kernel, `_assert_pending_case_isolation` in runtime |
| benchmark-only derived (quarantine) | editorial `trigger_signals/action/weight/approved_by` → `derived/legacy/` if experiments need them; never production authority |

## 7. Sequencing note

Phase B (T001–T003) touches `models.py`, `runtime.py`, `verification.py` and
their tests; Phase C (T004–T006) then migrates Case out of the kernel. The
P3B-3 checkpoint is already committed (`dbfe1c3`) so Phase B/C diffs stay
reviewable.
