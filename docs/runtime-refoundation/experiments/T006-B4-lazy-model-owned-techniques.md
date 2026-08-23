# T006-B4 — Lazy model-owned technique observation

Status: blind judgment complete. Technique OFF (Q) beat model-lazy (P), and
both failed evidence. Verdict: `REVERT`; no production promotion. The failed
benchmark surface was removed after the gate.

Date: 2026-08-21

## Reproduced failure and one causal change

T006-B3's eager model-owned mode put 3,187 technique-catalog characters into
the first request, truncated the catalog tail and then selected zero technique
IDs. The OFF draft won the blind quality ranking. B1, B2 and B3 nevertheless
had different comparative winners, so the B3 result does not justify a global
OFF rule.

This iteration changes only observation timing:

- the initial `model_lazy` desk pack is byte-for-byte the same rendered text as
  technique OFF;
- the model may call `pull_technique_catalog` to observe neutral metadata;
- it may then call `pull_techniques` once with 0–3 exact IDs;
- neither tool ranks, adds or substitutes a technique;
- Host makes no new technique, scene, schema or evidence judgment;
- production default remains `host`.

The benchmark mode and profile are experimental. This is not a new runtime
capability, state machine, reward model or reinforcement-learning subsystem.

## Frozen comparison

| fact | value |
|---|---|
| control | frozen T006-B3 OFF winner / former anonymous Z |
| candidate | current-main `model_lazy` |
| case | `REAL-AGENT-TRUST-1` |
| model | `deepseek/deepseek-v4-flash` through the same endpoint |
| task / audience / constraints | unchanged |
| raw materials | same five continuous WhereMyLife windows |
| human learning | same repository `learning/` projection |
| EPUB corpus | same converted `WhereMyLife__2026_08_20.epub` corpus |
| request / tool-call budget | `12 / 40` |

## Candidate command

```text
uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing-t006-b4-lazy-model-techniques \
  --technique-selection-mode model_lazy --request-limit 12 \
  --out workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/current-main-model-lazy
```

## First-request context distribution

The persisted prompt content contains 15,300 characters. The B3 measurement
convention used `jq -r`, whose terminal newline makes the comparable complete
prompt count 15,301.

| actual first-request input | frozen OFF | model-lazy |
|---|---:|---:|
| complete prompt, B3 extraction convention | 15,301 | 15,301 |
| task materials | 7,536 | 7,536 |
| human learning | 1,885 | 1,885 |
| EPUB windows | 5,248 | 5,248 |
| technique body / catalog actually entered | 0 | 0 |
| tail-truncated section | none | none |

The candidate's first-request desk pack therefore removes the reproduced eager
catalog distribution cost. The instruction/tool schemas still differ because
the candidate must own the optional observation decision; this is part of the
mechanism being tested, not an assertion of zero model-boundary cost.

## Mechanical candidate result

| metric | model-lazy candidate |
|---|---:|
| execution state | completed |
| model requests | 2 |
| tool calls | 1 |
| tool sequence | `save_article` |
| catalog observations | 0 |
| selected technique IDs | 0 |
| input tokens | 23,661 |
| output tokens | 6,610 |
| reasoning tokens | 4,896 |
| largest input tokens | 14,789 |
| wall clock ms | 125,845.647 |
| artifact characters | 2,719 |
| artifact SHA-256 | `c228ce...f51` |

The model exercised the legal zero-technique path without inspecting the
catalog. Thus this single trajectory tests OFF-shaped context plus the cost and
semantic choice of optional technique tools; it does not test quality after an
actual technique retrieval.

## Blind gate

Review packet:

- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind-b4/P.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind-b4/Q.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind-b4/SOURCE-DESK-PACK.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind-b4/REVIEW.md`

P and Q were mechanically verified against their source artifacts. Unlike B3,
the complete first-request evidence desk pack was included. The reviewer
recorded `Q > P`, then the mapping was revealed as P = model-lazy and Q =
frozen technique OFF. Both received `FAIL` for evidence. See
`T006-B4-human-judgment.md`.

## Current decision

```text
EXECUTION_COMPLETE
LAZY_OBSERVATION_CHOSEN_ZERO_TIMES
INITIAL_DISTRIBUTION_MATCHES_OFF
QUALITY_OFF_WIN
EVIDENCE_BOTH_FAIL
REVERT_LAZY_BENCHMARK_SURFACE
NO_PRODUCTION_PROMOTION
T007_DEFERRED
```
