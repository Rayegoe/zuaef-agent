---
name: zuaef-runtime-coach
description: Optimize ZUAEF Agent runtime behavior by measuring real trajectories, reducing unnecessary model decisions, re-admitting capabilities only with evidence, and preserving business outcome/evidence integrity. Use for runtime architecture, WCASE optimization, capability/core changes, revision/context design, and complexity regression reviews.
---

# ZUAEF Runtime Coach

## Mission

Drive the repository toward the smallest reliable Agent loop.

Do not equate:
- fewer files with a better Agent;
- more capabilities with a better Agent;
- tool use with autonomy;
- persistence with task state;
- message history with state;
- test pass with runtime quality.

## Required reading

Before runtime architecture work read:

```text
docs/runtime-refoundation/SPEC.md
docs/runtime-refoundation/BENCHMARKS.md
docs/runtime-refoundation/CAPABILITY_ADMISSION.md
docs/runtime-refoundation/DELETION.md
docs/runtime-refoundation/TASKS.md
```

## Loop

For each iteration:

### 1. Observe

Name one concrete failure from a real trace or benchmark.

Bad:

```text
the architecture feels complex
```

Good:

```text
WCASE-1 performs write_plan/read_plan/status updates before saving,
without those turns introducing new business evidence.
```

A queued task is a hypothesis about a failure, not a contract. Re-derive the
failure from current code and a fresh trace before executing the task; a
queue can lag behind evidence. A historical diagnosis that no longer
reproduces is closed with a recorded verdict
(`CURRENT_PATH_ALREADY_MINIMAL` / `NO_REMOVAL_JUSTIFIED` /
`PROBLEM_NOT_REPRODUCED`), never honored with new architecture.

### 2. Classify the cost

Classify each suspicious action:

- `SEMANTIC_OBSERVATION`
- `SEMANTIC_DECISION`
- `ARTIFACT_SUBMISSION`
- `EXTERNAL_ACTION`
- `VALIDATION`
- `MECHANICAL_TRANSPORT`
- `BOOKKEEPING`
- `DURABILITY`
- `PRESENTATION`

`ARTIFACT_SUBMISSION` persists the model's own local deliverable (for
example `save_article`). `EXTERNAL_ACTION` changes external systems,
production data, or people. Local artifact persistence is not an external
side effect; confusing the two pollutes cross-domain effect accounting.

Model turns should cluster around semantic observation, semantic decision,
artifact submission, external action and validation when semantic
interpretation is needed.

### 3. Form one causal hypothesis

Examples:

```text
Planning is unnecessary for this task class.
Per-material reads create avoidable dependent round trips.
Revision reconstructs transcript instead of using current task state.
Unknown evidence lacks a semantic convergence rule.
```

Do not change several causal mechanisms together.

### 4. Make the narrowest experiment

Start from removal or narrowing before adding machinery.

When testing a capability:
- OFF is the control;
- ON must earn admission.

### 5. Evaluate

Always compare:
- accepted outcome — a recorded verdict; `execution_state=completed` or a
  `null` outcome evaluation blocks optimization acceptance;
- evidence/effect integrity;
- requests;
- tool calls;
- token/context metrics;
- latency;
- repeated observation.

### 6. Decide

One of:

- `KEEP_CHANGE`
- `REVERT`
- `REFINE`
- `PROMOTE_TO_PROFILE`
- `PROMOTE_TO_CORE_CANDIDATE`
- `QUARANTINE_OLD_PATH`
- `DELETE_OLD_PATH`

A task may equally close with zero code change when its failure premise does
not reproduce or its outcome gate is unverified.

### 7. Record

Update experiment/decision records.

## Architecture guardrails

### Capability burden of proof

A capability must solve a reproduced failure.

### Model-turn burden of proof

A new turn must be able to change a semantic decision.

### Mechanical work

Keep deterministic:
- hashing;
- batching;
- indexing;
- receipt writing;
- path manipulation;
- state recording.

### Semantic work

Keep model-owned:
- relevance;
- priority;
- factual interpretation;
- strategy;
- writing judgment;
- negotiation choice;
- decision under ambiguity;
- which material, excerpt, technique guidance or past review counts as
  relevant.

Host-side lexical ranking, keyword tagging or heuristic filtering that
pre-decides any of the above is semantic preselection, not transport, and
requires an audit that proves it does not steal the model's selection
authority.

### Revision

Prefer:

```text
artifact + delta + bounded current state
```

over:

```text
search entire transcript + reload old results + rebuild plan
```

### Unknown

No available evidence is a result.

Do not repeatedly query an unchanged evidence surface to manufacture certainty.

## Stop rules

Stop and report rather than expanding architecture when:

- failure cannot be reproduced (including an expired task premise or
  historical diagnosis that current code no longer exhibits);
- metrics are missing;
- proposed change depends on hypothetical future use;
- outcome quality falls;
- semantic ownership would move into host heuristics;
- upstream already owns the primitive;
- current benchmark has not converged.

