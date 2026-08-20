# CODING AGENT PROMPT — Execute the Architecture Subtraction Spec

You are working in the `Rayegoe/zuaef-agent` repository.

Baseline for this spec pack:

```text
main@14e0df06012c4b925012d3ee9be0734af0282a7d
```

Read, in this order:

1. `README.md` from this spec pack
2. `PRD.md`
3. `SPEC.md`
4. `MIGRATION.md`
5. `PLAN.md`
6. `TASKS.md`
7. `ACCEPTANCE.md`
8. repository `AGENTS.md`

## Mission

Remove accidental abstraction and false semantic authority from ZUAEF while preserving real PydanticAI/Harness execution, safety, plugin composition, and resume behavior.

The central correction is:

> File hashes, tool-event fields, and typed receipt metadata are operational facts, not semantic verification. Real factual evidence should appear in the result as inspectable source URLs/citations. Real quality improvement comes from actual outputs + LLM critique + human annotations/edits + controlled promotion.

## Hard constraints

### Do not create replacement frameworks

You are NOT allowed to solve this cleanup by adding:

```text
EvidenceRegistry
EvidenceProvider
QualityRegistry
ContextRegistry
BindingRegistry
ServiceRegistry
EventBus
Graph runtime
new durable runtime
new database
```

If you believe one is necessary, stop implementation of that part and write the concrete failure that existing PydanticAI/Harness primitives cannot solve.

### Preserve upstream ownership

Continue using PydanticAI / pydantic-ai-harness for:
- Agent loop;
- capabilities;
- toolsets;
- approval;
- deferred calls;
- persistence;
- usage limits;
- memory/subagents/context controls where adopted.

Do not clone them.

### Preserve true invariants

Do not weaken:
- external/destructive approval;
- path security;
- credentials isolation;
- exact composition resume;
- pause continuity;
- run/conversation identity;
- StepPersistence.

### Business code stays in plugins

A change needed only for Case, Writing, Budget, WordPress, Client Service, or a future domain must not create a branch in the generic runtime.

### Natural generation stays natural

Do not reintroduce a structured model output schema for receipt/evidence fields.

## Required implementation order

Execute `T000` through `T015`.

Do not jump to the learning-loop rewrite before receipt/runtime semantics are cleaned.

After each major phase:
- run the narrow relevant tests;
- inspect diff;
- remove dead compatibility;
- confirm no new abstraction layer appeared.

## Critical semantic rename

Treat these concepts precisely:

```text
artifact hash            = byte/integrity fact
tool completed           = execution fact
composition snapshot     = reproducibility fact
source URL/citation      = inspectable evidence pointer
source supports claim    = evaluator judgment
human prefers result     = quality evidence
```

Never call the first three proof that content is correct.

## Learning migration rule

Existing editorial benchmark rows with fields such as:

```text
trigger_signals
action
weight
approved_by
```

are legacy derived data.

Do not delete original provenance, before/after text, or human comments.

Build the new vertical slice around preserved natural evidence:
- task;
- context;
- output;
- source URLs;
- human feedback;
- revision.

Only after a 3–5 case vertical slice works should you migrate more data.

## Stop condition

Stop when all gates in `ACCEPTANCE.md` pass.

Do not use remaining time to add “nice” abstractions.

The desired end state is smaller than the starting architecture.

## Result Contract requirement

Do not interpret “remove structured verification fields” as “all capabilities now produce an unstructured generic blob”.

The intended architecture is:

```text
Kernel:
  generic natural output + execution mechanics

Capability:
  domain-specific result contract
  (instructions + toolset/save/finalize semantics + local deterministic checks)

Artifact:
  native business deliverable
```

You MUST prove that at least three capabilities can impose different useful result structures without adding generic result fields.

Do NOT add `PluginBundle.result_schema`, `BusinessResult`, or a result registry.

Prefer PydanticAI Capability seams such as `get_instructions()` and `get_toolset()`. Domain-specific Pydantic models are allowed inside the owning plugin when required by a real deterministic API/business invariant; they must not leak into Kernel.


## Pydantic rule — object contract only

Do not solve orchestration by creating Pydantic workflow/status models.

Pydantic is appropriate for:
- function/tool arguments;
- plugin configuration;
- external API payloads;
- stored domain records;
- deterministic data objects.

It is NOT appropriate for:
- phase gates;
- completion gates;
- semantic quality gates;
- “required fields before next step” workflow;
- replacing Agent judgment with enums/booleans.

If you find yourself adding fields such as `research_complete`, `quality_passed`, `ready_to_publish`, `next_stage`, or `evidence_score` to make the Agent proceed mechanically, stop and remove that design.

Use the Agent loop + Capability instructions/tools for work progression. Use native approval only at real side-effect boundaries.
