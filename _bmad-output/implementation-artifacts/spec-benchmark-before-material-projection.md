---
title: 'Benchmark BEFORE Material Projection'
type: 'bugfix'
created: '2026-08-17'
status: 'draft'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The editorial benchmark's derived task record stores the assignment prompt in `material` and the source document to be revised in `before`. The benchmark runner, OLD/NEW comparison, and sequential-v1 runner currently pass `full["material"]` as the article body. T01 therefore gives the model a 144-character instruction instead of the BEFORE document, yet artifact existence is still recorded as success.

**Approach:** Establish one explicit benchmark input seam that distinguishes the task assignment from the BEFORE document. All benchmark execution paths must project the real `before` text as material, retain the assignment/intent in the prompt, and fail loudly when a derived task has no usable BEFORE body. Add contract tests that reproduce the exact T01 failure and prevent an artifact from being treated as a valid revision when the body is missing.

## Boundaries & Constraints

**Always:** Preserve the existing curated/compiler ABI, the production Host projection boundary, the shared runtime, claims/source immutability, and all unrelated dirty-tree changes. Keep benchmark raw/full text local-only. A valid revision run must receive non-empty BEFORE text and the assignment intent as separate context fields.

**Ask First:** None for this bugfix; changing the benchmark task schema beyond the smallest compatibility-preserving adapter requires a separate decision.

**Never:** Do not modify Writer/Editor instructions to compensate for missing input, weaken artifact validation, fabricate a BEFORE document, use `after` as runtime input, or make the compiler/agent retrieve benchmark material implicitly.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | `full.material` is assignment text and `full.before` is the real document | Prompt contains assignment plus BEFORE; material file and WritingContext contain BEFORE | N/A |
| MISSING_BEFORE | `before` absent, empty, or whitespace | No model call and no success artifact | Raise a clear validation error naming the task and required field |
| PROMPT_ONLY | `material` contains only the assignment, as current T01 | Runner must not use it as article body | Contract test fails if prompt text is projected as material |

</frozen-after-approval>

## Code Map

- `benchmarks/editorial-learning/scripts/build_tasks.py` -- defines the derived task fields and their semantics.
- `benchmarks/editorial-learning/scripts/run_benchmark.py` -- Gate E runner and material ingestion.
- `benchmarks/editorial-learning/scripts/compare_paths.py` -- OLD/NEW/Writer-Editor benchmark adapter.
- `benchmarks/editorial-learning/experiments/sequential-v1/scripts/common.py` and `run_experiment.py` -- Gate F task loading and execution.
- `tests/test_editorial_benchmark.py` -- committed benchmark contract tests.

## Tasks & Acceptance

**Execution:**

- [ ] Add a shared, compatibility-preserving task-input adapter that returns `before` as source text and the existing `material` value as assignment text; reject missing/empty `before`.
- [ ] Route `run_benchmark.py`, `compare_paths.py`, and sequential-v1 through the adapter; pass assignment and BEFORE separately to Writer and Editor.
- [ ] Add regression tests for T01-shaped prompt-only input and for missing BEFORE rejection; regenerate local derived materials and invalidate the old blind-eval receipts.

**Acceptance Criteria:**

- Given a T01-shaped derived record, when any benchmark path prepares material, then the material file and first WritingContext contain the full BEFORE body, not the 144-character assignment.
- Given a missing or empty `before`, when a runner starts, then it exits before model execution with a task-specific validation error and creates no success artifact.
- Given a Writer-Editor run, when the Editor receives the draft, then its context includes the same BEFORE body and assignment intent used by the Writer.
- Given the repository contract suite, when tests and delivery-scope lint run, then all existing tests remain green and new projection tests pass.

## Spec Change Log

## Verification

**Commands:**

- `pytest -q tests/test_editorial_benchmark.py tests/test_production_writing.py` -- expected: all pass, including projection guards.
- `pytest -q` -- expected: full suite passes.
- `ruff check src/ plugins/ examples/ benchmarks/ tests/ tools/` -- expected: clean.

