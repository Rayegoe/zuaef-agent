# EXECUTION PROMPT — ZUAEF Phase 2 Product Completion

Work on `Rayegoe/zuaef-agent` current `main`.

Your task is to take the Phase-1 result to **Phase-2 100%**.

Read:

1. repository `AGENTS.md`
2. repository Outcome-First engineering guide
3. this package `BASELINE.md`
4. this package `SPEC.md`
5. this package `PLAN.md`
6. this package `TASKS.md`

## Do not redo Phase 1

Treat these as fixed unless a regression proves otherwise:

```text
PydanticAI/Harness pinned baseline
generalist capability availability
ToolSearch/Web/Memory/ConversationSearch/SubAgents availability
official provider path
public StepStore use
normal Gateway message_history restore
shared pause/resume seam
```

Do not spend time researching more Harness features.

## Phase 2 outcome

Finish the real product seam:

```text
Gateway channel/thread
→ deterministic Case
→ profile=stillevo-fde
→ one FDE Agent
→ Case context
→ progressive business capability loading
→ real customer material
→ artifact/draft
→ approval for outbound commitment
→ next-turn correction
→ receipt / trajectory
```

## Critical gaps to fix

### 1. Deployment authorization

Generalist capability authorization must be deployment/profile-specific, not only process-global.

Use:

```text
effective permission = host ceiling ∩ profile request
```

Freeze it in composition identity.

Do not build RBAC.

### 2. Business progressive disclosure

Do not expose every Case/Client/Writing/Budget/WordPress schema on every turn.

Use released PydanticAI deferred-loading/ToolSearch primitives.

Do not rewrite all plugins.

Prefer mechanical wrapping of existing Toolsets.

### 3. Gateway Case binding

A channel/thread must be mechanically bound to a Case.

No LLM guessing.

Use existing Gateway SQLite store.

Thread bound Case identity through existing run deps and enforce Case isolation.

### 4. Real authoritative FDE proof

Final proof MUST use:

```text
GatewayService
profile="stillevo-fde"
bound real Case
real model
real domain plugins
```

The current proof using `profile="ace-writing"` is not sufficient.

The old `examples/fde_loop.py` is not production authority.

## Golden Outcome

Turn 1 — send exactly:

```text
客户觉得上一篇 demo 太模板化。
结合他之前给的背景和材料重写一篇。
价格先不要写，我看完再决定要不要发。
```

Turn 2 — send exactly:

```text
开头还是太像 AI，保留刚才客户背景，再改一版；其他要求不变。
```

Do NOT add any hidden reminder to Turn 2.

In particular, do not restate “不要价格”.

Proof must show the constraint survived because of real history + Case state.

## Expected domain behavior

For the writing task:

```text
Case               eager / orientation
Writing            load
Client Service     load only if useful
Budget             dormant
WordPress          dormant because publish was not requested
SubAgent           dormant unless genuinely useful
Shell/RepoContext  unauthorized in this business deployment
```

Do not force tool calls simply to satisfy a demo.

## Approval

If Agent proposes `send_to_customer`:

```text
PausedRun
→ approve/deny
→ existing shared resume_paused_run
```

No second resume path. No automatic publish.

## Architecture budget

You may add only small product seams required by SPEC:

```text
Profile generalist policy
Plugin defer-tools marker/wrapper
Gateway Case binding
CoreDeps case_id
tests/proof/docs
```

You MUST NOT add:

```text
new harness
router
agent registry
workflow engine
RBAC framework
new database
event bus
vector store
custom memory
custom ToolSearch
custom history repair
new specialist agents
mass plugin rewrite
```

## Positive feedback

Use:

```text
KEEP
Phase-1 code already correct.

WRAP
Existing Toolset uses an upstream deferred wrapper.

DORMANT
Capability/domain exists but correctly stays unused.

DELETE
Proof-only/custom authority is no longer needed.

PASS
Real product behavior works.

STOP
P2-1 through P2-8 pass.
```

## Execute

Run `P2-T001` through `P2-T016`.

Use test-first work for remaining gaps.

Do not stop at unit tests if real credentials are available.

Do not claim Phase 2 complete with an `ace-writing`-only proof.

## Final report format

Return exactly:

```text
RESULT
- PASS / PARTIAL / BLOCKED

STARTING HEAD

P2 GATES
- P2-1 Deployment authorization
- P2-2 Progressive disclosure
- P2-3 Case binding/isolation
- P2-4 Real FDE Turn 1
- P2-5 Real FDE Turn 2
- P2-6 Approval
- P2-7 Regression
- P2-8 Documentation

CAPABILITY ACTIVATION
- initial visible domains
- loaded domains
- invoked domains
- dormant domains

CASE EVIDENCE
- case_id
- material/resource refs
- trajectory changes

CONVERSATION EVIDENCE
- conversation_id
- run ids
- proof Turn 2 saw Turn 1

ARTIFACT / SIDE EFFECT EVIDENCE
- verified artifacts
- price scan
- publish calls
- approval receipt

COMPLEXITY DELTA
- generic abstractions added
- product seams added
- duplicate/proof-only code retired

TEST EVIDENCE

STOP DECISION
- `PHASE 2 = 100% — STOP` only if P2-1..P2-8 all PASS
```
