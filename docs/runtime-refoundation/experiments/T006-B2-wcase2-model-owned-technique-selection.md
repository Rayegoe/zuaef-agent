# T006-B2 — WCASE-2 Model-Owned Technique Selection

Status: blind quality and evidence judgment recorded. The model-owned
Candidate was preferred over the Host-selected Control, but both drafts added
unsupported scene details and the Candidate reached the usage boundary after
producing an artifact. Verdict: `REFINE`; no promotion. Phase 2 remains open.

Date: 2026-08-21

## Hypothesis

Technique knowledge has business value, but the Host should not own the
semantic choice of which technique applies. A neutral catalog plus one
model-owned ID selection should preserve the Control's editorial outcome and
return technique selection authority to the model. Runtime is measured as a
secondary constraint; a quality gain may justify an additional semantic turn.

## Fixed variables and causal change

Both sides use the same WCASE-2 case, nine raw materials, fact boundary,
experience projection, model, thinking setting, task contract, ACE workspace,
save path and evidence rules. The production Control retains the current
Host-selected technique projection. The benchmark-only Candidate changes only
the technique selection seam:

```text
Control:  raw materials -> Host _technique_tags() -> 3/18 shards -> model
Candidate: raw materials + neutral 18-row catalog -> model selects 0–3 IDs
          -> one mechanical pull_techniques(ids) -> model writes
```

The Candidate catalog is read from the existing ACE index
`ACE_ROOT/corpus/exemplar_index.jsonl`. It contains existing metadata only:
ID, function, effect tags, use-when metadata, interpretation distance and
author-intrusion metadata. It does not contain technique bodies or a Host
generated summary. `pull_techniques` validates at most three IDs, preserves
request order, reads the exact indexed shards and applies only a prefix
character budget. It does not rank, score, tag, fallback or auto-select.

The selection contract is deliberately small: technique is optional, must have
a concrete use in the current material/task, and zero selected techniques is
valid.

## Run identity

Base commit: `c98504fb05c9dff350db49b2bc34e687b0ea7264`.
The worktree was dirty: the B2 seam/profile/tests and prior T006 records were
not committed, while the production profile default remained unchanged.

| fact | Control | Candidate |
|---|---|---|
| case / fixture | `WCASE-2` / `wcase-2-multi-material` | same |
| profile | `ace-writing` | `ace-writing-t006-b2-model-owned-techniques` |
| model | `deepseek/deepseek-v4-flash` | same |
| thinking | `openai_enable_thinking=null`; provider default, with reasoning tokens observed | same |
| composition id | `fe34cf072ed64dedd38d76aba5da8e24605c48fcffb6f43a0273c9b00b48088f` | `ef5a1d522c73382a876cf99b12aa27215e0d051a8a914b2668287bb147d93e66` |
| plugin | `ace-writing@0.2.0`, config `{}` | `ace-writing@0.2.0`, `technique_selection_mode=model` |
| run id | `wcase-2-multi-material` | `wcase-2-multi-material` |
| first-run conversation id | `b022b90f6e2149b68a6e3539a09c366f` | `2bd0127dd3474482b0833266a5146dfb` |
| raw materials | 9/9 | 9/9 |

Fixture identity is the committed WCASE-2 manifest plus its nine raw files.
`case.json` sha256 is
`119f966304e2577a38967fac53bc1dc9a052e005465635c2a5c7a0a6204dfc30`.
The aggregate fixture hash recorded for this manifest and raw-file set is
`ca83f46b82ad3dc85cfdbad45b8cbfa2e3fa91fa47c6d2f7cd00c781f8e21392`.
Per-file source hashes are preserved in each run's `bundle.json` and
`draft-record.json`.

## Commands

Control:

```text
uv run python tools/run_writing_eval.py WCASE-2 --profile ace-writing \
  --technique-selection-mode host \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-control
```

Candidate:

```text
uv run python tools/run_writing_eval.py WCASE-2 \
  --profile ace-writing-t006-b2-model-owned-techniques \
  --technique-selection-mode model \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-model-owned
```

The production profile was not edited or promoted.

## First-request projection identity

The first request was captured from the persisted snapshot before the next
run reused the same run-id state path. Both sides contained M001–M009 and the
same experience section.

| field | Control | Candidate |
|---|---:|---:|
| first prompt sha256 | `b63cc5ab4ef5f3021f31026efbd661a8a323fad2ad8ded84a70756c85e66664a` | `2c934760f322d148609309ff5798e108c1d4b4b1984e42d7860f3506ebccec15` |
| first prompt chars | 5,463 | 8,288 |
| materials | M001–M009 | M001–M009 |
| experience | present | present |
| technique bodies in first request | 3 Host-selected shards | none |
| neutral catalog | absent | 18 existing metadata rows |

The Candidate's extra first-request chars are the neutral catalog and its
small contract, not 18 technique bodies.

## Model-owned selection evidence

The Candidate made one successful `pull_techniques` call with exactly these
IDs, in this order:

```text
ex-scene-pause-001
ex-prose-object-001
ex-final-quote-001
```

This is different from the Control's Host-selected IDs:

```text
ex-prose-object-001
ex-uncertainty-unverified-001
ex-ending-number-001
```

The Candidate therefore exercised an actual model-owned selection rather than
merely receiving the Control's three shards under a new label. The tool event
record shows one `pull_techniques` effect; subsequent repeated effects were
`save_article`, not repeated semantic retrieval.

## Mechanical run comparison

These are runtime facts, not quality or evidence judgments.

| metric | Control | Candidate |
|---|---:|---:|
| execution state | `completed` | `limit_reached` |
| outcome evaluation | comparative loss; not accepted | comparative preference; not accepted end-to-end |
| evidence evaluation | fail | fail |
| model requests | 2 | 12 |
| tool calls | 1 | 12 |
| tool sequence | `save_article` | `pull_techniques → save_article × 11` |
| input tokens | 12,141 | 175,569 |
| output tokens | 4,950 | 18,424 |
| reasoning tokens | 3,886 | 9,490 |
| cache-read tokens | 0 | 85,760 |
| wall clock | 113,050.284 ms | 399,771.416 ms |
| artifact chars | 1,211 | 1,179 |
| artifact sha256 | `0b590cac84ce8b4b1c91e1972eca4ba770a4e5bfcac64569d86ba17eb4d3f31a` | `0f899f13e64734a4a41e56aa516d5b3ad9cb8433cb6e0624a2866f1b2fc47704` |

The Candidate produced a final artifact, but the agent did not return a
natural terminal response before the Harness usage boundary. The repeated
`save_article` trajectory is an observed runtime failure/unknown, not a
quality verdict and not evidence that model-owned selection is intrinsically
slow. Do not report this as a stable latency ratio without another justified
experiment.

## Blind quality and evidence gate

Use only the anonymous copies for review:

- `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-blind/A.md`
- `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-blind/B.md`

The review was recorded before revealing the anonymous mapping. The mapping
was then mechanically resolved as:

```text
A = model-owned Candidate
B = Host-selected Control
```

The reviewer preferred **A**. It kept the core person, formal v3
specification, Siguniang Mountain test and commercial information
substantially faithful to the materials. It correctly used 380 g, 30 hours,
800 lumens and RMB 699 rather than the obsolete M002 figures. It did not
wrongly mix M005/M006/M009 into product facts.

The no-outside-facts check failed. Control/B invented several concrete scene
facts: light landing on a teammate's face followed by mumbling and turning
over, needing to bring the watch close to the eyes after dimming it, and
sub-zero wind outside the tent. Candidate/A was steadier but still lightly
expanded the scene with a cold tent and white light that could not warm it.
The supplied interview established 4 a.m., a dark tent, searching for a
flashlight and the "hot / bright" motivation, but not those added details.

The narrow gate is therefore:

| check | result |
|---|---|
| M002 obsolete figures not treated as current | pass |
| M008 formal v3 specification prioritized | pass |
| M005/M006/M009 not mixed into product facts | pass |
| no facts outside supplied materials | fail |

The Candidate wins the comparative editorial judgment and is less severe in
its unsupported expansion, but this is not an accepted evidence outcome.
Runtime completion also remains part of the result: Candidate ended
`limit_reached` after 12 requests / 12 tool calls and repeated
`save_article` submissions.

## Decision status

```text
T006-A   COMPLETE
T006-B1  COMPLETE (quality verdict recorded; evidence subchecks unclear)
T006-B2  COMPLETE (CANDIDATE PREFERRED / EVIDENCE FAIL / LIMIT_REACHED)
Phase 2  OPEN
T007     DEFERRED
```

Decision: `REFINE`.

The result rejects both simple conclusions. It does not support removing
technique knowledge entirely: T006-B1's technique-off draft regressed. It
also does not admit this model-owned implementation: its preferred prose
still failed the evidence gate and its run did not terminate normally. The
Host keyword selector remains an unvalidated provisional baseline rather
than final semantic authority.

This single pair does not show that model ownership increases unsupported
scene completion relative to the Host selector: Control/B added more severe
unsupported details than Candidate/A. The narrower reproduced fact is that
the preferred model-owned artifact still failed the evidence boundary. A
model-ownership-specific factual-boundary failure remains a hypothesis for
the real-corpus comparison, not a settled causal claim.

The next writing experiment should use current `main`, one fixed real task
and the same real EPUB corpus across Host-selected, technique-off and
model-owned inputs. Record actual per-section characters and whether the
final desk-pack tail truncation removed any section. Do not change EPUB
ingestion, corpus schema or retrieval. Do not pre-fix Candidate evidence or
add Host technique/scene/schema judgment before the comparison; either would
change the causal question. If the model-owned variant again wins on prose
while failing factual boundaries, that second independent observation may
justify a separate experiment in model-owned composition plus deterministic
factual boundary control. Do not start T007 before this current-path evidence
converges.
