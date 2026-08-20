# PRD — Architecture Subtraction & Evidence Reset

## 1. Problem

ZUAEF has accumulated several abstractions that were originally introduced to make business-agent work auditable:

- host-side “verification”;
- model/host evidence references;
- typed knowledge categories;
- verified artifact / knowledge / tool-effect lists;
- status degradation based on those lists;
- Case identity in generic runtime dependencies;
- Case-specific host context projection;
- duplicated generalist capability configuration;
- editorial learning records compressed into fixed sensors/actions/weights.

These mechanisms create three product problems.

### P1 — False authority

The runtime can prove that a file changed or a tool event exists, but it cannot prove that the result is factually supported or high quality.

Calling these fields “evidence” or “verification” gives a stronger claim than the mechanism can support.

### P2 — Business semantics leak into infrastructure

`case_id`, Case context projection, knowledge semantic types, and growing capability flag lists force generic runtime code to know domain concepts.

Every future domain risks producing another field, branch, enum, and schema.

### P3 — Human judgment is destroyed during “structuring”

Existing editorial-learning records map real human edits into hard-coded abstractions such as:

```text
trigger_signals
action
directive
weight
approved_by
```

This transforms rich judgment into brittle labels before the model can learn from the actual example.

The system then optimizes around the schema rather than the work.

## 2. Product goal

Make ZUAEF a **thin, stable FDE runtime** whose correctness boundary is limited to execution mechanics, while moving semantic evidence and quality improvement into artifacts and review workflows.

### Goal statement

A new business capability should normally be deliverable without modifying the generic runtime, and a result should be trusted because:

1. the result itself is inspectable;
2. factual claims point to real sources;
3. LLM/human review can compare, annotate, revise, and promote better behavior;
4. runtime records only factual operational history.

## 3. Users

### Primary
- FDE/operator supervising a real agent.
- Coding agent maintaining ZUAEF.
- Business-domain plugin author.

### Secondary
- Human editor / reviewer.
- LLM critic / evaluator.
- Customer receiving final business artifacts.

## 4. Success criteria

### Architecture
- no Case-specific business identity in generic runtime contracts;
- no semantic evidence parser in the kernel;
- no kernel status downgrade because a semantic evidence field is missing;
- no new global capability boolean for every Harness capability;
- plugin ABI remains thin.

### Result evidence
For research/factual deliverables:
- claims are supported by readable citations or a source section containing real URLs/stable resource links;
- URLs are part of the artifact, not hidden in receipt metadata;
- an evaluator can open the sources and judge support.

### Quality learning
At least one real workflow demonstrates:

```text
task
→ model result
→ LLM critique grounded in result + sources
→ human accept/reject/edit
→ revised result / learning note
→ future run receives accepted learning
→ blind or explicit human comparison
```

No regex/sensor score is allowed to be called “truth” or “quality acceptance”.

## 5. Non-goals

This project must NOT introduce:

- a generic Evidence Framework;
- a Context Provider Registry;
- a Binding Registry;
- a Quality Plane runtime;
- an Event Bus;
- a Service Registry;
- a custom memory service;
- a custom agent loop;
- a custom durable runtime;
- a new database for evaluation;
- a vector database;
- automatic self-modifying production code;
- automatic promotion of LLM critique without human policy.

## 6. Product principles

### G1 — Operational facts are not semantic truth
Hashes, status codes, and tool events are facts about execution only.

### G2 — Evidence should travel with the work
If a deliverable depends on public factual sources, the deliverable should expose those URLs/citations directly.

### G3 — Human judgment stays rich for as long as possible
Store actual output, actual revision, actual feedback, and actual sources before deriving labels.

### G4 — Derivations are disposable
Indexes, metrics, embeddings, sensors, and labels may be generated for search/analysis, but are never the authority.

### G5 — The runtime does less
PydanticAI/Harness owns generic agent mechanics. ZUAEF should add only business-runtime semantics that are not upstream responsibilities.

### G6 — Promotion follows reviewed outcomes
A learning rule is promoted because reviewed results improved, not because a field says `approved_by=human-editor`.

## 7. User-visible behavior after refactor

### Normal result
The user receives the model's natural result directly.

### Research/factual result
The result includes inline links or a `Sources` section.

### Internal execution record
The system can still show:
- run ID;
- model;
- timestamps;
- usage;
- plugin composition;
- errors;
- artifact files and hashes;
- tool events;
- pause/resume state.

But it will not label those as semantic evidence.

### Quality iteration
Review happens outside the generic runtime and can generate:
- critique;
- human feedback;
- revised artifact;
- accepted learning note;
- benchmark comparison.

## 8. Definition of done

The project is done when a coding agent can read `ACCEPTANCE.md`, run the required real and deterministic checks, and demonstrate:

- smaller kernel;
- fewer semantic fields;
- no loss of approval/durability;
- source-linked artifacts;
- a working human/LLM learning cycle.

## 9. Capability-owned deliverable customization

A central product requirement is:

> **Business result shape is defined inside the Capability, not inside the Kernel.**

Examples must be able to coexist with zero generic-result schema changes:

```text
WritingCapability     → article-shaped result
ResearchCapability    → sourced research report
BudgetCapability      → numeric/business analysis
NegotiationCapability → customer reply / strategy output
WordPressCapability   → publishable post state / operator presentation
```

The generic runtime must not acquire a union of all those fields.

Success means adding or changing a result structure requires touching the owning Capability/plugin and its tests, not `models.py`, `runtime.py`, generic receipt models, or a central result registry.


## 10. Pydantic usage rule

Pydantic defines data contracts, not business-process gates.

Use it for:
- tool/API inputs;
- plugin config;
- persisted data;
- deterministic domain objects.

Do not use it to encode:
- workflow phase;
- semantic completeness;
- research sufficiency;
- writing readiness;
- approval-by-field;
- “all required fields present, therefore the Agent may continue”.

If a process decision requires judgment, leave it to the Agent/Capability or a real human approval boundary.
