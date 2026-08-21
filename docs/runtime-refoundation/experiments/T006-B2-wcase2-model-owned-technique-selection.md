# T006-B2 — WCASE-2 Model-Owned Technique Selection

Status: execution recorded; candidate reached the usage boundary after
producing an artifact; blind quality and narrow evidence review are pending.
Phase 2 remains open. This run does not promote the candidate or start T007.

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
| outcome evaluation | `null` / unjudged | `null` / unjudged |
| evidence evaluation | `null` / unjudged | `null` / unjudged |
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

The reviewer must not use profile names, tool counts, selected IDs or runtime
facts as a quality proxy. Record the result in
`T006-B2-human-judgment.md`:

```text
Overall: A / B / Tie
Evidence:
- M002 obsolete figures were not treated as current facts: pass / fail / unclear
- M008 formal spec was prioritized: pass / fail / unclear
- M005/M006/M009 were not wrongly mixed into product facts: pass / fail / unclear
- no facts outside the supplied materials: pass / fail / unclear
Why:
```

No promotion decision is valid until both the overall blind result and the
narrow evidence fields are recorded. Runtime completion is also part of the
Candidate's observed outcome and must not be silently omitted.

## Decision status

```text
T006-A   COMPLETE
T006-B1  COMPLETE (quality verdict recorded; evidence subchecks unclear)
T006-B2  EXECUTION RECORDED / HUMAN VERDICT PENDING
Phase 2  OPEN
T007     DEFERRED
```

The only admissible next step is the human blind/evidence review of this
artifact pair. Depending on that result, the next architecture decision is:

- model-owned quality/evidence equal or better: remove Host semantic
  preselection and retain the neutral catalog/retrieval seam;
- model-owned quality clearly worse: keep the current path as a provisional
  baseline and investigate which prior or selection affordance is missing;
- evidence failure: fix observation correctness before interpreting prose
  quality;
- runtime worse with quality better: do not reject solely on the extra
  semantic turn;
- runtime better with quality worse: reject the trade.

No experience-selection experiment, thinking A/B or T007 is started by this
record.
