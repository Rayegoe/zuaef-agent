# v1.1 validation record

## Completed in this build environment

- 11 pure/static tests passed.
- All Python source, tests, and examples compiled and parsed successfully.
- `pyproject.toml` parsed and reports version `0.1.1`.
- Static contract asserts the core includes `ToolOutputLimits`, `StepPersistence`, `LocalFileStore`, and `FileStepStore`, and does not introduce `AgentRegistry` / custom state-machine symbols.
- Runtime state is rejected if configured inside the model-writable workspace.

## Not executable in this build environment

This environment does not have `pydantic_ai` or `pydantic_ai_harness` installed, so a real provider-backed run was not executed here.

## Required target-machine acceptance test

On the target machine (repository root) after installing/syncing dependencies:

1. Run the full pytest suite.
2. Run a small read-only agent task and verify a receipt appears under `.zuaef-state/receipts/`.
3. Run a tool that returns >10k characters and verify a spill appears under `.zuaef-state/tool-results/` and the model receives a read handle/preview rather than the entire payload.
4. Inspect `.zuaef-state/steps/<run_id>/` and verify step events/snapshots/tool-effect records exist.
5. Register one external-write test tool with native `requires_approval=True` and verify execution pauses/defers until approval.
6. Then run the first real vertical slice: YouTube URL -> transcript/evidence -> knowledge nodes -> RunSummary + RunReceipt.
