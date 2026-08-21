# ZUAEF Agent Runtime Re-foundation Coach Pack

> A drop-in engineering coach for continuously reducing Agent runtime complexity without throwing away validated business assets.

## Mission

This pack turns one architectural principle into an executable development discipline:

> **The shortest correct trajectory is the preferred trajectory.**

ZUAEF has already reduced a large amount of static architecture complexity: duplicated runtimes, duplicate control planes, generic tool surfaces, editorial-control machinery, and unnecessary framework ownership. The remaining risk is different:

**runtime behavior can still be complex even when the Python architecture looks thin.**

A business task can still cause the model to:

- create and reread plans;
- load skills without evidence that they help;
- inspect state that the host could already provide;
- read materials one by one;
- repeat evidence checks after the evidence state cannot change;
- reconstruct prior history for a simple revision;
- perform bookkeeping through model-visible actions;
- create new model turns without receiving materially new semantic information.

This coach pack makes those costs first-class architecture constraints.

## What this pack is

This is not a Writing optimization guide.

It is a **brownfield runtime re-foundation system** for the whole ZUAEF FDE Agent:

- Writing is the first canary.
- Negotiation, client service, budget analysis, research, WordPress, supplier work and future capabilities inherit the same runtime rules.
- Existing validated assets remain available.
- Existing runtime behavior does not automatically retain production authority.

The re-foundation strategy is:

```text
PRESERVE ASSETS
    +
FREEZE CURRENT BEHAVIOR AS REFERENCE
    +
BUILD A MINIMAL PATH FROM ZERO
    +
RE-ADMIT COMPLEXITY ONLY WITH EVIDENCE
```

## Core distinction

A Harness capability is not a free software feature.

Adding a capability can change:

- model-visible tool schemas;
- instructions;
- action-space entropy;
- number of model requests;
- context growth;
- prompt-cache behavior;
- failure/retry surfaces;
- model attention allocation.

Therefore:

```text
available != enabled
enabled != required
reusable != free
capability != workflow
history != state
autonomy != model-mediated mechanics
```

## Recommended repository placement

Copy this pack's contents into the repository root.

The most important entry points become:

```text
.agents/skills/zuaef-runtime-coach/SKILL.md
docs/runtime-refoundation/PRD.md
docs/runtime-refoundation/SPEC.md
docs/runtime-refoundation/BENCHMARKS.md
docs/runtime-refoundation/CAPABILITY_ADMISSION.md
docs/runtime-refoundation/DELETION.md
prompts/runtime-refoundation/CODE_AGENT_MASTER_PROMPT.md
```

The existing repository's `Outcome-First PydanticAI Agent Engineering Guide v2.0.md` remains strategic background. This pack operationalizes it into measurable runtime gates.

## Non-goals

This pack does **not** authorize:

- deleting the repository;
- rewriting the plugin ABI;
- replacing PydanticAI or Pydantic AI Harness;
- inventing a new graph runtime;
- building a new memory framework;
- creating a second durable runtime;
- replacing ACE;
- turning every domain into a deterministic workflow;
- optimizing benchmark numbers by reducing business quality;
- hard-coding WCASE answers.

## First command for a Coding Agent

Give the agent:

```text
Read AGENTS.md, then read:
1. .agents/skills/zuaef-runtime-coach/SKILL.md
2. docs/runtime-refoundation/SPEC.md
3. docs/runtime-refoundation/BENCHMARKS.md
4. docs/runtime-refoundation/DELETION.md
5. docs/runtime-refoundation/TASKS.md

Execute only the next admissible experiment.
Do not redesign the whole repository.
Do not add a capability to solve a failure that has not been reproduced.
```

## Definition of success

The re-foundation is complete when:

1. simple business tasks stay simple;
2. complex tasks can progressively acquire complexity;
3. model turns correspond to semantic progress;
4. mechanical work does not consume model decisions;
5. unknown evidence states converge;
6. revision uses bounded state rather than default history reconstruction;
7. capabilities have measured admission evidence;
8. business quality does not regress;
9. old runtime machinery that has lost authority is deleted or clearly quarantined;
10. the same principles hold outside Writing.

