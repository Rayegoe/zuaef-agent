# ZUAEF Agent Core Rules

## Goal

Own the user outcome with the smallest reliable agent loop. Business behavior is composed through capabilities, toolsets, and deferred skills.

## Architecture boundaries

- Keep one core Agent. Do not create an agent registry or one agent class per business domain.
- Prefer explicit Python composition over discovery/registry machinery.
- Reuse PydanticAI and pydantic-ai-harness primitives; do not clone filesystem, planning, skills, tool-output limiting, approval, usage-limit, or durable-runtime implementations.
- Keep run output thin. Long deliverables go under `workspace/artifacts/`.
- Knowledge is file-native under `workspace/knowledge/`; plain documents are valid, and factual deliverables expose inspectable source URLs where support matters.
- Full oversized tool outputs belong under `.zuaef-state/tool-results/`; pass a handle/preview to the model and retrieve progressively.
- Durable step/tool-effect facts belong to Harness `StepPersistence`; `RunReceipt` is only an index, never a second source of truth.
- External writes and destructive actions use PydanticAI native approval. Never interpret model intent as authorization.
- Surface/Gateway is an external interaction layer. It may own transport, authorization, session bindings, host-grounded interaction projection and approval presentation, but must not implement agent execution, business policy, approval semantics, durable execution truth or receipts.
- Do not add a vector database until lexical/file navigation is measurably insufficient.
- Do not add a graph runtime, custom state machine, long-term-memory service, multi-agent team, custom event bus, custom steering runtime, or custom durable runtime without a measured failure that requires it.

## Layer model

Four layers compose behavior; prefer the lowest layer that fully contains the need:

- **Toolset** answers "what actions can the agent take in this domain?" — a domain action surface plus that toolset's own local call policy (budgets, ordering, tool withdrawal). Local state or policy is not a reason to upgrade.
- **Capability** answers "which reusable behavior must carry tools + instructions + hooks/settings/lifecycle semantics as one unit?" — cross-cutting or shared runtime behavior. A Capability may serve a subset of agents, not necessarily all; it is not defined as "changes every tool / every run".
- **Core** answers "which Harness invariants do all business domains rely on?" — receipts, step persistence, approval, tool-output limiting, protected paths.
- **Skill** carries deferred domain guidance (instructions/knowledge), exposed by the harness as a deferred capability.

Knowledge and FileSystem protection are a paired design, not hook injection: `core.py` configures FileSystem's protected patterns (e.g. `knowledge/*` write-restriction) and the `Knowledge` Capability provides the write path; `Knowledge` does not rewrite FileSystem behavior through hooks.

## Elevation rule

Whether a mechanism floats up (Toolset → Capability → Core) is decided by the emergence of a **stable, domain-agnostic repeated mechanism that needs unified lifecycle semantics** — not by code complexity, and not merely because "two domains both use it". Reuse twice is a signal to start abstracting (a shared `BudgetedToolset`/wrapper/decorator), not an automatic upgrade. Only when the shared mechanism additionally needs unified instructions, tool interception, lifecycle hooks, persistence integration, or settings does it become a Capability; only cross-domain invariants modify the core.

## Terminal states

Every user-facing run ends as `completed`, `partial`, or `blocked` and states unknowns rather than fabricating evidence.

## Change rule

For a new business domain, first add a Skill or Toolset; add a Capability only when the behavior needs to bundle tools/instructions/hooks/settings/lifecycle semantics as one reusable unit (see Layer model and Elevation rule). Modify the core only for cross-domain semantics.

After the v1.2 kernel freeze, a Kernel change is admissible only for PydanticAI/Harness compatibility, execution correctness, a security boundary, durability/resume correctness, the composition ABI, or generic operational run facts. “A business capability needs it” is not sufficient; implement that behavior in its Skill, Toolset, Capability, plugin, or Gateway interaction layer.
