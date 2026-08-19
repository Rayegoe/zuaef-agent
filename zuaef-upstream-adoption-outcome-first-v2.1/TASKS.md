# TASKS — Capability-Complete Outcome-First Ledger v2.1

Allowed results:

```text
PASS
READY
DORMANT
KEEP
DELETE
RELEASE GAP
BLOCKED
```

---

## T001 — Baseline repository and Golden Outcome

Run tests/lint and the closest current FDE proof.

Record:

```text
current HEAD
current dependency versions
current Golden Outcome path
known continuity defect
business invariants that already work
```

Do not refactor.

---

## T002 — Pin released upstream pair

Probe and record exact released support for:

```text
Agent/Capability/Toolsets
deferred tools/history
FileSystem
Shell
RepoContext
Planning
Skills
ToolOutputLimits
StepPersistence/public StepStore
WebSearch
WebFetch
ToolSearch/on-demand loading
context controls
Memory
ConversationSearch
SubAgents
official DeepSeek/provider path
```

For each item mark:

```text
READY
or
RELEASE GAP
```

Do not use main-only production imports.

Regenerate `uv.lock`.

---

## T003 — Delete generic tool-conflict duplication

Remove ZUAEF preflight whose job is already handled by upstream composition.

Add a small collision regression test.

Expected result:

```text
DELETE
```

Do not replace it with another registry.

---

## T004 — Replace private StepPersistence layout parsing

Remove `tool_effects.jsonl` or equivalent backend-file dependencies.

Use public StepStore/persistence APIs.

Keep business verification logic.

Expected result:

```text
DELETE private coupling
KEEP business verification
```

---

## T005 — Simplify provider resolution

Use official provider/profile behavior.

Delete duplicated DeepSeek/model capability flags when supported by the pinned release.

Keep only deployment-specific HTTP/proxy/custom-endpoint glue.

---

## T006 — Compose baseline generalist capability surface

Integrate released public implementations for:

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
ToolSearch/on-demand capability loading
context controls
Memory
ConversationSearch
SubAgents
```

A release-gap capability must be documented, not silently custom-built.

Do not create `ZUAEFGeneralistHarness`.

A small constructor/helper returning upstream capabilities is acceptable.

### Done

Every baseline primitive is either:

```text
READY
or
RELEASE GAP
```

---

## T007 — Implement authorization + progressive disclosure policy

Prove the five states remain separate:

```text
AVAILABLE
AUTHORIZED
DISCOVERABLE
LOADED
INVOKED
```

Required test cases:

### Case A — internal writing task

Expected:

```text
writing/case capability may load
web remains dormant
shell remains dormant
subagent remains dormant
```

### Case B — current external research task

Expected:

```text
web capability discoverable
web loads/invokes
unrelated WordPress/budget capability remains dormant
```

### Case C — repository task

Expected:

```text
RepoContext available
Shell available if authorized
repo/shell may load
client-writing capability remains dormant
```

### Case D — isolated parallel task

Prove SubAgent is available and callable.

Do not force the model to use it in all tasks.

---

## T008 — Context management baseline

Enable released upstream controls:

```text
ToolOutputLimits
clear stale tool results / equivalent
compaction / context-window strategy
warnings/thresholds where available
```

Test with an oversized synthetic trajectory.

Expected:

```text
capability READY
activation is threshold/task driven
```

---

## T009 — Memory and conversation recall baseline

Wire released:

```text
Memory
ConversationSearch
```

Keep them separate from:

```text
Case
Knowledge
message_history
```

Tests must show:

```text
Memory can persist/retrieve a non-evidentiary note
ConversationSearch can retrieve prior conversation material
Knowledge provenance is unchanged
Case state is unchanged
```

Do not migrate Case/Knowledge into Memory.

---

## T010 — Fix normal Gateway multi-turn history

Implement:

```text
session
→ previous server-owned run
→ public history restore
→ message_history
→ new run_id
→ same conversation_id
```

Test Turn 1 constraint is visible to Turn 2.

---

## T011 — Preserve approval continuation

Verify approve/deny/resume still works.

Requirements:

```text
fresh run_id
same conversation_id
history restored
DeferredToolResults
composition identity preserved
```

Do not create another continuation engine.

---

## T012 — Preserve business invariants

Verify existing:

```text
Case
Knowledge provenance
artifact verification
RunReceipt/PauseReceipt
ACE writing
client service
budget
WordPress
FDE decision loop
```

Healthy components should be marked:

```text
KEEP
```

Do not refactor them merely because adjacent substrate changed.

---

## T013 — Real FDE two-turn proof

Turn 1:

```text
客户觉得上一篇 demo 太模板化。
结合他之前给的背景和材料重写一篇。
价格先不要写，我看完再决定要不要发。
```

Turn 2:

```text
开头还是太像 AI。
保留刚才客户背景，再改一版；其他要求不变。
```

Capture:

```text
conversation_id
two run_ids
loaded capabilities
invoked tools
dormant irrelevant capabilities where observable
Case/customer context
material sources
artifact
verification
no pricing
no publish
receipt
Turn 2 continuity
```

This gate requires real execution if credentials are available.

---

## T014 — Final regression and stop

Run:

```bash
uv run pytest -q
uv run ruff check .
```

Report:

```text
CAPABILITY SURFACE
READY / RELEASE GAP

ACTIVATION QUALITY
what loaded
what remained dormant
why

DELETE
local generic infrastructure removed

KEEP
business semantics retained

COMPLEXITY DELTA
generic abstractions added/deleted

FDE OUTCOME
PASS/PARTIAL/BLOCKED
```

If CAP-1 through CAP-6 pass:

```text
STOP generic harness work.
```
