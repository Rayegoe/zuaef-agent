# UPSTREAM BASELINE — ZUAEF pinned release record

Inspection anchor: 2026-08-28 (ZUAEF-ASHARE-001 U0 upstream refresh; prior anchor 2026-08-19 v2.1).

Source of truth for what the ZUAEF platform baseline is built on. Execute
`uv run python tools/probe_upstream_baseline.py` against the locked
environment to reproduce the matrix below (it only probes importability —
no model request, no credentials).

## Pinned pair

| Package | Version | Lockfile |
|---|---|---|
| `pydantic-ai` | 2.35.3 | `uv.lock` |
| `pydantic-ai-harness[skills,code-mode]` | 0.27.0 (minor-bound: `>=0.27,<0.28`) | `uv.lock` |
| Python | 3.13 | — |

`uv.lock` is the exact execution baseline. Production never consumes upstream
`main`; anything not present in this pair is recorded as a `RELEASE GAP` and
is never silently reimplemented or vendored.

## Capability matrix (released support)

| Primitive | Module | Result |
|---|---:|---:|
| Agent / Capability / Toolset | `pydantic_ai` | READY |
| FileSystem | `pydantic_ai_harness.filesystem` | READY |
| Shell | `pydantic_ai_harness.shell` | READY |
| RepoContext | `pydantic_ai_harness.repo_context` | READY |
| Planning | `pydantic_ai_harness.planning` | READY |
| Skills | `pydantic_ai_harness.skills` | READY |
| ToolOutputLimits | `pydantic_ai_harness.tool_output_limits` | READY |
| StepPersistence / public StepStore | `pydantic_ai_harness.step_persistence` | READY |
| Memory | `pydantic_ai_harness.memory` | READY |
| ConversationSearch | `pydantic_ai_harness.conversation_search` | READY |
| SubAgents | `pydantic_ai_harness.subagents` | READY |
| Context controls / compaction | `pydantic_ai_harness.compaction` | READY |
| WebSearch | `pydantic_ai.capabilities` | READY |
| WebFetch | `pydantic_ai.capabilities` | READY |
| ToolSearch / on-demand loading | `pydantic_ai.capabilities` + `pydantic_ai.toolsets.DeferredLoadingToolset` | READY |
| official DeepSeek provider/profile | `pydantic_ai.providers.deepseek` | READY |
| CodeMode (combined stack, optional) | `pydantic_ai_harness.code_mode` | READY |
| Advisor (optional) | `pydantic_ai_harness.advisor` | READY |
| DynamicWorkflow (optional) | `pydantic_ai_harness.dynamic_workflow` | READY |

**RELEASE GAPS: none for the required baseline surface on this pair.**

## Availability vs activation

The matrix answers only: *can the platform provide this capability?*

- **AVAILABLE** — integrated/composable in the runtime, covered by smoke tests.
- **AUTHORIZED** — enabled by deployment/profile policy (not model judgment).
- **DISCOVERABLE** — a compact catalog/tool-search entry the model can see.
- **LOADED** — full instructions/tools enter active context for a task.
- **INVOKED** — the model actually calls it for this task.

A primitive may be `AVAILABLE + AUTHORIZED + DISCOVERABLE` while correctly
remaining `NOT LOADED + NOT INVOKED` for a particular task — that is
successful progressive disclosure, not missing functionality.

## Deferred tool-loading / ToolSearch

- `pydantic_ai.toolsets.DeferredLoadingToolset` wraps any toolset so its tools
  are not injected until the model asks.
- `pydantic_ai.capabilities.ToolSearch` (plus `ToolSearchFunc` /
  `ToolSearchLocalStrategy`) gives the model a compact catalog of capabilities
  and on-demand activation.
- Harness capabilities that take `id`/`description` are deferred-capability
  capable.

## Memory boundary

Harness `Memory` and `ConversationSearch` are generic. They do NOT replace:

- ZUAEF `Case` (durable business situation/actors/decisions/constraints);
- evidence-backed `Knowledge` (provenance-carrying re-usable knowledge);
- `RunReceipt` (business settlement truth, an index only).

## Persistence rule

Execution truth lives in public Harness step-persistence APIs
(`pydantic_ai_harness.step_persistence.FileStepStore` /
`StepStore` / `continue_run` / `fork_run` / `list_events`). ZUAEF never parses
private backend files (`tool_effects.jsonl` etc. are not stable contracts).

## Generated/locked files

- `uv.lock` — exact dependency baseline.
- `tools/probe_upstream_baseline.py` — reproducible release probe.
- This file — the recorded support matrix.
