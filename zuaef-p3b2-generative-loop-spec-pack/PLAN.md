# PLAN — P3B-2 Implementation Plan

The plan deliberately removes coupling in layers. Do not mix every change into one commit.

---

# 1. Preflight

1. Record HEAD.
2. Run:
   - Ruff;
   - full pytest;
   - manifest check/regeneration dry run if available.
3. Confirm pinned dependency versions from `uv.lock`.
4. Probe natural `str + DeferredToolRequests` output on the pinned PydanticAI version.

If the probe fails because of a release limitation, stop and report the exact upstream limitation. Do not invent a custom agent loop.

---

# 2. Commit sequence

## Commit A — `refactor(loop): restore natural terminal output`

Scope:

- `core.py`
- `models.py`
- `runtime.py`
- `gateway/renderer.py`
- focused runtime/core tests

Changes:

1. generic Agent terminal becomes natural text;
2. `TerminalRun.presentation`;
3. `RunSummary` host-generated;
4. stop producing `deliverable`;
5. receipts remain intact;
6. error/partial/blocked settlement remains host-owned.

Required gate before Commit B:

- natural output test passes;
- approval pause still passes;
- artifact/effect settlement still passes;
- no P3B-2 business-plugin changes yet.

Rollback point:
- this commit should be independently revertible.

---

## Commit B — `refactor(context): case supplies context, not workflow`

Scope:

- `context_projection.py`
- `gateway/bridge.py`
- Case toolset
- `profiles/stillevo-fde.toml`
- Case/model-surface tests

Changes:

1. host-projected bounded Case brief;
2. remove Case workflow instructions;
3. defer Case tools;
4. initial model surface becomes smaller.

Required gate:

- bound Case authoring works without loading Case mutation/delivery tools;
- unbound authoring unchanged;
- isolation unchanged.

---

## Commit C — `refactor(judgment): return business decisions to the FDE`

Scope:

- Client Service plugin
- Writing rules
- Budget rules
- corresponding tests

Changes:

1. remove deterministic client strategy tools from production surface;
2. local interaction recording no approval;
3. Writing stops mandating artifact/final schema;
4. Budget stops mandating report artifact;
5. deterministic math/facts remain.

Required gate:

- G1–G5 deterministic cases pass;
- offline policy tests remain available;
- no loss of hard constraints.

---

## Commit D — `refactor(approval): make external effects self-describing`

Scope:

- Case outbound tool
- Gateway service/renderer
- approval tests

Changes:

1. pending send carries exact outbound text;
2. delete Gateway Case draft filesystem lookup;
3. approve executes exactly shown payload;
4. deny executes zero.

Required gate:

- G6/G7 pass;
- pause/resume/restart pass;
- no duplicate effect.

---

## Commit E — `test/docs: freeze P3B-2 agent-loop contract`

Scope:

- `tests/test_model_surface_contract.py`
- README
- `docs/agent-loop-contract.md`
- manifest

Changes:

1. structural leakage regression;
2. architecture documentation;
3. final manifest.

Then run real-model proof.

---

# 3. Migration strategy

## RunSummary compatibility

Do not break old receipts unnecessarily.

During P3B-2:

- old receipts containing `deliverable` remain readable;
- new runs do not write `deliverable`;
- renderer prefers `TerminalRun.presentation`;
- next receipt-schema version may remove `deliverable`.

## Client Service policy compatibility

Keep deterministic policy code and fixtures for regression/evaluation.

Only disconnect them from production Agent tool registration.

This preserves historical business assets without letting them decide every live turn.

## Case compatibility

Do not redesign Case storage schema in P3B-2.

Only change:

- what is projected to the model;
- which Case tools are initially visible;
- workflow instructions.

Full context/memory scoping is a separate phase.

---

# 4. Test strategy

Use three layers.

## Layer A — Structural

Tests prove what the model can see.

Most important test in the phase.

A future developer should not be able to re-add `RunSummary`, strategy enums, or outbound Case tools to the first request without breaking CI.

## Layer B — Deterministic behavior

FunctionModel/scripted tests for G1–G7.

These prove boundaries without relying on stochastic model behavior.

## Layer C — Real model

Three-turn proof.

This proves the corrected architecture produces the intended product behavior with the production model.

A real-model failure after A+B pass should be treated as instruction/context quality evidence, not a reason to reintroduce deterministic workflow fields.

---

# 5. Review checklist per commit

Before accepting each commit ask:

1. Did this add a new field the LLM now has to reason around?
2. Did this add a new mandatory tool sequence?
3. Did this make a soft business judgment deterministic?
4. Did this move host/receipt concerns into model instructions?
5. Did this make Gateway aware of a business plugin’s internal storage?
6. Could the same safety property be enforced as a guard instead of guidance?
7. Is this capability available without being forced into every task?

If any answer indicates new coupling, revise before proceeding.

---

# 6. Final proof report format

The coding agent must report:

```text
BASELINE
- starting SHA
- pinned versions
- baseline tests

CHANGES
- Commit A SHA + purpose
- Commit B SHA + purpose
- Commit C SHA + purpose
- Commit D SHA + purpose
- Commit E SHA + purpose

STRUCTURAL PROOF
- model output contract
- initial model-visible tools
- forbidden strings/schemas absent

GOLDEN CASES
G1 PASS/FAIL
...
G7 PASS/FAIL

CONTINUITY
- StepPersistence
- pause/resume
- frozen composition
- Case isolation

REAL MODEL
- Turn 1
- Turn 2
- Turn 3
- approval payload equality

QUALITY
- Ruff
- pytest count
- manifest

VERDICT
P3B-2 = 100% — STOP
```

Do not claim 100% with a failed real-model proof or failed structural gate.
