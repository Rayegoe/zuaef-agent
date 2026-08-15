# ZUAEF Agent Core Rules

## Goal
Own the user outcome with the smallest reliable agent loop. Business behavior is composed through capabilities, toolsets, and deferred skills.

## Architecture boundaries
- Keep one core Agent. Do not create an agent registry or one agent class per business domain.
- Prefer explicit Python composition over discovery/registry machinery.
- Reuse PydanticAI and pydantic-ai-harness primitives; do not clone filesystem, planning, skills, tool-output limiting, approval, usage-limit, or durable-runtime implementations.
- Keep run output thin. Long deliverables go under `workspace/artifacts/`.
- Knowledge is file-native under `workspace/knowledge/`; important claims carry source/evidence metadata.
- Full oversized tool outputs belong under `.zuaef-state/tool-results/`; pass a handle/preview to the model and retrieve progressively.
- Durable step/tool-effect evidence belongs to Harness `StepPersistence`; `RunReceipt` is only an index, never a second source of truth.
- External writes and destructive actions use PydanticAI native approval. Never interpret model intent as authorization.
- Do not add a vector database until lexical/file navigation is measurably insufficient.
- Do not add a graph runtime, custom state machine, long-term-memory service, multi-agent team, custom event bus, custom steering runtime, or custom durable runtime without a measured failure that requires it.

## Terminal states
Every user-facing run ends as `completed`, `partial`, or `blocked` and states unknowns rather than fabricating evidence.

## Change rule
For a new business domain, first add a Skill or Toolset. Add a Capability only when the behavior needs to bundle tools/instructions/hooks/settings as one reusable unit. Modify the core only for cross-domain semantics.
