# Changelog

## Unreleased

### Docs — project narrative: proof PASS fixed as repo fact

- `README.md`: `Next vertical slice` → `Proven vertical slice`. The final proof run
  (`c58bf8cc62534cb3b991d47b6b5f404c`, `deepseek-v4-flash`, 22 requests, receipt
  `completed`) is now stated as fact, with the pull/receipt/settlement dataflow
  diagram and the convergence fixes (resume-safe quota, tool withdrawal, run
  isolation, probe non-authoritative). `Next` now reads: repeat the same contract
  with a second business slice or a second runtime.
- `LICENSE`: added MIT license for the public repository.

### Proof — Harness-neutral pull-based Context execution (PASS)

- article_id `vs-hw951-context-proof-20260815`, run `c58bf8cc62534cb3b991d47b6b5f404c`, `deepseek-v4-flash`, 22 requests, receipt **completed**; all machine checks PASS; historical unstamped receipts ignored; knowledge/exemplars stopped exactly at per-run caps; probe ran after final save without triggering another save. Details in `spec/writing-slice-gate.md`.

### Changed — writing-slice convergence mechanics

- `examples/writing_toolset.py`: budgets are now resume-safe. `BudgetedWritingToolset` seeds per-run delivery counts from THIS run's ACE receipts (durable truth, read once per process) plus an in-process fast-path counter; a rebuilt toolset after pause/crash/resume re-reads the receipts, so quota is never reset by process reconstruction. Exhausted tools are refused at call time (normal terminal return → settled `completed` effect) AND withdrawn from the next model step's action space via `get_tools` — the model is no longer offered a tool whose budget is spent.
- `examples/writing_case.py`: instructions/prompt state that exhausted tools are withdrawn (do not attempt them again) and that the `integration_probe` is non-authoritative for the saved artifact — its output must never trigger another save.
- `spec/writing-slice-gate.md`: documents receipt-backed durable quota, withdrawal semantics, and the probe non-authoritative declaration.

### Changed — writing-slice experiment credibility repair

- `examples/writing_toolset.py`: every ACE call is stamped with `run_id` (from `RunContext.deps`); budgets are enforced per `(run_id, tool)` in the adapter only — the impl-layer receipt-history counters were deleted, so prior runs can no longer exhaust a new run's budget or satisfy its acceptance.
- `examples/writing_case.py`: `context_usage(workspace, run_id)` filters receipts and claim-checks to the current run; the mandatory-vs-conditional claim-check contradiction is resolved by an explicit `purpose="integration_probe"` capability canary after the final save; gate predicate renamed to `machine_ready_or_complete` (fully green OR only `human_final_reviewed` pending); `save_artifact_impl` no longer overwrites ACE's semantic `ok` (adds `transport_ok` instead).
- `spec/writing-slice-gate.md` updated to the run-isolated receipt contract and the bounded-trajectory / probe semantics.

## 0.1.1 — 2026-08-14

### Added

- Harness `ToolOutputLimits` with persistent local spill storage at `.zuaef-state/tool-results/`.
- Harness `StepPersistence` with `FileStepStore`, bounded snapshot retention, and explicit per-run id correlation.
- `EffectClass` / `requires_approval()` policy helper for PydanticAI native tool approval.
- Atomic `RunReceipt` persistence at `.zuaef-state/receipts/`.
- Knowledge provenance lookup by generating `run_id`.
- Runtime-state isolation: `.zuaef-state/` must live outside the model-writable workspace.
- Static architecture contract tests and approval example.

### Intentionally not added

- Agent registry, event bus, plugin tree, graph runtime, custom state machine, custom durable runtime, multi-agent orchestration, vector database, generic source router, or custom steering queue.
