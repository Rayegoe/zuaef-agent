# T006-B5 — Synthesis evidence preservation (benchmark A/B)

Status: COMPLETE — verdict `WEAKEN_PRIMARY_HYPOTHESIS`. The ONE-factor
instruction did not produce a material reduction in the predeclared
evidence-preservation failures; the same failure families persist in the
candidate. Primary causal hypothesis weakened; competing salience /
context-representation explanation gains support. NO production promotion.
Evidence returned to Supervisor per the frozen approval.

Date: 2026-08-24
Baseline commit: `1b0e46bbf5e67de00a194c3e5b68638b230434f7`

## Question

On the frozen `REAL-AGENT-TRUST-1` technique-OFF path, does appending exactly
ONE compact synthesis instruction — preserve the source's semantic boundaries
(who states / source-benchmark scope / modal-logical strength / responsibility
subject) when converting evidence into article claims — reduce the
predeclared proposition-level evidence-preservation failures reproduced in the
full-desk-pack adjudication of the frozen T006-B3 X/Y/Z artifacts?

- Control (A): technique-OFF writer path, existing writer instructions.
- Candidate (B): identical OFF path + the one instruction, nothing else.

## Frozen identity

| fact | value |
| --- | --- |
| base commit | `1b0e46bbf5e67de00a194c3e5b68638b230434f7` |
| case | `REAL-AGENT-TRUST-1` |
| assignment | 《AI Agent 越来越容易造，为什么企业还是不敢把工作交给它？》 |
| model | `deepseek/deepseek-v4-flash-0731` via OpenRouter (`.env` LLM_MODEL / LLM_API_BASE) |
| request / tool budget | `12 / 40`, total-token unset (identical to T006-B3) |
| profile | `ace-writing-t006-b1-technique-off` (both arms; technique guidance OFF) |
| EPUB corpus | same `WhereMyLife__2026_08_20` converted corpus; same five raw windows (7,288 chars) |
| human learning | same `learning/` projection; same desk-pack human-review section |
| retrieval | unchanged; no `pull_context` in any of the six runs |
| available tools | unchanged (`pull_context`, `save_article` only; technique OFF) |
| artifact submission | identical `save_article` semantics |

## Implementation — exactly one semantic factor

Smallest seam to expose the candidate instruction to the benchmark:

- `examples/production_writing.py`: `render_agent_prompt(...)` and
  `run_production_task(...)` accept an optional
  `synthesis_boundary_instruction: str | None = None`. When set, ONE section
  is appended to the writer instructions immediately before the closing
  protocol. Default `None` → byte-identical behavior to the pre-change
  control prompt. The evidence desk pack (`writer_context`) is never touched.
- `tools/run_writing_eval.py`: `--synthesis-boundary` flag; constant
  `SYNTHESIS_BOUNDARY_INSTRUCTION` (the general rule, encodes none of the
  X/Y/Z corrections); recorded in `observation_controls`.

Candidate instruction text (verbatim):

> When turning evidence into article claims, preserve who owns or states the
> evidence, its source/benchmark scope, its modal/logical strength, and the
> responsibility subject. Do not strengthen, generalize, or transfer these
> boundaries merely to make the thesis cleaner.

First-request prompt identity (verified from persisted run snapshots):

| | control (any A) | candidate (any B) | delta |
| --- | --- | --- | --- |
| prompt chars | 15,300 | 15,605 | +305 (the instruction section only) |
| evidence desk pack chars | 14,733 | 14,733 | byte-identical (sha `d9620a987ffe`) |

The desk pack is byte-identical across ALL SIX runs (verified: six identical
SHA-256 of the extracted pack). The ONLY text difference between arms is the
single appended instruction. No `pull_context` was called in any run, so the
first-prompt desk pack is the complete evidence set each model saw.

Production default writer behavior is unchanged (default `None`); no profile,
plugin, corpus, retrieval or budget was changed.

## Commands (one per run)

```text
# control (A arm)
uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing-t006-b1-technique-off --no-technique-guidance \
  --request-limit 12 --out .../t006-b5/control-{1,2,3}

# candidate (B arm) — identical + one factor
uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing-t006-b1-technique-off --no-technique-guidance \
  --request-limit 12 --synthesis-boundary --out .../t006-b5/candidate-{1,2,3}
```

Paired adjacency: `control-1→candidate-1`, `control-2→candidate-2`,
`control-3→candidate-3`. Three replicates per arm. Per-run full conversation
and first-request prompt captured from the step store into each run's
`context/` dir.

## Run facts (mechanical, not verdicts)

| run | status | requests | tool calls | artifact chars | artifact sha |
| --- | --- | --- | --- | --- | --- |
| control-1 | completed | 8 | save_article ×7 | 2,446 | `37eb9bb857…` |
| candidate-1 | completed | 2 | save_article ×1 | 2,385 | `2e234fbb0d…` |
| control-2 | limit_reached | 12 | save_article ×12 | 2,002 | `b38ac547f3…` |
| candidate-2 | completed | 3 | save_article ×2 | 2,225 | `ebebc644b7…` |
| control-3 | limit_reached | 12 | save_article ×12 | 2,162 | `75877a7534…` |
| candidate-3 | limit_reached | 12 | save_article ×12 | 2,305 | `8cdf687154…` |

Runtime/terminal-state is recorded as an ordinary metric; runtime reduction is
NOT the objective of this iteration.

## Blind adjudication

- Rubric predeclared before any artifact was read:
  `blind-b5/rubric.md` (classes 1–5 + business quality guard).
- Anonymous artifacts `A–F` (shuffled, mapping sealed until after review) +
  the complete desk pack: `blind-b5/artifacts/`, `blind-b5/desk-pack.md`.
- Blind record: `blind-b5/REVIEW.md` — every failure lists the exact draft
  proposition and the desk-pack boundary it violates.

Blind per-artifact evidence-failure counts (before reveal):

| artifact | c1 attrib | c2 scope | c3 logical | c4 resp | c5 detail | total |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0 | 0 | 0 | 0 | 0 | 0 |
| B | 0 | 1 | 0 | 0 | 1 | 2 minor |
| C | 0 | 0 | 0 | 0 | 0 | 0 |
| D | 0 | 1 | 0 | 0 | 0 | 1 minor |
| E | 0 | 0 | 0 | 0 | 1 | 1 minor |
| F | 0 | 0 | 0 | 0 | 0 | 0 |

Revealed mapping:

```text
D = control-1      (1 minor: c2 benchmark scope)
E = control-2      (1 minor: c5 10→5 min figure)
A = control-3      (0)
C = candidate-2    (0)
F = candidate-1    (0)
B = candidate-3    (2 minor: c2 benchmark scope + c5 WorkHelp name)
```

## Result

| arm | evidence failures (3 replicates) | families seen |
| --- | --- | --- |
| Control (A) | 2 minor | c2 benchmark-scope generalization (D); c5 figure drift (E) |
| Candidate (B) | 2 minor | c2 benchmark-scope generalization (B); c5 name drift (B) |

- NO material reduction in predeclared evidence failures: 2 per arm.
- The same failure families persist in the candidate: benchmark-scope
  generalization and concrete-detail drift both appear in BOTH arms.
- Candidate did not introduce a new failure family, but the "material
  reduction" half of the acceptance condition is not met.
- Business quality guard: PASS for all six — every artifact remains an article
  with an argument; none became source-by-source summary, disclaimer laundry,
  citation ledger or mechanically qualified prose.
- No modal-strength flip, no responsibility-subject drift, no fabricated
  person/company in any artifact; the failures are minor and at the margin.

## Verdict

```text
WEAKEN_PRIMARY_HYPOTHESIS
INCREASE_SUPPORT_COMPETING_SALIENCE_OR_CONTEXT_REPRESENTATION_EXPLANATION
NO_MATERIAL_EVIDENCE_REDUCTION
ACCEPTANCE_NOT_MET
QUALITY_GUARD_PASS
NO_PRODUCTION_PROMOTION
EVIDENCE_RETURNED_TO_SUPERVISOR
T007_DEFERRED
STOP_AFTER_EXPERIMENT
```

Per the frozen approval interpretation: the same failure families persist
despite the instruction ⇒ weaken the synthesis-compression hypothesis and
increase support for the competing salience / context-representation
explanation.

No additional mechanism was introduced. No promotion. This worker stops after
the paired experiment and its artifacts, per worker authority.

## Interpretation boundary

- Small sample (3 replicates per arm) and a low base rate (4 minor failures in
  6 runs). This iteration cannot rule out a small candidate effect; it does
  rule out the "material reduction" required by the acceptance condition.
- The blind gate was a single reviewer who also generated the shuffle. Review
  was content-driven against the complete desk pack with the predeclared
  classes and independently reproducible excerpts; this is a limitation, not
  a substitute for an independent adjudicator.
- Reasonable next step (NOT taken here, requires Supervisor): a
  salience-focused variant — keep the desk pack identical and make the
  qualification *more salient inside the evidence* (e.g. per-window boundary
  markers), which is the competing hypothesis's predicted lever. That is a
  different experiment and is out of this worker's authority.

## Artifacts

- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/t006-b5/{control-1,candidate-1,control-2,candidate-2,control-3,candidate-3}/` — bundles, drafts, records, `context/` (persisted first prompts + full conversations)
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/t006-b5/desk-pack.md` — the complete evidence desk pack (14,733 chars)
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/t006-b5/blind-b5/` — rubric, anonymized artifacts A–F, mapping, REVIEW.md

## Code change surface (benchmark-only, frozen baseline)

- `examples/production_writing.py` — optional `synthesis_boundary_instruction` seam (default None; control prompt byte-unchanged).
- `tools/run_writing_eval.py` — `--synthesis-boundary` flag + instruction constant + `observation_controls` field.
- No profile/plugin/corpus/retrieval/budget change; production default writer behavior unchanged.
