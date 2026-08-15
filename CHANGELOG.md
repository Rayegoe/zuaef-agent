# Changelog

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
