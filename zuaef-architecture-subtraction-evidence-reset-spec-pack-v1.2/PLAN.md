# PLAN — Implementation Sequence

## Strategy

This is a **delete-first refactor**.

Do not start by introducing target abstractions. Start by removing false semantics while preserving real runtime behavior.

## Phase A — Freeze baseline and inventory

1. Record baseline commit.
2. Run full tests.
3. Run the authoritative Gateway/FDE proof if environment permits.
4. Search for:
   - `verified_`
   - `evidence`
   - `Verification`
   - `case_id`
   - `GENERALIST_FLAGS`
   - `trigger_signals`
   - `approved_by`
   - `weight`
5. Classify each occurrence:
   - security/integrity;
   - runtime bookkeeping;
   - semantic claim;
   - business-domain leak;
   - benchmark-only derived data.

Do not refactor before this inventory exists.

## Phase B — Receipt and integrity reset

1. Introduce v2 operational receipt models.
2. Stop writing semantic verification/evidence fields.
3. Convert artifact hashes and tool events into neutrally named facts only if real consumers need them.
4. Remove semantic status degradation.
5. Rename/delete `verification.py`.

Checkpoint:
- normal authoring result still returns natural text;
- external effect approval still pauses;
- resume still works;
- runtime no longer claims semantic validation.

## Phase C — Remove Case from kernel

1. `case_id` → opaque `bindings`.
2. preserve bindings in terminal and pause receipts.
3. restore bindings on continuation.
4. move context projection to Case capability.
5. move cross-case call validation into Case tool validation.
6. remove Case-specific branches/imports from runtime and gateway bridge.

Checkpoint:
- existing Stillevo FDE two-turn behavior still works;
- kernel can run without Case plugin;
- generic kernel contains no Case business logic.

## Phase D — Simplify knowledge semantics

1. remove global truth/type enum requirements;
2. remove `SourceRef` requirement from kernel;
3. preserve safe document storage;
4. ensure source URLs are written in real artifacts/knowledge prose where appropriate.

Checkpoint:
- storage works without fake evidence fields;
- evidence-bearing example has readable URLs.

## Phase E — Stop capability registry growth

1. mark `GENERALIST_FLAGS` closed;
2. add architecture test preventing new keys without explicit architecture decision;
3. do not perform a broad extraction unless necessary.

Checkpoint:
- no new framework created.

## Phase F — Build real quality loop

Reuse existing editorial-learning assets where useful.

1. create document-first case packet format;
2. migrate a small representative set first;
3. add LLM review prompt/process;
4. add human review file;
5. promote one accepted lesson to Skill/example;
6. compare later output against baseline.

Do not migrate all historical benchmark rows before one vertical slice proves the new loop.

## Phase G — Remove dead compatibility

After tests and real proof pass:
- delete old semantic models/functions;
- delete unused imports;
- delete obsolete tests;
- document v2 boundary;
- freeze kernel API.

## Stop rules

Stop and reassess if implementation proposes any of:

```text
EvidenceRegistry
QualityRegistry
ContextRegistry
BindingRegistry
ServiceRegistry
EventBus
new custom durable runtime
new global database
new graph/state machine
automatic learning promotion
```

Also stop if a change touches `core.py/runtime.py/composition.py` to support a single business domain. The business need must first be moved to a plugin/capability.

## Commit strategy

Prefer small commits grouped by invariant:

1. receipt/integrity semantics;
2. bindings migration;
3. Case plugin migration;
4. knowledge simplification;
5. quality-loop vertical slice;
6. docs/freeze.

Do not mix formatting churn or unrelated plugin work.

## Phase H — Prove Capability-owned result customization

Before declaring Kernel frozen, prove result-shape variation across at least three domains/capabilities.

Recommended proof:

```text
Writing     → article
Budget      → budget analysis
Research or Client Service → materially different result
```

For each:
- use the same generic runtime terminal contract;
- no new generic result fields;
- no `if domain == ...` in runtime;
- structure is controlled by capability instructions/tooling;
- domain-local deterministic validation is allowed.

The proof is architectural: the three useful outputs must be visibly different because their capabilities differ, while Kernel remains unchanged.
