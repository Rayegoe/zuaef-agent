# ACCEPTANCE — Outcome Gates

## A. Architectural subtraction

### A1 — Kernel vocabulary
PASS if generic runtime source has no business Case semantics except migration/legacy comments that are scheduled for deletion.

Required checks include:

```text
CoreDeps has bindings, not case_id
runtime has no cross-case branch
gateway bridge does not project Case context
```

### A2 — No evidence framework replacement
PASS if deletion of old evidence machinery does not introduce:
- evidence registry;
- evidence provider interface;
- quality registry;
- context registry;
- binding registry.

### A3 — Plugin ABI remains thin
PASS if plugin factories still resolve to the existing primitive bundle concept.

## B. Runtime truthfulness

### B1 — Operational receipt only
PASS if a fresh receipt can truthfully answer execution questions without claiming content correctness.

FAIL if fields named `verified_*` imply semantic validity.

### B2 — No fake semantic downgrade
Given a valid natural model result with no model-crafted evidence metadata:

```text
expected: execution completed
```

It MUST NOT become `partial` merely because:
- no `evidence` ref was emitted;
- no knowledge frontmatter source field exists;
- no artifact claim was copied into a summary.

### B3 — Safety remains
Must still pass:
- path containment;
- native external/destructive approval;
- pause/resume;
- exact composition restore;
- usage boundaries;
- secret isolation.

## C. Case de-coupling

### C1
A bound Case still supplies useful background.

### C2
Case tools still enforce case isolation.

### C3
Cross-case external effect never reaches operator approval.

### C4
The generic kernel itself has no Case-specific validation.

## D. Evidence-bearing artifact

Create at least one real factual/research artifact.

PASS if:
- the artifact contains real source URLs or stable inspectable resource links;
- major factual claims can be mapped to sources by a human reader;
- an evaluator actually opens/checks a sample of cited sources.

FAIL if the only “evidence” is:
- a SHA-256;
- a `knowledge:` identifier;
- a `tool-effect:` identifier;
- `approved_by`;
- a source-count field.

## E. Learning loop

At least one full loop:

```text
real task
→ real output
→ LLM prose critique
→ human feedback/edit
→ accepted lesson
→ applied to later task
→ comparison
```

PASS requires preserved raw human feedback and actual before/after text.

FAIL if human judgment is reduced first to:
- action enum;
- sensor enum;
- numeric weight;
- confidence field.

## F. Quality comparison

For the first migration slice, target 5 or more comparable tasks where possible.

Report human pairwise preference.

A valid row contains at minimum:
- task reference;
- baseline artifact;
- candidate artifact;
- human preference/comment.

No hard-coded machine threshold may declare writing quality PASS without human judgment.

## G. Regression

Required deterministic gates:
- `pytest`;
- lint used by repository;
- plugin list/inspect/profile check;
- composition snapshot tests;
- resume tests.

Required real gates where environment allows:
- real model run;
- source-linked deliverable;
- approval/resume external-effect flow.

If a real gate cannot run because credentials/network are unavailable, mark it `NOT RUN` with the exact missing prerequisite. Do not replace it with a field assertion and call it proved.

## H. Final code-shape check

The final change should preferably reduce conceptual surface.

Measure and report:
- deleted files/functions/classes;
- added files/functions/classes;
- receipt field count before/after;
- kernel business-specific identifiers before/after.

This is descriptive, not a quality score.

## I. Capability-owned Result Contract

### I1 — Three result shapes, one runtime

Run at least three materially different domains, for example:

```text
writing       → article
budget        → budget analysis
client-service/research → reply or sourced report
```

PASS if all use the same generic Kernel terminal/output contract.

### I2 — Structure-only change isolation

Make a harmless structure-only change in one test fixture/capability, for example:
- writing moves source notes to a final section;
- budget changes report section order.

PASS only if the implementation change is confined to the owning capability/plugin (plus its tests/fixtures).

FAIL if it requires editing:
- generic `models.py`;
- `runtime.py`;
- receipt schema;
- a central result registry.

### I3 — No universal business result schema

Search source for newly introduced abstractions such as:

```text
BusinessResult
ResultSchema
ResultRegistry
DeliverableType
ArtifactKind
```

Any such generic abstraction requires explicit proof from multiple domains; otherwise FAIL.

### I4 — Capability owns evidence presentation

Research/factual capability can require visible source URLs.
Writing capability can use a different source convention.
Budget capability can cite its input data rather than web URLs.

PASS if no global `sources`/`evidence` field is required across all results.


## J. Pydantic is not workflow governance

### J1 — No field-driven phase machine

Search the new/modified generic code for workflow fields such as:

```text
research_complete
draft_ready
quality_passed
evidence_passed
next_stage
phase
workflow_status
```

A domain API may legitimately use a field named `status`; this gate concerns fields used to control the Agent's reasoning/work sequence.

PASS if business work can proceed through the Agent loop without filling a predefined phase schema.

### J2 — Pydantic stays at data boundaries

Inspect representative Pydantic models.

PASS if their purpose is object/config/API/persistence shape.

FAIL if a model exists primarily to decide whether the Agent may proceed to the next semantic step.

### J3 — Approval remains authorization, not workflow

External/destructive effects may still require native approval.

PASS if approval is tied to the actual effect boundary rather than “draft phase completed” or similar process state.
