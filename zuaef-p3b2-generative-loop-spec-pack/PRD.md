# PRD — P3B-2 Generative Agent Loop Separation

**Product:** ZUAEF / Stillevo FDE
**Phase:** P3B-2
**Status:** Ready for implementation
**Primary user:** Supervisor/operator using the FDE through Telegram now and other surfaces later.

---

## 1. Problem statement

ZUAEF has repeatedly reproduced the same failure mode in different forms:

1. A business problem is converted into structured fields.
2. Deterministic policies or workflow instructions decide what the fields imply.
3. Tool schemas and approval gates become the most salient model-visible actions.
4. The LLM is reduced to selecting tools, filling schemas, or polishing text.
5. The system remains auditable but stops behaving like an outcome-owning FDE.

The field failure that triggered P3B-1 is representative:

- User pasted an article and asked: **“改写这篇文章”**.
- The system treated a normal authoring task as a customer-delivery workflow.
- `save_draft → send_to_customer → approval` became the effective completion path.
- The user did not receive the rewritten article directly.

P3B-1 repaired the immediate UX by adding `RunSummary.deliverable` and narrowing delivery instructions. The deeper product defect remains: **the model's terminal contract is still a machine settlement schema, and business plugins still contain workflow/decision logic that steers generation.**

---

## 2. Product thesis

ZUAEF is not a workflow engine with an LLM attached.

ZUAEF is a supervised FDE execution system in which:

- the LLM owns interpretation, judgment, planning, composition, and language;
- deterministic code owns facts that should be deterministic;
- tools expose capabilities rather than prescribe workflows;
- host code owns authority, isolation, persistence, verification, and receipts;
- only true external or destructive effects require approval.

The product must feel like:

> “I tell the FDE what outcome I want; it understands the context, uses tools when useful, and gives me the result.”

It must not feel like:

> “I must drive a hidden workflow by triggering fields, tools, gates, and commands in the expected order.”

---

## 3. User outcomes

### UO-1 — Natural authoring

Given a pasted article and “改写这篇文章”, the user receives the rewritten article directly.

No Case is required.
No approval is required.
No artifact is required unless there is a legitimate reason to persist one.

### UO-2 — Bound Case does not hijack intent

If the same authoring request happens while a customer Case is bound, the Case contributes relevant background only.

The mere existence of a customer Case must **not** imply:

- customer delivery,
- customer-service strategy selection,
- mandatory artifact saving,
- mandatory Case writes,
- approval.

### UO-3 — FDE judgment remains generative

For requests such as:

- “这个客户现在应该怎么回复？”
- “为什么他一直不拍板？”
- “这篇到底哪里像 AI？”
- “这个预算真正的问题是什么？”

the FDE performs the semantic/business judgment.

Deterministic tools may provide facts, calculations, retrieval, hard constraints, or evidence, but may not replace the central judgment with a strategy enum or field-matching engine.

### UO-4 — External actions remain safe

When the user explicitly asks:

- “发给客户”
- “发布到 WordPress”
- “把邮件发出去”
- “修改生产数据”

the corresponding external/destructive tool remains approval-gated.

### UO-5 — Audit remains intact without burdening the model

Receipts, artifacts, effects, usage, persistence, and verification remain durable.

The model does not need to compose or restate audit metadata for the host.

---

## 4. Product principles

### P1 — Judgment belongs to the model

If the answer depends on interpretation, trade-offs, business sense, rhetoric, taste, or context, the model owns the decision unless a hard policy explicitly forbids an action.

### P2 — Determinism belongs to facts and hard constraints

Good deterministic responsibilities:

- arithmetic,
- file existence,
- hashes,
- IDs,
- parsing,
- access control,
- Case isolation,
- side-effect classification,
- explicit hard limits,
- source/evidence validation.

Bad deterministic substitutions:

- customer value,
- negotiation strategy,
- whether to disclose a solution,
- narrative angle,
- what the “real problem” is,
- which reply strategy should be used.

### P3 — Guard, don’t guide

A guard says:

> “You cannot send this without approval.”

A workflow instruction says:

> “After writing, send this for approval.”

P3B-2 permits the first and removes the second.

### P4 — Model-visible means intentionally generative

Any content shown to the LLM changes the probability distribution of its next output.

Therefore every model-visible schema, field, instruction, and tool description must pass this test:

> **Do we intentionally want this content to influence the model’s judgment or next-token distribution?**

If not, it must stay host-side.

### P5 — Presentation and settlement are different products

The user sees the work product.

The system records the execution evidence.

Neither substitutes for the other.

---

## 5. Scope

P3B-2 includes:

- agent terminal-output contract;
- runtime settlement;
- Core instructions;
- Case model-facing behavior;
- Case tool loading policy;
- Client Service production decision path;
- Writing tool instructions;
- Budget tool instructions;
- approval-preview decoupling;
- structural model-surface tests;
- golden regressions;
- real-model proof.

---

## 6. Non-goals

Do not add:

- a custom Agent Loop;
- a workflow engine;
- a router or intent classifier;
- an agent registry;
- a generic event bus;
- a new approval system;
- a new memory database;
- a vector database;
- a strategy DSL;
- generic RBAC;
- a new orchestration layer.

Do not solve in this phase:

- full Working / Conversation / Case / Owner / Archive memory scoping;
- Telegram groups;
- Feishu integration;
- Supervisor Console;
- asynchronous run/presence UX.

These are later phases and must build on the corrected agent-loop contract.

---

## 7. Success metrics

P3B-2 succeeds when:

1. normal FDE completion is natural-language output, not `RunSummary`;
2. `RunSummary` is host-generated;
3. authoring under a bound Case still returns directly with zero approval;
4. Client Service deterministic strategy selection is removed from the production FDE path;
5. local business-state recording does not require approval;
6. true external effects still pause and resume through native PydanticAI approval;
7. model-visible surface tests prove that audit/business-control schemas are absent from a normal initial request;
8. a real-model three-turn proof passes;
9. full regression, Ruff, and manifest pass.

---

## 8. Product acceptance examples

### Example A — authoring

**Input**

> [article text]
> 改写这篇文章

**Expected**

- rewritten article returned;
- no approval;
- no `/case`;
- no mandatory save;
- no customer-delivery action.

### Example B — business judgment

**Input**

> 这个客户一直两三天问一次案例，但又不拍板，你判断一下现在怎么回。

**Expected**

- FDE uses customer context/history as evidence;
- FDE decides the reply strategy itself;
- no `select_response_strategy` deterministic tool in production surface;
- hard policy constraints still apply.

### Example C — explicit delivery

**Input**

> 这版可以，发给客户。

**Expected**

- outbound tool call;
- native approval pause;
- operator sees exact outbound payload;
- approve executes once;
- deny executes zero times.

---

## 9. Product stop statement

Do not declare success because a schema validates, a receipt exists, or a tool was called.

The product is successful only when the user outcome is natural and the machine control plane remains verifiable without becoming the model’s workflow.
