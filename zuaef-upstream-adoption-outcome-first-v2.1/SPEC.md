# ZUAEF Upstream Adoption — Outcome-First SPEC v2.1

Status: **Executable**
Target repository: `Rayegoe/zuaef-agent`

---

# 0. Executive decision

ZUAEF is an **FDE application layer** built on PydanticAI and Pydantic AI Harness.

It must become a **generalist-capable platform**, which means the standard general execution primitives are available to the same FDE Agent.

The governing architecture is:

```text
PydanticAI
    Agent loop / providers / tool semantics / capabilities / history / deferred tools
        │
Pydantic AI Harness
    reusable generalist execution capabilities
        │
════════╪════════  ZUAEF ownership boundary
        │
ZUAEF
    FDE business state / domain capabilities / evidence / verification / settlement / surfaces
```

The Outcome-First rule is NOT:

> “Do not integrate a capability until a case fails without it.”

The correct rule is:

> **Integrate the generalist capability surface once using upstream primitives; keep the active context and actual tool use task-driven.**

---

# 1. Product outcome

The target product is one FDE Agent that can receive arbitrary natural-language work within its authorization boundary and decide what it needs.

Example:

```text
客户觉得上一篇 demo 太模板化。
结合他之前给的背景和材料重写一篇。
价格先不要写，我看完再决定要不要发。
```

The same deployment should be capable of deciding whether it needs:

```text
Case
Knowledge
Writing
Web
Files
Shell
RepoContext
Planning
Memory
ConversationSearch
SubAgent
WordPress
Budget
other business capabilities
```

without the user selecting a task-specific agent.

The important distinction is:

```text
capability exists
≠ capability is loaded
≠ capability is called
```

---

# 2. Outcome-First capability lifecycle

This section is normative.

Every general capability must be understood through five independent states.

## 2.1 AVAILABLE

The capability is installed/composable in the runtime and covered by smoke tests.

This is a platform responsibility.

## 2.2 AUTHORIZED

The current deployment/user/tenant is allowed to use it.

Examples:

```text
Shell allowed for trusted local operator
Shell disabled for untrusted public Gateway
WordPress publishing available only for the correct tenant/site
destructive actions require stronger policy
```

Authorization is not model judgment.

## 2.3 DISCOVERABLE

The model can learn that the capability exists through a compact catalog/tool-search/deferred-capability representation.

The full implementation should not enter every prompt.

## 2.4 LOADED

The capability's instructions/toolset enter the active context because the current task justifies it.

## 2.5 INVOKED

The model actually calls it.

A capability can be:

```text
AVAILABLE + AUTHORIZED + DISCOVERABLE
```

while correctly remaining:

```text
NOT LOADED + NOT INVOKED
```

for a particular task.

That is successful progressive disclosure, not missing functionality.

---

# 3. Capability-complete, context-minimal rule

The baseline target is:

```text
broad platform capability surface
+
small active context
+
smaller actual action set
```

This avoids both failure modes:

## Failure A — capability-poor platform

```text
natural-language task arrives
→ required primitive does not exist
→ engineer must first extend the platform
```

This is unacceptable for the intended generalist FDE core.

## Failure B — capability dump

```text
every capability
+ every tool schema
+ every skill
+ every domain workflow
→ injected into every turn
```

This is also unacceptable.

Correct design:

```text
complete capability surface
→ compact discovery
→ selective load
→ selective invocation
```

---

# 4. Required generalist capability surface

Where the selected released PydanticAI/Harness pair provides a public implementation, ZUAEF MUST integrate the following baseline primitives.

## 4.1 Core execution

```text
FileSystem
Shell
RepoContext
Planning
Skills
ToolOutputLimits
StepPersistence
```

## 4.2 Research

```text
WebSearch
WebFetch
```

## 4.3 Progressive disclosure

```text
ToolSearch and/or released on-demand capability loading
```

## 4.4 Context management

```text
released compaction / clear-tool-results / context-window controls
```

## 4.5 Long-horizon recall

```text
Memory
ConversationSearch
```

These do not replace Case or evidence-backed Knowledge.

## 4.6 Task isolation

```text
SubAgents
```

SubAgents must be available as a platform primitive if released and stable, but they MUST NOT become the default execution pattern.

## 4.7 Optional advanced primitives

Capabilities such as:

```text
CodeMode
browser automation
durable workflow integrations
provider-specific built-in tools
```

may be integrated when they are part of the intended supported deployment surface.

They must not cause ZUAEF to reimplement upstream infrastructure.

---

# 5. Default activation policy

Availability does not mean global activation.

The default policy should be approximately:

| Capability | Available | Default loaded? | Invocation policy |
|---|---:|---:|---|
| FileSystem | YES | YES/compact | normal workspace work |
| Planning | YES | YES/compact | model may use for multi-step tasks |
| Skills | YES | catalog | load relevant skill only |
| ToolOutputLimits | YES | host-side | always active |
| StepPersistence | YES | host-side | always active |
| WebSearch/WebFetch | YES | compact/catalog | invoke for external/current evidence |
| ToolSearch | YES | compact | use when capability/tool catalog is large |
| Shell | YES | deployment policy | invoke only in authorized execution environments |
| RepoContext | YES | repo mode | load for repository/code tasks |
| Compaction/context controls | YES | host-side | activate based on context pressure policy |
| Memory | YES | catalog/host | read/write according to memory policy |
| ConversationSearch | YES | catalog | invoke for relevant long-history retrieval |
| SubAgents | YES | catalog | invoke only for isolated/parallelizable work |

The exact constructor/API may differ by released upstream version.

The behavior contract matters more than class names.

---

# 6. Positive-feedback policy

This is normative.

## 6.1 READY is success

When a general capability is correctly integrated and tested:

```text
READY
```

is a deliverable.

No fake business case is required merely to justify its existence.

## 6.2 DORMANT is success

If a task does not need a capability and the model does not load/call it:

```text
DORMANT
```

is correct behavior.

Example:

```text
internal client-writing task
→ no web needed
→ WebSearch remains dormant
```

This is better than either removing WebSearch from the platform or calling it unnecessarily.

## 6.3 LOAD is evidence

Loading a capability should have a reason visible from the task.

Example:

```text
"check the latest WordPress API behavior"
→ load web research capability
```

## 6.4 INVOKE is outcome-driven

Tools/actions should be invoked only when they help complete the user's outcome.

The model should not exercise capabilities for demonstration.

## 6.5 KEEP / DELETE / REUSE

Keep the earlier Outcome-First rules:

```text
KEEP   existing thin ZUAEF business semantics
DELETE local generic duplication
REUSE  released upstream public primitives
```

## 6.6 STOP

Once:

```text
baseline capability surface ready
+
progressive disclosure works
+
real FDE case works
+
regression passes
```

STOP building generic harness abstractions.

---

# 7. Complexity budget

Capability completeness does NOT authorize framework proliferation.

Default budget:

```text
new generic framework classes: 0
new generic persistence systems: 0
new intent routers: 0
new default domain agents: 0
new workflow engines: 0
new vector stores: 0
new custom web/search stacks: 0
new custom provider-profile frameworks: 0
```

The platform can be capability-rich while ZUAEF-specific infrastructure remains thin.

This is the intended architecture.

---

# 8. Ownership boundary

## 8.1 PydanticAI owns

Do not reimplement:

```text
Agent loop
tool scheduling / validation / retries
tool call/result pairing
generic toolset composition
message-history repair
deferred tool protocol
generic approval mechanics
WebSearch/WebFetch primitives
ToolSearch/on-demand loading
provider/model capability profiles
durable-execution framework
web UI event protocol
```

## 8.2 Harness owns

Use released public APIs for:

```text
FileSystem
Shell
RepoContext
Planning
Skills
ToolOutputLimits
StepPersistence
Memory
ConversationSearch
context management
SubAgents
other generic harness capabilities
```

## 8.3 ZUAEF owns

Retain:

```text
deployment identity
Case / Situation / stakeholders / trajectory
business capabilities
client-service decision policy
writing/budget/WordPress/hardware-scout behavior
evidence-backed Knowledge
artifact/provenance verification
business effect policy
RunReceipt / PauseReceipt
Gateway session/tenant/auth binding
Telegram / Feishu / Slack / WeChat adapters
```

---

# 9. Memory separation

Three different forms of “memory” must stay distinct.

```text
Conversation history
    exact/working conversational context

Harness Memory
    general persistent model notes/preferences/working recall

ZUAEF Case
    durable business situation, actors, decisions, constraints

ZUAEF Knowledge
    reusable evidence-backed knowledge with provenance
```

ConversationSearch searches prior conversation material.

Harness Memory does not replace Case.

Harness Memory does not replace evidence-backed Knowledge.

---

# 10. SubAgent policy

SubAgents are a baseline available primitive, not a default topology.

Correct use:

```text
main FDE Agent owns outcome
→ delegates a bounded isolated task when useful
→ subagent has reduced scope/permissions/context
→ main Agent receives inspectable result/evidence
```

Default use is still single-Agent.

The model may choose a SubAgent when:

- task is independently bounded;
- isolation reduces context load;
- parallel work is beneficial;
- permissions can be narrowed;
- result can be independently inspected.

The system must not route every domain through specialist agents.

---

# 11. ToolSearch policy

ToolSearch/on-demand capability loading is baseline infrastructure because the intended platform will accumulate many domains.

Its purpose is not to fix a current bug.

Its purpose is to keep:

```text
capability surface ↑
while
active tool/context surface stays bounded
```

The platform must prove:

```text
capability is discoverable
full tool definitions are not always injected
model can load relevant capability
irrelevant capability remains dormant
```

This is a structural requirement of the platform, not speculative overengineering.

---

# 12. Context-management policy

Context management is also baseline infrastructure.

The system should provide released upstream controls for:

```text
tool output limits
clearing stale tool results
compaction/context windows
warnings/thresholds
```

The policy may activate based on thresholds.

Do not wait for production context overflow before integrating the primitive.

Do not write a custom summarization framework.

---

# 13. Provider migration

Use official providers/profiles where the selected release supports the deployment.

For DeepSeek, upstream owns generic compatibility behavior.

Local provider code may remain only for deployment-specific transport/configuration.

If official behavior passes:

```text
DELETE local duplicated compatibility
```

and stop.

---

# 14. StepPersistence

Execution trajectory belongs upstream.

Business settlement belongs to ZUAEF.

```text
StepPersistence = execution truth
RunReceipt      = business settlement truth
```

Use public StepStore APIs.

No direct backend file parsing.

---

# 15. Conversation continuity

`conversation_id` is correlation, not context.

Normal follow-up:

```text
Gateway session
→ prior server-authoritative run
→ public persistence/history restore
→ message_history
→ fresh run_id
→ same conversation_id
→ Agent.run(...)
```

Pause/resume uses the same history semantics plus DeferredToolResults.

Do not create a second conversation database unless public upstream persistence is proven insufficient.

---

# 16. Deployment composition

Existing plugin/profile composition may remain for:

```text
package discovery
version/config resolution
deployment identity
frozen composition snapshot
authorization policy
```

It must not become a second runtime for:

```text
tool lifecycle
capability activation semantics
tool conflicts
history
approval
tool search
```

Business packages should progressively expose native PydanticAI Capability/Toolset forms when low-risk, but mass migration is not required for this SPEC.

---

# 17. Required implementation scope

## P0 — release baseline

Pin a tested released PydanticAI/Harness pair.

## P1 — delete duplicated generic infrastructure

At minimum address:

```text
custom generic tool-conflict preflight
private StepPersistence file parsing
duplicated DeepSeek/provider profile logic
```

## P2 — complete baseline generalist capability surface

Integrate the capabilities in Section 4 using upstream public APIs.

Where a capability is unavailable in the selected release:

```text
document RELEASE GAP
use the nearest released public primitive
do not silently reimplement upstream
```

## P3 — progressive disclosure / activation policy

Prove that capability availability is broad while loaded/invoked context remains selective.

## P4 — real normal-turn continuity

Restore actual prior message history.

## P5 — preserve business invariants

Case, Knowledge, verification, approval, receipts, domain tools.

## P6 — real FDE proof

Run the two-turn Golden Outcome.

---

# 18. Acceptance gates

## CAP-1 — capability surface ready

PASS when the released baseline capabilities are integrated/testable, or a specific release gap is documented.

This is about availability, not invocation.

## CAP-2 — selective activation works

PASS when tests prove:

```text
relevant capability can be discovered/loaded/invoked
irrelevant capability remains dormant
```

No full tool dump is required.

## CAP-3 — less duplicated ZUAEF infrastructure

PASS when generic duplication has been removed where upstream owns it.

## CAP-4 — real continuity

PASS only if Turn 2 receives prior model-visible history.

## CAP-5 — FDE business proof

PASS when the real two-turn FDE scenario produces a usable artifact, preserves constraints, avoids unauthorized publish, and settles a receipt.

## CAP-6 — regression

PASS when:

```bash
uv run pytest -q
uv run ruff check .
```

and existing domain proofs pass.

Once CAP-1 through CAP-6 pass:

```text
STOP generic harness work.
```

---

# 19. Forbidden architecture

Still forbidden:

```text
IntentRouterAgent
domain Agent registry as default topology
ZUAEFGeneralistHarness framework
custom WebSearch/WebFetch
custom ToolSearch
custom message-history repair
custom checkpoint/replay runtime
private Harness file parsing
copying provider capability flags
new event bus
new vector database
new workflow graph engine
automatic specialist-agent routing
```

Capability completeness must come from upstream composition, not local framework invention.

---

# 20. Final rule

For platform primitives:

```text
MAKE AVAILABLE ONCE
AUTHORIZE BY DEPLOYMENT
DISCOVER COMPACTLY
LOAD WHEN RELEVANT
INVOKE WHEN USEFUL
```

For ZUAEF business engineering:

```text
KEEP IT THIN
KEEP IT OUTCOME-OWNING
STOP WHEN THE REAL FDE OUTCOME WORKS
```
