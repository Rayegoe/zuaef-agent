# Refactor notes — v1.1

## Kept in the core

- Model/provider resolution.
- One `Agent` construction function.
- Run dependency object and usage budgets.
- Thin terminal output contract.
- Cross-domain filesystem, planning, skills, and knowledge capabilities.

## Added in v1.1

- `ToolOutputLimits` with a runtime-only sibling spill store outside the model-writable workspace. Large tool payloads are stored once and read progressively instead of dominating every later request.
- `StepPersistence` with `FileStepStore`. Step events, continuable snapshots, and the tool-effect ledger come from the Harness; ZUAEF does not reimplement them.
- `EffectClass` + `requires_approval()` as a tiny policy vocabulary for PydanticAI native approval. No custom approval runtime was introduced.
- `RunReceipt` + atomic `ReceiptStore`. A receipt is an index over durable evidence, not a second event log.
- Knowledge nodes can be queried by generating `run_id`, allowing receipts to list knowledge updates without a database.

## Removed / still rejected by design

- Agent registry.
- Domain-specific agent subclasses.
- Custom graph/state-machine runtime.
- Long-term-memory service.
- Vector database/RAG pipeline.
- Multi-agent/team orchestration.
- Custom checkpoint/durable runtime.
- Cordis-style plugin tree / service registry / event bus.
- Pi-style custom durable operation state machine.

## Runtime truth boundaries

1. `workspace/knowledge` and `workspace/artifacts` are durable user/business truth.
2. `.zuaef-state/steps` is execution evidence owned by Harness StepPersistence.
3. `.zuaef-state/tool-results` is full-fidelity spill storage for large tool returns.
4. `.zuaef-state/receipts` is a compact per-run index.
5. The model context is a projection of what is currently needed; it is not the durable truth store.

## Approval rule

Read-only and ordinary local writes may run automatically. External writes and destructive actions should be registered with PydanticAI native approval. Approval protects against model autonomy; tool implementations must still enforce authentication and authorization.

## Integration into the target repository

This package was generated outside that machine, so it does not overwrite the local checkout. Apply it as a scaffold/patch source, then run the target environment's installed PydanticAI/Harness integration tests. The package was statically validated here, but this environment does not have `pydantic_ai` / `pydantic_ai_harness` installed, so provider-backed integration execution must happen in the target environment.
