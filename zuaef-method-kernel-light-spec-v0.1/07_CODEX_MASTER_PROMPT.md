# Codex Master Prompt — ZUAEF Method Kernel v0.1

Implement the lightweight ZUAEF Method Kernel.

The objective is NOT to build another framework.

The objective is to make ZUAEF better at:

```text
reconstructing reality
using evidence
choosing the smallest intervention
making uncertainty explicit
falsifying important conclusions
learning only from proven improvements
```

## First inspect

Read:

```text
src/zuaef_agent/core.py
tools/llm_reviewer.py
tools/promote_lesson.py
learning/
relevant tests
```

Classify:

```text
REUSE
EXTEND
MISSING
```

before changing code.

---

## Change 1 — Core

Add or refine a very small Method Kernel in `CORE_INSTRUCTIONS`.

It should encode roughly:

```text
1. Reconstruct reality before proposing change.
2. Evidence outranks explanation.
3. Prefer the smallest intervention that can prove the outcome.
4. Make material uncertainty explicit.
5. Try to falsify important conclusions.
6. Promote only what survives evidence.
```

Keep it short.

Do not add a mandatory workflow/checklist.

---

## Change 2 — Reviewer

Generalize the existing independent reviewer instead of creating a new reviewer platform.

It should work across:

```text
documents
implementation
research
architecture
business deliverables
```

Keep prose-first output.

Do not add score enums or fixed labels unless an existing evaluator already requires them.

---

## Change 3 — Promotion

Make learning promotion intervention-neutral.

A promoted result may be:

```text
nothing
prompt line
example
test
tool fix
plugin fix
data fix
skill
architecture fix
retirement/deletion candidate
```

Human review remains authoritative.

No auto-promotion.

---

## Change 4 — Ablation

Add the smallest useful baseline-vs-candidate experiment runner using existing runtime/receipts/evaluators.

Compare, where available:

```text
task completion
quality
factual errors
requests
tokens
tool calls
latency
```

Do not invent a universal scalar score.

---

## Required proof

Use at least one real historical ZUAEF case.

Preferred examples:

```text
600550 cache-miss service failure
Quant research Skill with/without
a historically overlong prompt
```

Demonstrate that the Method Kernel leads to a smaller or better-evidenced intervention.

---

## Hard constraints

Do not:

- create a new Agent framework;
- create a new workflow engine;
- create a Method Skill with hundreds of lines;
- force reviewer on every run;
- force ablation on every run;
- introduce SubAgents/Swarm just for review;
- duplicate Harness functionality;
- add a new database;
- make learning assets append-only forever;
- auto-delete Skills without human approval;
- turn the six principles into a rigid state machine.

---

## Definition of Done

The change is done when:

1. Core has a concise, domain-agnostic Method Kernel.
2. Existing reviewer is reusable beyond writing.
3. Promotion can recommend simplify/replace/delete, not only add.
4. A minimal ablation path exists.
5. At least one real case proves the approach.
6. Simple tasks remain simple.
7. No new framework was introduced.

Return:

```text
Reused
Changed
Real proof
Ablation result
What was deleted/simplified
What remains unproven
```
