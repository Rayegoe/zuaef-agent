# CODEX MASTER PROMPT — ZUAEF Harness Alignment v0.1

You are working in `Rayegoe/zuaef-agent`.

## Mission

Evaluate whether current ZUAEF can safely move from its production PydanticAI Harness 0.27.x line to Harness 0.29.x without expanding the architecture or changing capability admission.

This is a compatibility and evidence task, not a feature-upgrade task.

## Authority

Before doing anything, read in this order:

1. `AGENTS.md`
2. `.agents/skills/zuaef-runtime-coach/SKILL.md`
3. `docs/runtime-refoundation/CAPABILITY_ADMISSION.md`
4. `docs/runtime-refoundation/TASKS.md`
5. this spec pack:
   - `00_README.md`
   - `01_RECONCILED_AUDIT.md`
   - `02_ARCHITECTURE_BOUNDARY.md`
   - `03_SPEC.md`
   - `04_TASKS.md`
   - `05_ACCEPTANCE.md`
   - `06_VERSION_AND_CAPABILITY_POLICY.md`
   - `07_PATCH_TARGETS.md`

Repository authority outranks this pack if any conflict appears.

Do not bypass the current runtime-refoundation queue. Read-only/version compatibility work may proceed; any production runtime/capability behavior change must be routed through the repository's existing authority/order.

## First principles

Preserve these boundaries:

```text
PydanticAI owns the agent loop and native approval/usage primitives.
Harness owns generic reusable agent capabilities.
ZUAEF owns business semantics, domain capabilities, composition identity and thin operational settlement/control-plane behavior.
```

Do not build a second Harness.

## Current expected baseline

Declared production dependencies are expected to include:

```text
pydantic-ai>=2.35.3,<3
pydantic-ai-harness[skills,code-mode]>=0.27,<0.28
```

Candidate upstream Harness 0.29.x requires PydanticAI slim >=2.38.0.

Verify actual repository/lock facts. Do not trust this prompt over current code.

## Execute tasks

Follow `04_TASKS.md` H000 → H014 in order.

Important execution rules:

### 1. Baseline before edits

Run focused Harness-boundary tests on the current dependency set before creating the candidate environment.

### 2. Candidate first, repairs second

Create a disposable branch/worktree/environment for 0.29.x.

Run the same focused tests unchanged before modifying code.

Classify every candidate failure before editing anything.

### 3. Public behavior beats private internals

Known risk:

```python
tests/test_writing_codemode_skills.py
getattr(caps, "_deferred_capabilities", ())
```

If this fails because Harness changed a private member while public deferred-skill behavior still works, repair the test to use public/observable behavior. Do not create a compatibility shim that recreates upstream internals.

### 4. Protect the continuation seam

The most important compatibility proof is:

```text
run -> native DeferredToolRequests -> pause/frontier
process boundary
continue_run(include_interrupted=True)
native DeferredToolResults approve/deny
resume with same conversation + frozen composition + bindings
terminal result
```

Test both approve and deny with deterministic/local fixtures and prove no duplicated effect.

### 5. No feature shopping

Do not enable or integrate any of these during compatibility work:

- DynamicWorkflow
- Guardrails
- PromptInjectionDefender
- Spend
- CapabilityCreation
- Coder
- Researcher
- Temporal/DBOS/Prefect durable execution

They may be recorded as `NOT_ADMITTED` / experimental candidates only.

### 6. No architecture inflation

Do not add:

- agent registry;
- custom durable runtime;
- custom event bus;
- new global capability flags;
- second approval system;
- second tool dispatcher;
- compatibility framework;
- manifests/checksums/hashes for this upgrade;
- schemas/gates/fields without a reproduced failure.

### 7. One causal fix at a time

If candidate 0.29 breaks:

1. reproduce;
2. classify;
3. make the smallest fix;
4. rerun the same focused test;
5. then run the full regression.

Do not redesign several layers together.

## Focused test set

Start with at least:

```text
tests/test_generalist_activation.py
tests/test_phase2_generalist_policy.py
tests/test_phase2_deferred_tools.py
tests/test_plugin_composition.py
tests/test_continuation.py
tests/test_execute_run_seam.py
tests/test_writing_codemode_skills.py
```

Discover and include existing focused tests for FileSystem protected paths and ToolOutputLimits if present.

After focused tests pass, run canonical full gates, normally:

```bash
uv run pytest
uv run ruff check .
```

Use repository canonical commands if different.

## Deliverable

Produce one concise compatibility report containing:

1. baseline declared/resolved versions;
2. candidate resolved versions;
3. focused baseline result;
4. focused candidate-before-fix result;
5. every incompatibility classification;
6. exact changes made, if any;
7. pause/resume approve+deny proof;
8. capability/tool-surface comparison;
9. full regression result;
10. final verdict.

Final verdict must be exactly one of:

```text
PROMOTE_0_29
HOLD_0_27_PUBLIC_BREAK
HOLD_0_27_DEPENDENCY_CONFLICT
HOLD_0_27_BEHAVIOR_REGRESSION
REFINE_TEST_PRIVATE_API_ONLY
```

If the verdict is not `PROMOTE_0_29`, revert/discard candidate dependency edits and leave production unchanged.

If the verdict is `PROMOTE_0_29`, update the production dependency pin/lock only after all gates pass. Do not change capability defaults or architecture as part of promotion.

A precise HOLD is a successful outcome. Do not force an upgrade.
