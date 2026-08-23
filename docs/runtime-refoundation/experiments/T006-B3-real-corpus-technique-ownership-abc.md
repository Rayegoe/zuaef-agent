# T006-B3 — Current-main real-corpus technique ownership A/B/C

Status: blind human quality/evidence judgment recorded. Technique OFF won the
quality ranking, model-owned eager catalog placed second and Host-selected
placed third. Evidence remained unclear. Verdict: `REFINE`; no production
authority change.

Date: 2026-08-21

## Question

On current `main`, with one real writing task, one model, one WhereMyLife EPUB
corpus, one raw-material set, one human-learning store and one budget, does the
editorial/evidence result differ across:

- A: Host-selected technique bodies;
- B: technique OFF;
- C: model-owned neutral technique catalog and optional exact-ID retrieval?

This run does not pre-fix the prior Candidate's evidence failure and adds no
Host technique, scene or schema judgment.

## Frozen identity

| fact | value |
|---|---|
| base branch / commit | `main` / `cbea05e2362f40eea7aac4641f2c9b1a56bd78cb` |
| origin state before fixture | `main...origin/main` |
| case | `REAL-AGENT-TRUST-1` |
| assignment | 《AI Agent 越来越容易造，为什么企业还是不敢把工作交给它？》 |
| model | `deepseek/deepseek-v4-flash` through the existing compatibility endpoint |
| thinking | `null`; provider default |
| request / tool-call budget | `12 / 40` for every run |
| total-token budget | unset for every run |
| EPUB corpus | `WhereMyLife__2026_08_20.epub` converted corpus dated `2026-08-20` |
| corpus receipt | 1,676 articles, 34 sources, 1,713 TOC entries |
| human learning | the same repository `learning/` projection for all first requests |
| raw task materials | the same five byte-identical continuous source windows |

The source EPUB binary is not stored under the ignored corpus directory, but
the existing converted corpus includes the receipt, manifest, 1,676 article
files and the original EPUB filename. No ingestion or converter code changed.

## Mechanical material selection

The fixture contains no `insight`, `angle`, `hook`, expected structure or
material-role fields. Each raw file was compared byte-for-byte against the
corresponding continuous lines in the converted corpus before execution.

| material | source lines | characters |
|---|---|---:|
| `WML-20260820-21-003-L013-L065.md` | `WML-20260820-21-003:13-65` | 2,081 |
| `WML-20260820-21-009-L067-L117.md` | `WML-20260820-21-009:67-117` | 1,225 |
| `WML-20260820-21-041-L055-L083.md` | `WML-20260820-21-041:55-83` | 1,472 |
| `WML-20260820-21-056-L011-L027.md` | `WML-20260820-21-056:11-27` | 871 |
| `WML-20260820-21-056-L381-L429.md` | `WML-20260820-21-056:381-429` | 1,639 |
| total | five windows | 7,288 |

The source mapping and inspectable URLs are in
`benchmarks/writing-cases/REAL-AGENT-TRUST-1/case.json`.

## Commands

```text
uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing --technique-selection-mode host --request-limit 12 \
  --out workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/current-main-host

uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing-t006-b1-technique-off --no-technique-guidance \
  --request-limit 12 \
  --out workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/current-main-off

uv run python tools/run_writing_eval.py REAL-AGENT-TRUST-1 \
  --profile ace-writing-t006-b2-model-owned-techniques \
  --technique-selection-mode model --request-limit 12 \
  --out workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/current-main-model-owned
```

## First-request context distribution

Character counts are measured from the persisted first-request prompt. Section
headers are included in their section count; the fact-boundary and final
protocol text are not assigned to any of the four requested categories.

| actual first-request input | A Host | B OFF | C model-owned |
|---|---:|---:|---:|
| complete prompt | 16,296 | 15,301 | 18,505 |
| task materials | 7,536 | 7,536 | 7,536 |
| human learning | 1,885 | 1,885 | 1,885 |
| EPUB windows | 5,248 | 5,248 | 5,248 |
| technique bodies / catalog actually entered | 995 | 0 | 3,187 |
| tail truncation marker | no | no | yes, 16 characters including newline |

A received three Host-selected bodies:

```text
ex-quote-twovoices-001
ex-braid-mechanism-001
ex-braid-history-001
```

C's source catalog contains 18 rows / 3,606 characters before the surrounding
header and selection contract. The bounded desk pack retained 14 complete rows
and part of `ex-ending-number-001`; it cut that row at `author_in`. The final
three rows were absent:

```text
ex-final-unfinished-001
ex-final-questions-001
ex-final-quote-001
```

Thus the only first-request distribution difference is the requested technique
mode, and the C catalog is the only section whose tail was cut.

## Model-owned observation facts

C made no `pull_techniques` call. Zero selected techniques is legal under the
existing contract, so this is an exercised model-owned decision, but it means
this sample compares Host bodies and OFF against a catalog-visible / zero-body
model-owned trajectory. It does not show which technique bodies the model would
have selected if it had chosen to retrieve any.

B made one model-owned `pull_context` call with query:

```text
DSH 4300 plugins success rate enterprise trust agent
```

That later observation added 7,536 task-material characters and 3,152 EPUB
characters. It did not include a human-learning section or a technique section,
and it was not tail-truncated. A and C made no later observation call.

## Mechanical run results

These are execution facts, not quality or evidence verdicts.

| metric | A Host | B OFF | C model-owned |
|---|---:|---:|---:|
| execution state | completed | completed | completed |
| model requests | 2 | 3 | 2 |
| tool calls | 1 | 2 | 1 |
| tool sequence | `save_article` | `pull_context -> save_article` | `save_article` |
| input tokens | 24,845 | 40,991 | 24,444 |
| output tokens | 6,813 | 4,260 | 5,814 |
| reasoning tokens | 5,093 | 2,131 | 3,897 |
| cache-read tokens | 0 | 32,000 | 0 |
| largest input tokens | 15,701 | 17,137 | 14,741 |
| wall clock ms | 139,110.172 | 90,588.848 | 103,617.782 |
| artifact characters | 2,796 | 3,224 | 2,974 |
| artifact SHA-256 | `86346f...00c3` | `f70449...2551` | `a8afbf...05b` |

The B input/token difference is explained at least in part by its one additional
semantic observation. One run per mode is not a causal speed claim.

## Blind gate and revealed result

Review only:

- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind/X.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind/Y.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind/Z.md`
- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/blind/REVIEW.md`

The copies were mechanically verified against their source artifacts. The
reviewer recorded `Z > X > Y` before the mapping was revealed:

```text
X = model-owned eager catalog
Y = Host-selected techniques
Z = technique OFF
```

Quality interpretation: OFF best rebuilt a relationship from the materials;
model-owned was steadier but became over-complete in its final Harness
explanation; Host most strongly exhibited repeated summary/framework moves.
Evidence remained `unclear` because the blind reviewer did not receive the
complete desk pack. See `T006-B3-human-judgment.md`.

## Current decision

```text
EXECUTION_COMPLETE
OFF_COMPARATIVE_QUALITY_WIN
EVIDENCE_UNCLEAR
REFINE
NO_PRODUCTION_PROMOTION
T007_DEFERRED
```

No technique mode is promoted globally. B1, B2 and B3 disagree on the
comparative winner, which is evidence of task dependence rather than grounds
for a permanent Host/ON/OFF rule. The next narrow experiment is a benchmark-only
lazy model-owned catalog: keep the initial desk pack at the OFF shape, and let
the model decide whether to observe the neutral catalog and then retrieve exact
technique IDs.
