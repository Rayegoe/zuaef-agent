# Changelog

## Unreleased

### Proof — EMTB budget slice (example2) through the production seam (PASS)

- `examples/budget_lib/`: faithful extraction of zesenticai finance_agent deterministic commands (bilingual CSV parsing + summary / variance / consistency / health / query / significant-change). Zero agent / LLM dependency; unit-pinned to source behavior.
- `examples/budget_toolset.py`: `FunctionToolset` adapter over budget_lib; observe tools + `local_write` artifact save; bounded JSON returns.
- `examples/budget_case.py`: drives one real core agent over one real EMTB budget CSV (Chinese + English headers) via `build_agent(settings, extra_toolsets=[...])` — the first business domain through the production seam. Final run `2639102722814111b9b9be253a50d8be` (`deepseek-v4-flash`): receipt `completed`, host-verified artifact, all machine checks PASS, unknowns none.
- `tests/test_budget_slice.py`: 18 deterministic tests — budget_lib extraction pinned to original behavior, toolset functions via TestModel context, and the `extra_toolsets` composition seam driven through `execute_run` with FunctionModel.
- `tests/test_manifest_integrity.py` / `tools/regen_manifest.py`: manifest scope extended to `examples/budget_lib/*.py` and `examples/data/*.csv`.

### Changed — provider networking on proxied hosts

- `src/zuaef_agent/providers.py`: `resolve_model` now honors an http(s) proxy from the environment (`HTTPS_PROXY`/`HTTP_PROXY`) while ignoring `socks://` entries. Fixes `Connection error` on hosts whose system resolver is SERVFAIL behind a TUN/transparent proxy (`trust_env=False` alone could not reach the model endpoint).

### Docs — example2 narrative

- `README.md`: added `Second vertical slice: EMTB budget (example2)` (proof run, what it proved / did not prove); `Next` updated to the third-slice question (Hardware Scout / WordPress adapter as candidate).

### Docs — layer model & elevation rule made explicit

- `AGENTS.md`: added Layer model (Toolset = domain action surface + local call policy; Capability = reusable unit bundling tools/instructions/hooks/settings/lifecycle semantics, may serve a subset of agents; Core = cross-domain Harness invariants; Skill = deferred guidance) and an Elevation rule: a mechanism floats up only on a **stable, domain-agnostic repeated mechanism needing unified lifecycle semantics** — not on code complexity, not on mere two-domain reuse (reuse twice = start abstracting, e.g. a shared `BudgetedToolset`/wrapper). Knowledge/FileSystem protection documented as paired design, not hook injection.
- `README.md` `Next`: sharpened to the verified gap — the writing proof used task-local composition and did **not** exercise the production seam `build_agent(settings, extra_toolsets=[...])`; the second slice must prove that seam (or a second runtime) without touching core.

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
