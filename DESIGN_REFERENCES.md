# v1.1 design references

These repositories informed v1.1. They are design references, not copied runtime dependencies.

## DeepSeek Harness

Source: https://github.com/deepseek-ai/deepseek-harness

Absorbed principles:
- Separate durable session/execution facts from the model-visible surface.
- Treat tool execution as a guarded effects boundary.
- Make compaction/output reduction optional capabilities rather than agent-loop identity.
- Preserve enough execution evidence to distinguish settled work from uncertain tool effects.

Explicitly rejected for this phase:
- Cordis plugin tree.
- Service registry/event waterfalls.
- Agent registry and a fully event-sourced application runtime.

Reason: ZUAEF already has PydanticAI Capability/Toolset composition, and the current business requirement does not justify a second runtime platform.

## Pi

Source: https://github.com/earendil-works/pi

Absorbed principles:
- Keep the core agent loop small.
- Treat context as a projection (`transformContext`-style thinking), not the durable truth store.
- Separate tool preflight/effect policy from tool implementation.
- Keep interruption/recovery semantics explicit.

Deferred:
- Steering/follow-up queues.
- Pi's full durable AgentHarness operation state machine.

Reason: useful later for Telegram/live control, but not required to validate the first ingestion vertical slice.

## PydanticAI / pydantic-ai-harness

Runtime implementation source:
- https://github.com/pydantic/pydantic-ai
- https://github.com/pydantic/pydantic-ai-harness

Used directly instead of reimplementation:
- Capability / Toolset composition.
- Native tool approval / deferred tool flow.
- `ToolOutputLimits`.
- `StepPersistence`.
- Filesystem, Planning, and Skills capabilities.
