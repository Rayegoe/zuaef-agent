# ZUAEF Phase 2 — Product Completion SPEC v1.0

Status: Executable
Target: `Rayegoe/zuaef-agent`

---

# 0. Executive decision

Phase 1 solved substrate ownership.

Phase 2 must prove the product.

The target is:

> A real bound customer conversation enters the Gateway, the one `stillevo-fde` Agent knows which Case it owns, sees only a compact initial business surface, loads the relevant domain capability when needed, uses real customer material, produces/updates a verified artifact, respects approval/side-effect policy, and carries the user's correction into the next turn.

---

# 1. Phase 2 north-star flow

```text
Surface event
    ↓
Gateway SessionBinding
    ↓
deterministic Case binding
    ↓
profile = stillevo-fde
    ↓
one FDE Agent
    ↓
Case context first
    ↓
ToolSearch / deferred business capability discovery
    ↓
load only relevant business domains
    ↓
Act
    ↓
Artifact / Draft
    ↓
Approval if customer-visible external commitment
    ↓
Receipt / Case trajectory
    ↓
next inbound turn
    ↓
same Case + same conversation, fresh run
```

No separate `WritingAgent`, `NegotiationAgent`, `FDELoopAgent`, or router.

---

# 2. Definition of Phase-2 100%

Phase 2 is 100% only when all are true:

1. `stillevo-fde` has explicit deployment-level generalist authorization.
2. Gateway sessions can be deterministically bound to exactly one Case.
3. Bound Case identity constrains Case operations; the model cannot silently act on another Case.
4. Business domains in `stillevo-fde` use real progressive disclosure instead of dumping all tool schemas into every turn.
5. A real two-turn customer-demo task runs through the production-like Gateway using `profile="stillevo-fde"`.
6. Turn 2 succeeds without the host restating Turn-1 constraints.
7. Customer-visible send remains approval-gated.
8. Real customer/Case materials, not synthetic prompt restatements, ground the draft.
9. Artifact verification, Case trajectory, StepPersistence and receipts all settle.
10. Existing business regressions and the full test/lint suite pass.
11. README/example config reflects the actual product.
12. No new generic ZUAEF harness abstraction was introduced.

Once these pass: STOP.

---

# 3. Deployment-level generalist authorization

## 3.1 Current problem

Generalist primitives are currently authorized primarily through process-level `AgentSettings` flags.

A Gateway process can switch profiles, so process-global flags are not sufficient as deployment policy.

## 3.2 Required model

Use two layers:

```text
HOST CEILING
    ∩
PROFILE REQUEST
    =
EFFECTIVE CAPABILITY AUTHORIZATION
```

Host ceiling answers whether the process/environment may ever expose the capability.

Profile request answers whether this deployment needs/permits the capability.

The model decides neither.

## 3.3 Minimal profile shape

Add one small top-level profile policy model. Exact names may vary, but semantics must be equivalent:

```toml
[generalist]
web_search = true
web_fetch = true
tool_search = true
memory = true
conversation_search = true
context_controls = true
subagents = true

shell = false
repo_context = false
```

Do not create RBAC, policy engines, permission graphs, or tenant ACL frameworks.

## 3.4 Backward compatibility

Existing profiles without `[generalist]` must keep current narrow behavior.

No-profile CLI runs may continue using direct host settings.

## 3.5 Frozen identity

Effective profile generalist policy must be included in `CompositionSnapshot` identity so pause/resume reproduces the same deployment authority.

A profile change after pause must not alter resumed capabilities.

---

# 4. Business-domain progressive disclosure

## 4.1 Current problem

`stillevo-fde` composes multiple business plugins, but existing plugin toolsets are flattened into the Agent.

This can make all business tool schemas visible together even when only one domain is relevant.

## 4.2 Required design

Use released PydanticAI deferred-loading / ToolSearch primitives.

Do NOT rewrite business plugins.

The smallest acceptable design is a deployment/composition flag such as:

```toml
[[plugins]]
id = "ace-writing"
defer_tools = true
```

Exact syntax may vary.

The composition layer may mechanically wrap an existing plugin toolset in released `DeferredLoadingToolset` or equivalent public primitive.

No new capability registry.

## 4.3 `stillevo-fde` initial policy

Recommended:

```text
zuaef-case          eager / always available
client-service      deferred
ace-writing         deferred
zuaef-emtb-budget   deferred
wordpress           deferred
```

Case is the FDE business orientation layer. Other domains enter active context only when needed.

## 4.4 Required proof

For `stillevo-fde`:

Before loading a domain:

```text
Case tools + compact discovery are visible
Writing/Budget/WordPress full tool schemas are not all present
```

For a writing request:

```text
writing capability/toolset loads
client-service may load if useful
budget stays dormant
wordpress stays dormant unless publication is actually requested
```

Proof must inspect the model-visible tool surface, not an internal registry.

---

# 5. Gateway → Case binding

## 5.1 Product requirement

A field FDE cannot infer customer identity from free text.

A channel/thread/session must be mechanically bound to a Case.

No LLM identity guessing.

## 5.2 Required state

Extend Gateway routing state with:

```text
case_id: str | None
```

Conversation identity and Case identity stay separate:

```text
conversation_id = this dialogue lifecycle
case_id         = this business relationship/work item
```

Do not force `conversation_id == case_id`.

## 5.3 Binding storage

Use the existing Gateway SQLite control-plane store.

Add the smallest durable mapping needed for:

```text
surface + tenant + channel + thread
→ case_id
```

No new database/service.

## 5.4 Binding operation

Provide one deterministic supervisor/admin path to bind a channel/thread to a Case.

Preferred minimum:

```text
GatewayStore.bind_case(...)
+
one thin CLI/admin command that writes the binding
```

Do not let the model bind itself to a Case.

## 5.5 Inbound behavior

On each ordinary inbound run:

1. resolve the session's bound `case_id`;
2. reject or run non-case mode according to deployment policy if none is bound;
3. for `stillevo-fde`, include bound Case identity mechanically;
4. the FDE must load Case context before consequential business action.

## 5.6 Case isolation

Add optional `case_id` to `CoreDeps` or equivalent server-owned execution dependency.

When a run is bound to a Case, Case tools must reject attempts to read/write/send for a different `case_id`.

Backward-compatible unbound CLI/test behavior may remain where explicitly required.

This is a business authorization boundary, not prompt guidance.

---

# 6. Case → business capability references

## 6.1 Problem

The old `examples/fde_loop.py` can write from real Case materials because custom proof glue knows the ACE article/material mapping.

The production `stillevo-fde` path must not depend on that custom runner.

## 6.2 Required solution

Store business-resource references in ordinary Case state/material metadata, not in a new orchestration layer.

For the proof Case, Case context must expose enough deterministic information for the FDE to reach the existing ACE writing capability, e.g.:

```json
{
  "resources": {
    "ace_article_id": "fde-case-stillevo-beauty"
  }
}
```

or an equivalent existing field.

The exact representation may live in `situation.state` because it is already an open business-state mapping.

## 6.3 Material provenance

Customer facts and product claims must still come from real Case/ACE material records.

Do not copy entire customer background into the prompt as a substitute for Case/material retrieval.

---

# 7. Golden Outcome — authoritative Phase 2 proof

The authoritative proof must use:

```text
GatewayService
profile = stillevo-fde
bound case = stillevo-beauty (or equivalent real repo Case fixture)
real model
real StepPersistence
real Case store
real ACE material ingestion
real artifact verification
real receipts
```

A recording/fake transport surface is acceptable for deterministic capture, but execution must go through the real Gateway service.

## 7.1 Turn 1

Send only:

```text
客户觉得上一篇 demo 太模板化。
结合他之前给的背景和材料重写一篇。
价格先不要写，我看完再决定要不要发。
```

Do not append hidden editorial instructions that restate customer background or the no-price constraint.

Expected:

1. session resolves bound Case;
2. Case context is loaded;
3. writing domain is discovered/loaded;
4. relevant customer material is retrieved;
5. a revised article/draft is created;
6. no price is written;
7. WordPress publish is not called;
8. customer-visible send, if attempted, pauses for approval;
9. artifact/draft and decision are recorded.

## 7.2 Turn 2

Send only:

```text
开头还是太像 AI，保留刚才客户背景，再改一版；其他要求不变。
```

Forbidden host addition:

```text
“上一轮客户说过不要价格……”
```

or equivalent reminder.

Expected:

- prior message history is model-visible;
- same `case_id`;
- same `conversation_id`;
- fresh `run_id`;
- no-price constraint still holds;
- prior customer background/material refs are reused;
- article/draft is revised;
- irrelevant domains remain dormant.

## 7.3 Approval

If `send_to_customer` is proposed:

```text
PausedRun
→ supervisor approve
→ shared resume_paused_run
→ same conversation_id + same case_id
→ customer-visible send
```

A deny path must remain valid.

---

# 8. What the proof must NOT do

Automatic proof failure:

```text
profile="ace-writing"
custom build_agent(...) replacing stillevo-fde
custom FDE toolset used only by the proof
hard-coded customer background in the Turn prompt
host restating Turn-1 constraints in Turn 2
directly calling writing implementation instead of Agent tool choice
automatic WordPress publish
bypassing approval
creating a second Case store
creating a second conversation store
```

Proof may perform mechanical fixture preparation only:

```text
ensure Case fixture exists
ingest bytes
bind source hashes/material ids
bind Gateway channel to case
send inbound envelopes
capture outputs/evidence
```

---

# 9. Existing proof paths

## 9.1 `examples/fde_loop.py`

Do not delete its historical evidence immediately.

Reuse only deterministic fixture preparation if useful.

Its custom runtime/tool composition must stop being the product authority once the new Gateway `stillevo-fde` proof passes.

After the gate, mark it historical/diagnostic or simplify it to production seam if trivial.

Do not maintain two FDE architectures.

## 9.2 `tools/fde_two_turn_proof.py`

Replace or rewrite it.

Final authoritative tool must use GatewayService, `stillevo-fde`, bound Case, literal turns, and capture loaded/invoked/dormant domains plus artifacts/receipts/history.

Do not create a second proof framework.

---

# 10. Documentation completion

Update at least:

```text
README.md
.env.example
profiles/stillevo-fde.toml
relevant Gateway docs
```

README must stop claiming generic Memory/SubAgent capability is absent if the platform now provides those upstream primitives.

Document:

```text
available
≠ authorized
≠ loaded
≠ invoked
```

Document how a supervisor binds a Gateway channel/thread to a Case.

---

# 11. Phase 2 acceptance gates

Only these gates define 100%.

## P2-1 — Deployment authorization

PASS when:

- profile generalist policy exists;
- effective authorization = host ceiling ∩ profile request;
- policy is frozen in composition identity;
- existing profiles remain compatible.

## P2-2 — Domain progressive disclosure

PASS when `stillevo-fde` proves:

- Case is available initially;
- full Writing/Budget/WordPress surfaces are not all injected initially;
- writing loads on writing task;
- unrelated domains remain dormant.

## P2-3 — Case binding and isolation

PASS when:

- channel/session deterministically resolves a Case;
- bound `case_id` reaches execution deps;
- Case tools reject cross-case access for a bound run;
- no model identity guessing exists.

## P2-4 — Real FDE Turn 1

PASS when Turn 1 through Gateway + `stillevo-fde`:

- uses Case/materials;
- produces usable verified draft/artifact;
- contains no forbidden price;
- does not publish;
- records receipt/trajectory.

## P2-5 — Real FDE Turn 2

PASS when Turn 2:

- receives no hidden restatement;
- visibly inherits prior message history;
- keeps same Case/conversation;
- revises result;
- preserves old constraints.

## P2-6 — Approval

PASS when customer-visible send:

- pauses;
- approve resumes through shared seam;
- deny works;
- Case/conversation identity survives resume.

## P2-7 — Regression

PASS when:

```bash
uv run pytest -q
uv run ruff check .
```

plus existing writing, budget, client-service, WordPress, Case, Gateway and resume proofs all pass.

## P2-8 — Product documentation

PASS when README/profile/env examples describe actual behavior.

When P2-1 through P2-8 pass:

```text
PHASE 2 = 100%
STOP.
```

---

# 12. Forbidden Phase 2 work

Do not add:

```text
new generic capability framework
new agent registry
intent router
workflow graph
event bus
new database
vector DB
generic RBAC framework
custom ToolSearch
custom Memory
custom ConversationSearch
custom history repair
custom persistence engine
new specialist default agents
mass rewrite of all plugins
new UI/dashboard
new channel adapter
```

Feishu/Slack/WeChat expansion belongs after this phase.

---

# 13. Positive feedback / stop discipline

Successful outcomes:

```text
KEEP
Phase-1 substrate already works; do not touch it.

WRAP
Existing business Toolset is mechanically wrapped by upstream deferred loading.

DELETE
A proof-only/custom path becomes unnecessary after production seam passes.

DORMANT
An authorized domain is correctly not loaded/invoked for the task.

PASS
The real FDE outcome works.

STOP
P2-1..P2-8 pass. Do not invent a Phase 2.5 harness project.
```

Desired complexity delta:

```text
business product seams   +small
generic ZUAEF framework  +0
duplicate proof/runtime  -some
```
