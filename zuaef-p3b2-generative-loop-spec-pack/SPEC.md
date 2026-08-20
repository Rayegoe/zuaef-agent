# SPEC — P3B-2 Generative Agent Loop Separation

**Normative language:** MUST / MUST NOT / SHOULD / MAY
**Repository:** `Rayegoe/zuaef-agent`
**Baseline:** PydanticAI 2.30.0 + PydanticAI Harness 0.20.0 from `uv.lock`

---

# 1. Executive architecture decision

The native PydanticAI Agent Loop is the cognitive and generative center.

```text
User Goal
   ↓
Model-visible context
   ↓
PydanticAI Agent Loop
   ├─ model judgment
   ├─ tool calls when useful
   ├─ tool results
   ├─ further judgment
   └─ natural-language terminal result
   ↓
User Presentation

Host Settlement runs alongside/afterward:
   StepPersistence
   Tool effects
   Artifact verification
   Knowledge verification
   Composition snapshot
   Usage
   Errors
   ↓
   RunReceipt
```

ZUAEF MUST NOT place settlement schemas or business workflow fields in the generic model terminal contract.

---

# 2. Architecture invariants

## INV-1 — Natural terminal output

The default FDE Agent MUST use:

```python
output_type=[str, DeferredToolRequests]
```

or the exact equivalent supported by the pinned PydanticAI version.

`RunSummary` MUST NOT be a model output type.

Before implementation, add a tiny compatibility/probe test against the pinned version if needed. Do not invent a custom loop to achieve this.

## INV-2 — Host-generated settlement

`RunSummary` is a host settlement object.

The runtime, not the model, MUST construct it from:

- terminal presentation;
- runtime exceptions;
- verified artifact diff;
- verified knowledge updates;
- verified tool effects;
- unresolved effects;
- usage;
- composition;
- prior pause state.

The model MUST NOT be asked to provide:

- artifact refs;
- tool-effect IDs;
- receipt paths;
- run IDs;
- host status fields.

## INV-3 — Presentation is separate from receipt

Target shape:

```python
@dataclass(kw_only=True)
class TerminalRun:
    presentation: str
    receipt: RunReceipt
```

A temporary compatibility property MAY expose `summary` if existing callers need it, but user-facing presentation MUST NOT be stored as the long-term `RunSummary.deliverable` contract.

`RunSummary.deliverable` MUST be deprecated in P3B-2 and scheduled for removal from the next receipt schema revision.

## INV-4 — Tools provide capabilities, not workflow

Tool descriptions MAY explain:

- what the tool does;
- valid arguments;
- data/evidence semantics;
- hard constraints;
- side-effect class.

Tool descriptions MUST NOT prescribe a generic completion sequence such as:

```text
read → assess → strategy → save → send → final_result
```

unless the tool itself is literally an atomic deterministic transaction that requires that sequence internally.

## INV-5 — Business judgment remains with the FDE

The production FDE MUST NOT use deterministic semantic strategy engines as the primary decision-maker for customer-service judgment.

Specifically, production model action space MUST remove:

- `assess_customer`
- `select_response_strategy`

from the Client Service toolset.

Their underlying code MAY remain for offline regression, analytics, benchmark comparison, or policy audit.

## INV-6 — Hard policy remains enforceable

The removal of deterministic semantic judgment MUST NOT remove hard guards.

Hard constraints may remain mechanical, including:

- cross-Case isolation;
- authentication/authorization;
- external/destructive approval;
- credential boundaries;
- explicit disclosure bans;
- source/evidence requirements for factual claims;
- budget arithmetic;
- explicit numeric limits.

## INV-7 — Case is context, not workflow

A bound Case contributes durable business background.

Case MUST NOT prescribe:

- which business domain must be loaded;
- the order of tools;
- mandatory `save_artifact`;
- final-output schema;
- receipt/evidence construction;
- delivery unless explicitly requested.

## INV-8 — Case tools are not initially visible

In `stillevo-fde`, the Case business toolset MUST become deferred.

The initial request MAY receive a bounded host-projected Case brief, but MUST NOT automatically expose Case mutation/delivery tool schemas.

## INV-9 — External effects alone trigger approval by default

Default classification remains:

```text
observe        automatic
local_write    automatic
external_write approval
destructive    approval
```

Internal interaction logging, local drafts, local artifacts, and local Case-state writes MUST NOT require approval solely because they are important.

## INV-10 — Gateway remains business-agnostic

Gateway MUST NOT know the Case plugin’s internal draft storage path or naming convention.

Remove the P3B-1 logic that reads:

```text
workspace/cases/<case_id>/drafts/<draft_ref>
```

for approval previews.

The pending external tool call MUST be self-describing enough to render what will happen.

---

# 3. Agent loop contract

## 3.1 Core construction

Current anti-pattern:

```python
output_type=[RunSummary, DeferredToolRequests]
```

Target:

```python
output_type=[str, DeferredToolRequests]
```

`build_agent()` remains a normal PydanticAI Agent constructor. No ZUAEF graph or custom agent loop may be introduced.

## 3.2 Normal terminal

On a natural-language output:

```text
result.output: str
```

runtime MUST create:

```python
TerminalRun(
    presentation=result.output,
    receipt=<host-generated receipt>,
)
```

## 3.3 Paused terminal

On:

```text
result.output: DeferredToolRequests
```

existing PydanticAI pause/resume semantics remain authoritative.

## 3.4 Exceptions and usage boundaries

On runtime failure or usage limit:

- host creates the partial/blocked `RunSummary`;
- `TerminalRun.presentation` contains a bounded user-safe explanation;
- receipt contains the machine detail.

The model is not invoked merely to format an error receipt.

---

# 4. RunSummary and receipt migration

## 4.1 RunSummary target role

`RunSummary` becomes settlement-only:

```python
class RunSummary(BaseModel):
    status: Literal["completed", "partial", "blocked"]
    outcome: str
    artifacts: list[str] = []
    evidence: list[str] = []
    unknowns: list[str] = []
    next_action: str | None = None
    run_id: str | None = None
    receipt: str | None = None
```

`outcome` is a bounded host summary of the terminal state, not the user deliverable.

## 4.2 `deliverable`

For compatibility:

- keep reading old receipts containing `deliverable`;
- stop producing new `deliverable`;
- stop instructing the model about `deliverable`;
- stop rendering new terminals from `receipt.summary.deliverable`.

A later schema migration can remove the field entirely.

## 4.3 Evidence

Host continues to:

- detect changed artifacts;
- verify claimed/observed artifacts;
- settle completed effects from the effect ledger;
- verify knowledge written by the run;
- record unresolved effects.

Model-provided evidence refs are no longer required for normal settlement.

If legacy paths still accept them during migration, they MUST NOT be required for a completed run.

---

# 5. Core instruction contract

Replace the current receipt-oriented core instructions with a small generative contract.

Required semantic content:

```text
You are the single outcome-owning FDE agent.

Own the user's real outcome.

Use available context and tools when they materially help.
Tools are capabilities, not a required workflow.

Distinguish observed facts from assumptions. Do not invent missing facts.

For normal analysis, writing, revision and planning, return the useful result
directly to the current user.

An external or destructive action may only happen through the corresponding
approval-gated tool. Never infer external delivery merely because a customer
Case exists.

Do not claim an external action happened unless the corresponding tool
actually completed.
```

Core instructions MUST NOT contain:

- `RunSummary`;
- `deliverable`;
- `artifact:<...>`;
- `tool-effect:<...>`;
- receipt-writing instructions;
- Case field schemas;
- customer strategy enums.

---

# 6. Case redesign

## 6.1 Case definition

Case is:

> durable business context and state for one customer/project.

Case may contain structured storage internally.

Model-facing Case context SHOULD be a bounded natural-language projection.

## 6.2 Context projection

Add a thin module such as:

```text
src/zuaef_agent/context_projection.py
```

It MAY expose:

```python
project_case_context(case_id, ...) -> str | None
```

It MUST NOT become a new framework.

The projection should provide only task-relevant durable background, for example:

```text
Customer context:

XX Beauty already has its own content-generation and publishing workflow.
The current problem is repeated/template-like content and platform-quality risk.
The supervisor currently prefers demonstrating concrete content improvement
before proposing a broader Agent rebuild.

This is background information, not an instruction sequence.
```

Avoid dumping raw storage schemas such as:

```json
{
  "stage": "...",
  "authority": "...",
  "approval_level": "...",
  "sample_validation": "..."
}
```

unless those exact fields are materially useful to the current task.

## 6.3 Case instructions

Remove from `TOOLSET_INSTRUCTIONS`:

- `load_case_context first`;
- authoring completion workflow;
- ACE routing instructions;
- mandatory `save_artifact`;
- customer delivery workflow as a default;
- RunSummary/evidence instructions;
- hard-coded assumption that current user is always Barry.

Keep:

- Case isolation semantics;
- what each Case tool does;
- provenance rules for durable writes;
- explicit semantics of outbound tools.

## 6.4 Case deferred loading

Change `profiles/stillevo-fde.toml`:

```toml
[[plugins]]
id = "case"
defer_tools = true
```

Host projection supplies background before the model needs Case mutation tools.

---

# 7. Client Service redesign

## 7.1 Production toolset

Production Client Service MUST NOT expose deterministic judgment tools:

```text
assess_customer
select_response_strategy
```

Recommended production surface:

```text
retrieve_client_context
search_client_evidence      # optional thin extraction from existing retrieval
record_interaction
```

## 7.2 Deterministic policy engine

`policy.py`, canonical policies, and structured assessment models MAY remain for:

- regression evaluation;
- offline analysis;
- benchmark comparison;
- policy-audit reports.

They MUST NOT decide the normal FDE response strategy in the production agent loop.

## 7.3 Hard constraints vs soft judgment

Hard constraints remain enforceable.

Soft guidance should be retrieved as precedents / approved business guidance, e.g.:

```text
Past approved decision:
When a low-budget prospect repeatedly asks for complete implementation detail
before confirming authority, give direction and boundaries but do not hand over
an executable solution.
```

The FDE then judges whether that precedent applies.

## 7.4 `record_interaction`

Classify as local write.

Remove generic human approval from internal business-history recording.

If a later interaction recorder writes to an external CRM, that specific external tool may require approval.

---

# 8. Writing redesign

Writing tools remain useful.

`WRITING_RULES` MAY state:

- what ACE owns;
- source/evidence semantics;
- exemplar limitations;
- retrieval budgets;
- claim validation rules;
- `save_artifact` behavior.

`WRITING_RULES` MUST NOT state:

- every writing task must call `save_artifact`;
- every writing task must finish via `final_result`;
- the terminal response schema;
- a mandatory drafting workflow.

`save_artifact` is optional unless the user/task/domain requires persistence.

A pasted text with no legitimate ACE article/material identity may be rewritten and returned successfully with zero artifact.

---

# 9. Budget redesign

Deterministic budget computation remains production-authoritative for arithmetic and rule-based numeric checks.

Keep:

- parse;
- summary;
- variance;
- consistency;
- health calculations;
- queries;
- significant-change detection.

Remove instructions that require:

- `save_budget_report` on every task;
- `RunSummary.artifacts` declarations.

The FDE interprets deterministic results in natural language.

---

# 10. Approval and outbound payload

## 10.1 Approval semantics

Keep native PydanticAI approval.

Approval is triggered only by the effectful tool definition, never by semantic importance.

## 10.2 Self-describing outbound call

Modify customer send so the pending tool call carries the actual content to be sent.

Preferred target:

```python
send_to_customer(
    text: str,
    draft_ref: str | None = None,
)
```

If Case binding is required, Case identity remains server-owned through `CoreDeps`; the model need not choose a Case ID.

## 10.3 Exact payload invariant

The content displayed to the supervisor during approval MUST equal the content executed after approval.

No host-side lookup that could silently change between preview and execution.

The Gateway renders generic tool arguments/payload and remains unaware of Case storage layout.

---

# 11. Model-visible surface contract

Create `tests/test_model_surface_contract.py`.

For a normal bound-Case authoring request, capture the real first model request.

It MUST include only relevant generative context/capabilities.

It MUST NOT contain:

```text
RunSummary
deliverable
final_result settlement schema
artifact evidence instructions
tool-effect
approval_level
disclosure_ceiling
CustomerAssessment
select_response_strategy
save_draft
send_to_customer
update_situation
record_case_step
mandatory ACE workflow instructions
```

unless a deferred capability was explicitly discovered/loaded later.

---

# 12. Golden regressions

## G1 — unbound authoring

Input:

```text
<article>
改写这篇文章
```

Required:

- natural text result;
- 0 approval;
- no Case requirement;
- artifact optional.

## G2 — bound Case authoring

Same input with a bound Case.

Required:

- same natural behavior;
- Case background may inform writing;
- no outbound action;
- 0 approval.

## G3 — revision continuity

Input:

```text
开头还是太像 AI，第二段别动，其他地方保持。
```

Required:

- natural revision;
- real prior conversation history;
- no field-filling workflow.

## G4 — customer judgment

Input:

```text
这个客户一直两三天问一次案例，但又不拍板，你判断一下现在怎么回。
```

Required:

- FDE judgment;
- contextual retrieval may occur;
- no production `select_response_strategy`.

## G5 — budget reasoning

Input:

```text
算一下为什么这个预算超了，告诉我真正需要关注什么。
```

Required:

- deterministic arithmetic;
- LLM interpretation;
- no mandatory report artifact.

## G6 — explicit send

Input:

```text
这版可以，发给客户。
```

Required:

- outbound tool;
- native approval pause;
- exact content visible.

## G7 — approve/deny

Approve:

- exact payload executes once.

Deny:

- zero external execution.

---

# 13. Structural tests

Add tests that prove architecture, not just one scripted behavior:

1. Agent output surface no longer includes `RunSummary` output tool.
2. Host-generated receipt remains complete after natural-string terminal.
3. Normal authoring does not require an artifact to complete.
4. Deferred Case tools are absent initially.
5. Client Service deterministic strategy tools are absent in production.
6. Gateway has no Case draft filesystem knowledge.
7. Native approval pause/resume survives the refactor.
8. StepPersistence continuity remains intact.

---

# 14. Real-model proof

Run one disposable real-model proof through:

```text
GatewayService
+ profile=stillevo-fde
+ real StepPersistence
+ optional bound Case
```

### Turn 1

Paste the “夏天的指尖” article and:

```text
改写这篇文章
```

Expect:

- direct rewritten text;
- 0 approval;
- no forced ACE ingest;
- artifact may be 0.

### Turn 2

```text
开头还是太像 AI，第二段别动，其他地方保持。
```

Expect:

- real continuation;
- natural revision.

### Turn 3

```text
这版可以，发给客户。
```

Expect:

- native approval;
- exact outbound payload visible.

The disposable proof script must not be committed unless it becomes a stable general regression tool.

---

# 15. Forbidden implementation patterns

Do not implement P3B-2 by adding:

- custom model router;
- custom agent graph;
- workflow status machine;
- semantic intent enum;
- `task_type` classifier;
- new generic business schema;
- new output envelope containing presentation + settlement fields;
- a new policy engine.

The fix is removal/repositioning, not replacement machinery.

---

# 16. Required file set

Expected touched files:

```text
src/zuaef_agent/core.py
src/zuaef_agent/models.py
src/zuaef_agent/runtime.py
src/zuaef_agent/context_projection.py          # new, thin
src/zuaef_agent/gateway/bridge.py
src/zuaef_agent/gateway/renderer.py
src/zuaef_agent/gateway/service.py

profiles/stillevo-fde.toml

plugins/zuaef-case/zuaef_case/toolset.py
plugins/zuaef-client-service/zuaef_client_service/toolset.py
plugins/zuaef-client-service/zuaef_client_service/policy.py   # production path only
plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py
plugins/zuaef-emtb-budget/zuaef_emtb_budget/toolset.py

tests/test_core.py
tests/test_runtime.py
tests/test_gateway_service.py
tests/test_gateway_renderer.py
tests/test_case_plugin.py
tests/test_client_service_plugin.py
tests/test_model_surface_contract.py           # new

README.md
docs/agent-loop-contract.md                     # new
BUILD_MANIFEST.json
```

Exact file names may differ if the repository structure proves otherwise; preserve the architecture, not the list mechanically.

---

# 17. Stop gates

All must pass:

- **L1** generic FDE output is natural text + deferred approvals.
- **L2** `RunSummary` is not model-facing.
- **L3** receipts are host-generated.
- **L4** authoring can succeed with zero artifact.
- **L5** Case no longer defines workflow.
- **L6** Case mutation/delivery tools are deferred.
- **L7** Client Service deterministic strategy is absent from production path.
- **L8** local interaction recording is automatic.
- **L9** external/destructive effects remain approval-gated.
- **L10** Gateway has no Case draft storage coupling.
- **L11** G1–G7 deterministic regressions pass.
- **L12** model-visible surface contract passes.
- **L13** StepPersistence continuity passes.
- **L14** full pytest passes.
- **L15** Ruff passes.
- **L16** manifest matches.
- **L17** real-model three-turn proof passes.

Only then print:

```text
P3B-2 = 100% — STOP
```
