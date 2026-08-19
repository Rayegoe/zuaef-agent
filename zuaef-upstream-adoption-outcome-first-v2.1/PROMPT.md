# EXECUTION PROMPT — ZUAEF Capability-Complete Outcome-First v2.1

Work on `Rayegoe/zuaef-agent`.

Read:

1. repository `AGENTS.md`
2. repository `Outcome-First PydanticAI Agent Engineering Guide v2.0.md`
3. package `SPEC.md`
4. package `PLAN.md`
5. package `TASKS.md`
6. package `UPSTREAM_BASELINE.md`

## Critical correction

Do NOT interpret Outcome-First as “do not integrate general capabilities until a task fails”.

This is a platform FDE.

The baseline generalist capability surface should be **complete and ready**.

The rule is:

```text
AVAILABLE broadly
AUTHORIZED by deployment
DISCOVERABLE compactly
LOADED selectively
INVOKED only when useful
```

Capability existence and capability invocation are different decisions.

## Required baseline capability surface

Using released PydanticAI/Harness public APIs, make these available where the selected release supports them:

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
context controls / compaction
Memory
ConversationSearch
SubAgents
```

If a capability is unavailable in a released version, record:

```text
RELEASE GAP
```

Do not silently reimplement it.

## Outcome-First still applies

Capability completeness does NOT mean:

```text
load everything into every prompt
call every capability
create a new registry
create a new harness layer
create a router
create specialist default agents
```

The model/context should remain narrow.

## Positive feedback

Use these states:

### READY
Capability integrated and testable.

### DORMANT
Capability correctly remained unloaded/uninvoked for this task.

### LOAD
Capability entered active context because the task justified it.

### INVOKE
Capability/tool was actually used because it improved the outcome.

### KEEP
Existing thin ZUAEF business logic already owns a real business invariant.

### DELETE
Local generic infrastructure was replaced by upstream.

### REUSE
Released upstream public primitive was adopted directly.

### RELEASE GAP
Required baseline capability is not present in a suitable release; document it and do not invent a private replacement.

### STOP
Baseline capability surface + progressive disclosure + real FDE outcome + regressions pass.

## Forbidden architecture

Do not create:

```text
ZUAEFGeneralistHarness framework
IntentRouter
default per-domain Agents
custom WebSearch/WebFetch
custom ToolSearch
custom message-history repair
custom durable runtime
new event bus
new vector database
new generic conversation database
private Harness file parsing
local copies of provider capability profiles
```

SubAgents are allowed as an available upstream primitive, but the main FDE Agent remains the outcome owner.

## Execute

Run `T001` through `T014`.

Do not downgrade T006–T009 to “not needed”; they are platform baseline work.

The decision to load/invoke them belongs in T007 and runtime policy.

## Real FDE proof

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

Prove:

```text
same FDE deployment
real conversation continuity
Case/customer context
authorized material
usable artifact
no pricing
no unauthorized publish
verification
receipt
relevant capabilities used
irrelevant capabilities not needlessly invoked
```

## Final report

Return:

```text
RESULT

UPSTREAM BASELINE

CAPABILITY SURFACE
- READY
- RELEASE GAP

ACTIVATION POLICY
- capabilities loaded/invoked in tests
- capabilities correctly dormant

DELETE
- duplicate generic infrastructure removed

KEEP
- ZUAEF business semantics retained

CONTINUITY
- Turn 2 model-visible history evidence

FDE OUTCOME
- artifact / receipt / side-effect evidence

REGRESSION
- pytest
- ruff

COMPLEXITY DELTA
- generic abstractions added/deleted

STOP DECISION
```

The desired system is:

```text
capable of almost anything authorized,
but only spending context/actions on what this task actually needs.
```
