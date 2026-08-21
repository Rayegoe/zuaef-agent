# T006 — WCASE-2 Observation / Semantic-Ownership Proof

Status: complete — observation proof; no production-code change.

Date: 2026-08-21

## CURRENT BASELINE

Fresh current production run:

```text
uv run python tools/run_writing_eval.py WCASE-2 --profile ace-writing \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-current
```

The runner cleaned the workspace before preparation. Evidence is preserved in:

- `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-current/draft-record.json`
- `.zuaef-state/steps/wcase-2-multi-material/snapshots/0.json`
- `workspace/artifacts/wcase-2-multi-material/final.md`

The execution completed, but this fresh run has no human WCASE-2 quality
judgment. Therefore:

```text
execution status: completed
quality outcome gate: UNJUDGED / null
evidence gate: UNJUDGED / null
```

The mechanical baseline is:

| fact | observation |
|---|---:|
| model requests | 2 |
| tool calls | 1 |
| tool names | `save_article` once |
| `pull_context` calls | 0 |
| model-visible tools | `pull_context`, `save_article` |
| input tokens | 47,654 |
| output tokens | 39,943 |
| reasoning tokens | 38,752 |
| cache-read tokens | 43,776 |
| largest input | 43,704 tokens |
| wall clock | 273,033.832 ms |
| request latencies | 268,234.699 ms; 4,712.746 ms |
| `save_article` latency | 1.229 ms |
| saved artifact | 1,310 chars |
| material count | 9 |

The first model request contained a 5,463-character desk pack. All nine raw
material bodies were represented in full. The per-material budget was 1,222
characters (`11,000 / 9`, bounded below by 1,200); every raw body was shorter
than that budget, and the 18,000-character desk-pack cap was not reached.

The first request therefore contained the following source material content:

```text
M001 full   M002 full   M003 full   M004 full   M005 full
M006 full   M007 full   M008 full   M009 full
```

The artifact’s source use is an observation, not a quality verdict: it uses
the core field test, founder interview and formal specification, uses the
brand/pricing secondary material, does not use the three irrelevant files, and
does not present the early conflicting figures as current figures.

## HOST TRANSFORMATION AUDIT

The production entry builds `context_query` from assignment, audience and
constraints, then calls `build_writer_context()` before the first model turn
(`examples/production_writing.py:383-399`). The classifications below are
about what the functions can do, followed by what actually happened in this
WCASE-2 run.

| transformation | classification | current behavior |
|---|---|---|
| `_material_rows` | `MECHANICAL_TRANSPORT` | Parses ACE JSON-lines material metadata. |
| `_material_body` | `MECHANICAL_TRANSPORT` | Removes ACE wrapper/receipt lines; does not choose meaning. |
| `_relevance` | `SEMANTIC_PRESELECTION` | Converts lexical overlap into a relevance score used for direct-match and ranking decisions. |
| `_bounded_excerpt` | `SEMANTIC_PRESELECTION` | When text exceeds its limit, ranks paragraphs by `_relevance` and drops the rest. In this run every raw material fit, so this branch behaved as identity transport for the nine source bodies. |
| `_technique_tags` | `SEMANTIC_PRESELECTION` | Maps query words to `ordinary_prose`, `low_rhetorical_density` and `knowledge_braid` for this case. |
| `_parse_technique_records` | `MECHANICAL_TRANSPORT` | Parses returned exemplar records. |
| `_read_relative` | `MECHANICAL_TRANSPORT` | Safely reads the selected exemplar path. |
| `_experience_section` | `SEMANTIC_PRESELECTION` | Scores human-review cases, discards zero-score candidates, and keeps only the highest-scoring case plus bounded excerpts. |
| `_technique_section` | `SEMANTIC_PRESELECTION` | Applies heuristic tags, falls back to an untagged retrieval when needed, and renders only the first three records. |
| `build_writer_context` | `SEMANTIC_PRESELECTION` | Composes the raw-material transport with the direct-match fact-boundary sentence and the selected experience/technique projections. |

### Semantic preselection details

`_relevance` (`writing_toolset.py:152-160`)

1. Host decision: lexical overlap is treated as semantic relevance; it also
   determines whether the desk pack says the query has a direct material match.
2. Model omission: in an over-budget paragraph or experience corpus, text with
   lower/zero overlap is not selected for the model’s first inspection.
3. WCASE-2 effect: it could hide a qualifying scene, a limiting condition, or a
   conflicting qualifier. In this run it did not remove any raw WCASE-2 body
   because all nine bodies fit their budgets.
4. Correctness basis: deterministic string matching, but only a heuristic
   relevance proxy; it is not deterministic proof of material importance.

`_bounded_excerpt` (`writing_toolset.py:163-181`)

1. Host decision: when a body is too large, which paragraphs deserve the
   bounded representation.
2. Model omission: paragraphs outside the selected lexical ranking, including
   potentially relevant negative evidence or scene detail.
3. WCASE-2 effect: yes in principle; omitted conflict qualifiers could change
   factual interpretation. The observed WCASE-2 raw-material path made no such
   omission: all nine bodies were below 1,222 characters.
4. Correctness basis: the limit is deterministic; the paragraph choice is
   heuristic lexical relevance, not a correctness guarantee.

`_technique_tags` (`writing_toolset.py:205-213`)

1. Host decision: this query is represented as ordinary prose, low rhetorical
   density and knowledge braid, rather than leaving technique discovery to the
   model.
2. Model omission: exemplar records that do not pass the requested tag filter
   are not available in the first request; the model cannot inspect their
   alternative technique affordances.
3. WCASE-2 effect: yes, because it can bias scene handling, factual density,
   transitions and endings before the model chooses a technique.
4. Correctness basis: fixed keyword heuristics; no deterministic correctness
   proof that these are the right tags for this assignment.

`_technique_section` (`writing_toolset.py:235-269`)

1. Host decision: which retrieval result set and which first three exemplar
   records become writing guidance.
2. Model omission: the fresh prompt exposed 3 of 18 active exemplar-index
   records; 15 were not inspectable by the model in that request.
3. WCASE-2 effect: yes for technique choice and narrative movement. It does
   not remove WCASE-2 factual source material, but it can influence how the
   model uses that material.
4. Correctness basis: ACE retrieval/index order plus a fixed cap; this is a
   bounded transport mechanism with heuristic semantic selection, not a proof
   of technique relevance.

`_experience_section` (`writing_toolset.py:272-308`)

1. Host decision: which past human review/revised pair is relevant enough to
   project into the current writing context.
2. Model omission: nonmatching cases are dropped, and only the highest-scoring
   matching case is shown. The current `learning/cases` directory contained
   one human-review candidate, so this run did not demonstrate a wrong winner
   among multiple cases.
3. WCASE-2 effect: yes for prose quality, human presence and revision
   interpretation; the projected review can become an implicit style prior.
4. Correctness basis: lexical score and path tie-break; heuristic relevance,
   not deterministic correctness.

`build_writer_context` (`writing_toolset.py:311-370`)

1. Host decision: it does not select/drop a raw WCASE-2 material in this run,
   but it does decide which direct-match warning, human-review projection and
   technique projection the model receives before it can ask a question.
2. Model omission: the raw-source omission was zero in this run; the omitted
   information is the unselected experience and exemplar candidate material.
3. WCASE-2 effect: source selection and conflict resolution remain model-visible
   here; technique choice and style guidance are partially host-shaped.
4. Correctness basis: raw enumeration is mechanical and bounded, while the
   additional projections are heuristic semantic selection.

## MATERIAL COVERAGE

The roles below come from the WCASE-2 fixture README, not from a host ranking.
`pull_context = YES` means the model-visible tool could retrieve the material
through the current ACE-backed path; it does not mean the model actually called
it in this run. The same bounded/heuristic projection would apply on that
route.

| material_id | source identity | available to Host | first request | Host selection/ranking mechanism | pull_context | relevant/conflicting evidence objectively inspectable |
|---|---|---|---|---|---|---|
| M001 | `brand-history.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Secondary brand origin, testing locations and slogan. |
| M002 | `conflicting-spec-draft.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Conflicting early figures: 420g/24h/600lm/599; explicitly superseded by M008. |
| M003 | `field-test-notes.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Core field scene, rain, overnight use, scratch, battery use and “not a handheld searchlight” limitation. |
| M004 | `interview-founder.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Core founder origin, 27 battery variants, 380g/30h design target and anti-glare account. |
| M005 | `office-lunch-menu.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Objectively unrelated meal names/prices; no product evidence. |
| M006 | `old-product-line.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Objectively unrelated 2006 kerosene-lamp history; explicitly unrelated to the 2026 LED product. |
| M007 | `pricing-channels.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Secondary current price, channels, launch discount and warranty detail. |
| M008 | `product-spec.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Formal v3 product facts; the objectively inspectable counterpart to M002’s conflict. |
| M009 | `staff-travel-log.md` | YES | full | enumerate all rows; bounded excerpt was identity | YES | Objectively unrelated travel diary and old road lamp. |

This table is the key WCASE-2 observation: the current Host did not hide the
irrelevant or conflicting raw materials. The model received the opportunity to
ignore M005/M006/M009 and compare M002 with M008 itself.

## SEMANTIC OWNERSHIP

The current trace separates two results:

- Raw material selection: preserved for this case. All 9 source bodies reached
  the model, including the irrelevant and conflicting candidates. The saved
  article’s observable choices—using M003/M004/M008 and M001/M007, omitting
  M005/M006/M009, and not repeating M002’s obsolete figures—are model-side
  selection/conflict behavior in this trace. This is not a human quality pass.
- Technique and experience selection: not fully preserved. The Host injected a
  lexically/tag-selected experience projection and only 3 of 18 active
  exemplar records. The model could choose how to use those examples, but it
  could not inspect the omitted candidates before making its technique choice.

## OBSERVED FAILURE

Selected exactly one:

```text
2. HOST_SEMANTIC_PRESELECTION_CAUSES_MEASURED_RISK
```

The measured evidence is the current first-request trace plus the current
implementation: all raw source material was transported, while the Host made
real semantic filtering decisions for experience and technique guidance.
That is a semantic-ownership breach/risk even though this run provides no
human quality gate showing a prose regression.

This is not classified as `CURRENT_WCASE2_RUNTIME_FAILURE_REPRODUCED`: the run
completed with 2 requests and 1 save call. The 43,704-token largest input and
268-second first request are baseline cost observations, not a separately
defined current-code failure with an accepted outcome improvement.

## CANDIDATE

No candidate A/B was run.

Candidate A—bounded representation of all candidate source materials—is already
the observed raw-material path: all nine WCASE-2 bodies reached the first
request in full. Re-running it under another label would not test a different
mechanism.

Candidate B would require a genuinely neutral index/pull path and would need to
isolate the supplementary experience/technique projection from transport. The
current baseline has no dependent `pull_context` round-trip failure, and
combining neutral retrieval with guidance changes would optimize multiple
mechanisms at once. CodeMode has no measured dependent-tool failure to address.

Therefore no production candidate was justified in this observation turn.

## COMPARISON

Not applicable: only the fresh current baseline was run. There is no candidate
quality, evidence, request, token, latency, coverage or ownership result to
compare, and the null human gates prohibit treating the baseline artifact as
an accepted outcome.

## CODE CHANGE JUSTIFIED? NO

No production code was changed. The current trace proves that source-material
transport is already broad enough for WCASE-2, while exposing a separate
semantic-preselection risk in supplementary context. There is not yet a
single-mechanism candidate result that pays for changing the production path
under G1/G2/G3/G12.

## DECISION

Close T006 as an observation/ownership proof and keep T003 frozen.

The current Host can reduce raw-material transport/tool round-trips to a
2-request / 1-tool execution without taking raw material selection or conflict
resolution away from the model in this case. It has not proved that the same
reduction is semantically neutral for technique and experience guidance: those
choices are partly preselected in `build_writer_context()`.

Do not remove `pull_context`, do not add a planner/router/capability, and do
not optimize the current production path from this null-gate observation.

## NEXT EXPERIMENT

T007 — Fresh WCASE-3 Unknown Proof. The WCASE-2 neutral-context A/B question,
if still needed, must be isolated as its own experiment rather than folded
into T006 or combined with a transport optimization.
