# PLAN — Capability-Complete, Outcome-First Migration v2.1

The migration has five phases.

---

# Phase A — Freeze the released upstream baseline

## A1. Record current state

```bash
git status --short
git rev-parse HEAD
uv sync
uv run pytest -q
uv run ruff check .
```

## A2. Select released versions

Choose a released PydanticAI/Harness pair.

Probe the baseline capability surface:

```text
FileSystem
Shell
RepoContext
Planning
Skills
ToolOutputLimits
StepPersistence
WebSearch
WebFetch
ToolSearch/on-demand loading
context controls
Memory
ConversationSearch
SubAgents
```

If a capability exists only on upstream main, record it as:

```text
RELEASE GAP
```

Do not silently vendor it.

## A3. Lock

Record the exact baseline in:

```text
docs/upstream-baseline.md
uv.lock
```

---

# Phase B — Remove duplicate local substrate

## B1. Delete generic tool-conflict preflight

Use upstream toolset composition.

## B2. Replace private persistence parsing

Use public StepStore/persistence APIs.

## B3. Simplify provider logic

Use official DeepSeek/OpenAI-compatible providers/profiles where supported.

### Positive feedback

After each deletion:

```text
targeted tests pass
→ DELETE confirmed
→ do not replace with a new abstraction
```

---

# Phase C — Complete the generalist capability surface

This phase is REQUIRED.

The purpose is not to call everything.

The purpose is to make the same FDE runtime capable of using the standard generalist primitives when needed.

## C1. Integrate baseline upstream capabilities

Compose released public primitives directly.

## C2. Separate five lifecycle states

Implement/configure the architecture so these remain distinct:

```text
AVAILABLE
AUTHORIZED
DISCOVERABLE
LOADED
INVOKED
```

## C3. Progressive disclosure

Ensure the model does not receive all domain/full tool schemas on every turn.

Use released ToolSearch/deferred capability mechanisms.

## C4. Context controls

Enable upstream output/context management.

## C5. Memory/search

Wire Memory and ConversationSearch as available capabilities, with explicit separation from Case and Knowledge.

## C6. SubAgent

Make SubAgent capability available where released, but keep the one FDE Agent as the outcome owner.

### Phase C proof

Use deterministic/test models to prove:

```text
capability exists
authorized capability can be discovered
relevant capability can load
irrelevant capability stays dormant
subagent is available but not automatically used
```

---

# Phase D — Fix real conversational continuity

## D1. Restore history

Normal follow-up:

```text
session
→ previous run
→ public persistence restore
→ message_history
→ fresh run_id
→ same conversation_id
```

## D2. Preserve deferred approval continuation

Use the same upstream history semantics.

No second continuation engine.

---

# Phase E — Real FDE proof and stop

Run the two-turn FDE case.

Verify:

```text
conversation
Case
authorized business capability
artifact
verification
no pricing
no publish
receipt
second-turn correction
```

Then run full regression.

If CAP-1 through CAP-6 pass:

```text
STOP.
```

Next work goes to business-domain quality/capability, not another harness abstraction.

---

# Commit strategy

Prefer 4–6 commits:

```text
1. chore: pin tested PydanticAI and Harness baseline
2. refactor: remove duplicate substrate and private persistence coupling
3. feat: compose generalist capability surface with progressive disclosure
4. fix: restore gateway multi-turn history
5. test: prove capability activation policy and FDE continuation
```

Split provider migration into its own commit only if materially large.
