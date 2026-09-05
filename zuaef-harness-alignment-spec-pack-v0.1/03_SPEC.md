# SPEC — Harness Follow Lane v0.1

## 1. Problem

ZUAEF is already architecturally aligned with PydanticAI Harness but production is pinned to Harness 0.27.x while upstream is at 0.29.x.

Without an explicit follow lane, two failure modes are likely:

1. stay pinned indefinitely because every minor upgrade feels like an architecture project;
2. chase every upstream feature and accidentally expand the model surface/core without business evidence.

This spec creates a middle path: **small, repeatable compatibility evaluation with no automatic production promotion.**

## 2. Outcome

After execution, maintainers must be able to answer:

- Does current ZUAEF behavior run correctly on Harness 0.29.x + PydanticAI >=2.38?
- If not, what exact public/observable contract breaks?
- Is the break in production code, a private-API test, dependency resolution or intentional changed upstream behavior?
- What is the smallest repair?
- Should production stay on 0.27.x or promote to 0.29.x?

## 3. Functional requirements

### FR-1 — Baseline version truth

Record separately:

- production declared dependency range;
- resolved production versions from the lock/environment;
- candidate upstream minor line;
- candidate PydanticAI floor.

Never call the production pin "latest".

### FR-2 — Compatibility lane

Evaluate the candidate minor in an isolated branch/worktree/environment.

Do not edit the production pin in the baseline branch until all promotion gates pass.

### FR-3 — Public behavior first

Compatibility tests must prefer observable public behavior:

- model-visible tool/capability surface;
- protected path behavior;
- deferred loading behavior;
- pause/resume behavior;
- tool-output spill/limit behavior;
- composition and profile behavior;
- runtime terminal state/receipt behavior.

Tests must not depend on private Harness attributes when a public behavior can prove the same contract.

### FR-4 — Pause/resume gate

The candidate must prove the current approval continuation contract:

1. run pauses with pending approval;
2. interrupted frontier is durably available after process boundary;
3. continuation restores the same conversation and frozen composition/bindings;
4. approve/deny becomes native `DeferredToolResults` input;
5. the run reaches the expected terminal result;
6. no external effect is duplicated by the compatibility change.

### FR-5 — Composition gate

Existing profile/plugin composition must retain:

- one core Agent;
- explicit plugin factories;
- Toolset/Skill/Capability bundle boundary;
- `DeferredLoadingToolset` behavior where configured;
- frozen composition authority for resume;
- no second plugin runtime.

### FR-6 — Capability surface gate

A dependency-only upgrade must not silently add new production-visible capabilities/tools.

Any model-surface change must be explained by an intentional upstream behavior change and separately admitted before production promotion.

### FR-7 — CJK ToolSearch gate

The existing CJK search strategy must still compose through PydanticAI ToolSearch and preserve the intended ASCII behavior plus Chinese discoverability.

Do not fork ToolSearch.

### FR-8 — CodeMode gate

Existing CodeMode experimental/profile behavior must continue to:

- wrap only intended read/query-style tools;
- keep irreversible/external/artifact-submission actions outside CodeMode where current policy requires;
- remain off unless the profile explicitly enables it.

### FR-9 — Full regression

After focused compatibility tests pass, run the repository's ordinary lint/test gates.

No test should be weakened merely to make the new dependency pass.

### FR-10 — Promotion decision

The final result must be one of:

- `PROMOTE_0_29`
- `HOLD_0_27_PUBLIC_BREAK`
- `HOLD_0_27_DEPENDENCY_CONFLICT`
- `HOLD_0_27_BEHAVIOR_REGRESSION`
- `REFINE_TEST_PRIVATE_API_ONLY`

A hold decision is complete work when evidence is precise.

## 4. Non-functional requirements

### NFR-1 — No architecture expansion by default

Do not add new global capability flags, registries, middleware frameworks, event buses or durable runtimes to perform the upgrade.

### NFR-2 — No new hash/integrity machinery

Do not add SHA/checksum/fingerprint/manifest mechanisms for this work. Existing local integrity logic is out of scope unless the candidate version directly breaks its behavior.

### NFR-3 — No capability shopping

Do not enable DynamicWorkflow, Guardrails, PromptInjectionDefender, Spend, CapabilityCreation, Coder or Researcher merely because the candidate Harness contains them.

### NFR-4 — One causal change at a time

If the candidate breaks, isolate the smallest cause before editing production behavior.

### NFR-5 — No real external side effects in compatibility validation

Use deterministic/local fixtures for approval and effect tests. A live canary must be read-only or otherwise bounded and explicitly non-destructive.

## 5. Out of scope

- redesigning `runtime.py`;
- replacing StepPersistence with Temporal/DBOS/Prefect;
- introducing full event sourcing;
- making StillWrite/Gateway a second agent runtime;
- turning SubAgents or DynamicWorkflow into the default topology;
- redesigning domain plugins;
- quant strategy changes;
- writing-quality experiments already governed by runtime-refoundation T006/T008/etc.;
- promoting new capabilities without the existing Capability Admission Protocol.

## 6. Relationship to runtime-refoundation queue

This spec must not bypass `docs/runtime-refoundation/TASKS.md`.

Read-only audits and isolated dependency compatibility tests may proceed as a maintenance lane. Any production runtime/capability behavior change discovered here must be routed through the current runtime-refoundation authority and its task order.
