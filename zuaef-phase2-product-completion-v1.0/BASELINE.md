# BASELINE — Fixed Phase 1 Facts

These are accepted Phase 1 facts. Phase 2 must not reopen them unless a regression proves they are false.

## B1 — Upstream pair

```text
pydantic-ai = 2.30.0
pydantic-ai-harness = 0.20.0
Python = 3.13
```

Required baseline primitives are READY.

## B2 — Generalist capability surface

The current core can compose released upstream primitives including FileSystem, Shell, RepoContext, Planning, Skills, ToolOutputLimits, StepPersistence, WebSearch, WebFetch, ToolSearch, context controls, Memory, ConversationSearch, and SubAgents.

Phase 2 does not add a new generalist framework.

## B3 — Duplicate infrastructure already removed

Keep these deletions:

```text
ZUAEF generic tool-name conflict preflight
private tool_effects.jsonl parsing
duplicated DeepSeek/provider capability profile flags
```

Do not recreate them behind adapters.

## B4 — Normal Gateway history is fixed

Current Gateway can restore prior server-owned terminal history via public StepPersistence APIs and pass it as `message_history` into a fresh run with the same `conversation_id`.

Do not create another conversation-history database.

## B5 — Pause/resume seam exists

`resume_paused_run()` remains the single continuation implementation for CLI/Gateway approval.

Do not duplicate it.

## B6 — Current product gap

The repository still lacks one authoritative proof that:

```text
Gateway
+ real Case binding
+ profile="stillevo-fde"
+ real business-domain progressive disclosure
+ real customer materials
+ approval
+ follow-up correction
```

work together as one product path.

The existing `tools/fde_two_turn_proof.py` is not sufficient authority because it currently runs `profile="ace-writing"` and re-injects an old Turn-1 constraint into Turn 2.

The older `examples/fde_loop.py` has valuable real Case/decision-loop behavior but is a separate CLI proof with custom composition.

Phase 2 converges those paths into the production profile/Gateway seam.
