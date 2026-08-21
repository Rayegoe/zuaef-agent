# SPEC — ZUAEF Minimal Agent Runtime

Status: normative  
Version: 1.0

## 1. Executive decision

ZUAEF keeps the repository, its validated integrations and domain assets.

It does **not** treat the existing runtime composition as the default architectural truth.

A new minimal production path is established from the PydanticAI agent loop upward. Every additional model-visible capability must regain production authority through measured evidence.

This is a **controlled re-foundation**.

## 2. Runtime invariant set

### RUNTIME-1 — Shortest correct trajectory

For two trajectories that produce equivalent or better accepted outcomes, prefer the one with fewer semantic model decisions.

Do not optimize raw request count by hiding semantic decisions in unsafe deterministic code.

### RUNTIME-2 — Model-turn justification

A new model request is justified only when at least one holds:

1. a tool/external observation returned information that can materially alter the semantic decision;
2. the model must choose a new action based on changed state;
3. a validation result requires semantic revision;
4. a human/external actor supplied a meaningful delta.

These are not sufficient reasons by themselves:

- updating status;
- recording a receipt;
- persisting history;
- hashing files;
- reading a plan the host already knows;
- serializing fields;
- moving data between two deterministic components.

### RUNTIME-3 — Capability admission

No model-visible capability is production-default merely because:
- it exists upstream;
- it is reusable;
- it might be useful;
- another domain uses it;
- it is already implemented locally.

Admission requires the process in `CAPABILITY_ADMISSION.md`.

### RUNTIME-4 — Action surface

Expose a model tool only when the model must decide **whether** to perform the action or **how** to parameterize it based on semantic context.

Prefer deterministic helpers for:
- format conversion;
- indexing;
- batching;
- hashing;
- path creation;
- state bookkeeping;
- static validation;
- receipt writing.

### RUNTIME-5 — Semantic batching

Batch deterministic transport when doing so does not steal semantic judgment from the model.

Example:

```text
GOOD
host returns bounded materials M1..M9
model decides relevance/conflict/priority

BAD
host chooses M1/M3/M7 because host believes they are relevant
```

### RUNTIME-6 — Unknown convergence

When the available evidence cannot satisfy a requested fact and further use of the currently available evidence surface cannot change that state:

```text
observe
→ establish unsupported/unknown
→ preserve the unknown
→ continue feasible work or return partial
```

Repeated equivalent checks are a runtime regression.

### RUNTIME-7 — Revision

Default revision contract:

```text
current artifact
+ human delta
+ bounded current evidence/source state
+ unresolved items
→ revised artifact
```

Do not default to:
- full conversation-history search;
- replaying prior tool results;
- reconstructing old plans;
- reloading broad capabilities.

### RUNTIME-8 — History is not state

Message history is an interaction transcript.

Durable task state should be represented by the smallest authoritative state required for continuation.

A consumer must not search history merely to rediscover state that can be passed directly.

### RUNTIME-9 — Persistence is observational unless proven otherwise

Step persistence may record execution. Recording execution must not itself create business workflow steps.

Durability features are admitted according to the failure they solve.

### RUNTIME-10 — Core means invariant, not advanced

Core contains only cross-domain execution semantics that cannot safely vary by domain, such as:
- execution boundary;
- approval/effect semantics;
- settlement/integrity facts;
- composition authority/ABI;
- generic run usage/failure facts.

Planning, Memory, ConversationSearch, Skills, FileSystem, ToolOutputLimits, StepPersistence, SubAgents, ToolSearch, RepoContext, Shell and context controls are not "Core because advanced". They are admitted capabilities.

## 3. Minimal production path

The target initial canary path is conceptually:

```text
task
→ bounded domain observation
→ model semantic decision / artifact construction
→ necessary deterministic/domain validation
→ optional directed model revision
→ settlement
```

The exact number of calls is not hard-coded by this SPEC.

The implementation must make the minimal trajectory possible.

## 4. Domain toolset contract

A domain plugin should expose **semantic affordances**, not its internal implementation decomposition.

A model-visible tool passes the following test:

> If the host called this automatically every time, could it make the wrong business decision because the correct timing/arguments depend on semantic interpretation?

If no, strongly prefer a normal deterministic function/hook.

## 5. Capability modes

Every capability receives one of:

- `REQUIRED_INVARIANT` — cross-domain correctness boundary;
- `ADMITTED_PROFILE` — admitted for a measured deployment/task class;
- `EXPERIMENTAL` — benchmark only;
- `QUARANTINED` — retained for reference but no production authority;
- `DELETE_CANDIDATE` — no remaining authority/evidence.

Do not use a vague `enabled=True` as architectural justification.

## 6. Writing canary interpretation

Writing is not allowed to create Core semantics merely because its benchmark exposes a failure.

WCASE mapping:

- WCASE-1: minimal trajectory canary;
- WCASE-2: bounded observation / selection;
- WCASE-3: epistemic convergence;
- WCASE-4: delta revision.

A fix enters Core only when the mechanism is stable and domain-agnostic.

## 7. Runtime acceptance record

Every benchmark run should emit a compact record with:

```json
{
  "case": "WCASE-1",
  "variant": "minimal",
  "outcome_pass": true,
  "evidence_pass": true,
  "requests": 0,
  "tool_calls": 0,
  "input_tokens": 0,
  "output_tokens": 0,
  "reasoning_tokens": 0,
  "wall_clock_ms": 0,
  "model_visible_tools": [],
  "tool_counts": {},
  "repeated_signatures": [],
  "notes": []
}
```

Unknown provider metrics may be null. Do not fabricate metrics.

## 8. Regression rule

An iteration is rejected when:
- outcome/evidence quality regresses materially; or
- runtime complexity grows materially without demonstrated outcome benefit.

A new capability or model turn has a burden of proof.

## 9. Forbidden implementations

Do not solve this re-foundation by creating:
- `RuntimePlanner`;
- custom graph engine;
- custom workflow DSL;
- generic "convergence manager";
- global domain state schema;
- another receipt system;
- another history store;
- another memory layer;
- an evaluator that becomes production semantic authority.

Prefer upstream primitives or local deterministic code at the narrowest layer.

## 10. Authority migration

The old path remains available only as:
- regression oracle;
- benchmark reference;
- source of proven integration code.

Once the minimal path satisfies the migration gates, production authority moves deliberately. Old code is then deleted or quarantined according to `DELETION.md`.

