# CODING AGENT PROMPT — Execute P3B-2

You are working in `Rayegoe/zuaef-agent`.

Your task is to implement the P3B-2 **Generative Agent Loop Separation** package exactly as defined by:

1. `PRD.md`
2. `SPEC.md`
3. `TASKS.md`
4. `PLAN.md`

Read all four before editing.

---

## Mission

Fix the recurring ZUAEF architecture failure where business fields, schemas, tools, gates, and receipts begin to steer the LLM's generation.

The target principle is:

> **The model owns judgment and generation. The host owns authority, persistence, verification, and receipts.**

This is not a new framework project.

Use the native pinned PydanticAI Agent Loop. Consume upstream capabilities. Remove/reposition ZUAEF coupling.

---

## Non-negotiable architecture rules

### 1. Natural output

Generic FDE completion must be natural text plus native `DeferredToolRequests` for approval pauses.

`RunSummary` must leave the model output contract.

### 2. Host settlement

The host creates `RunSummary`/`RunReceipt`.

Do not ask the model to provide audit fields, artifact refs, tool-effect IDs, run IDs, or receipt paths.

### 3. Tools are capabilities

Do not encode generic workflows into tool instructions.

A tool may describe what it does, arguments, evidence semantics, and hard constraints.

### 4. Business judgment stays with the FDE

Remove deterministic Client Service `assess_customer` / `select_response_strategy` from the production Agent tool surface.

Keep their code only for offline evaluation/audit if useful.

### 5. Case is context

A bound Case provides background and durable state.

It does not define the workflow.

Case mutation/delivery tools must be deferred.

### 6. Approval is a boundary

Observe/local writes are automatic by default.

External/destructive effects remain native PydanticAI approval-gated.

Do not create another approval engine.

### 7. Gateway is generic

Gateway must not read `workspace/cases/<id>/drafts/...` or understand Case draft naming.

External actions must carry a self-describing approval payload.

### 8. No replacement machinery

Do not add:

- custom Agent Loop;
- workflow engine;
- router;
- agent registry;
- semantic intent classifier;
- event bus;
- new memory DB;
- strategy DSL;
- generic business output envelope.

---

## Required implementation sequence

Follow `PLAN.md`.

Do not begin by editing every plugin.

### First:
restore natural terminal output and host-generated settlement.

### Second:
make Case context-only + deferred tools.

### Third:
return business judgment to the FDE and clean Writing/Budget instructions.

### Fourth:
make outbound approval self-describing and remove Gateway business-storage coupling.

### Fifth:
freeze the structural regression and docs.

Keep commits logically separated.

---

## Critical tests

The most important test is not “the model happened to behave once”.

Add a structural test capturing the first normal model request and prove the model does **not** see:

- RunSummary settlement schema;
- `deliverable`;
- receipt/evidence crafting instructions;
- CustomerAssessment;
- deterministic response strategy;
- approval/disclosure enums;
- initially deferred Case mutation/delivery tools.

Then implement G1–G7 from `SPEC.md`.

---

## Real-model proof

After deterministic tests pass, run the three-turn proof:

### Turn 1

Paste the existing “夏天的指尖” sample and say:

`改写这篇文章`

Expected: direct rewritten text, zero approval.

### Turn 2

`开头还是太像 AI，第二段别动，其他地方保持。`

Expected: real continuation, direct revision, zero approval.

### Turn 3

`这版可以，发给客户。`

Expected: native approval pause with exact outbound content visible.

Approve must execute that exact payload once. Deny must execute zero times.

Use a disposable `/tmp` proof if appropriate. Do not commit a one-off script unless it becomes a stable general regression tool.

---

## Quality gates

Before finalizing:

- run Ruff;
- run full pytest;
- verify StepPersistence continuity;
- verify pause/resume;
- verify frozen composition;
- verify Case isolation;
- regenerate/verify manifest;
- review diff for accidental new framework;
- ensure README and `docs/agent-loop-contract.md` match the code.

---

## Reporting

Report progress by TASK ID.

When finished, provide:

- starting SHA;
- commit SHAs;
- changed-file summary;
- deterministic golden-case results G1–G7;
- model-visible-surface result;
- Ruff result;
- full pytest result/count;
- manifest result;
- real-model proof result;
- any remaining unknowns.

Only if every Stop Gate in `SPEC.md` passes, end with exactly:

`P3B-2 = 100% — STOP`

If any required gate fails, do not claim completion. State the failed gate and the smallest next experiment.
