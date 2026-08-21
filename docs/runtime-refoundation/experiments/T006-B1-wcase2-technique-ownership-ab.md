# T006-B1 — WCASE-2 Technique Semantic-Ownership A/B

Status: execution, reverse-order variance check and blind quality review
complete; evidence subchecks are not fully adjudicated.

Date: 2026-08-21

## Hypothesis

Host-selected technique shards are not required to preserve WCASE-2 outcome
quality, and removing automatic technique selection restores model semantic
ownership without material runtime regression.

This is one causal hypothesis. Experience projection, raw-material transport,
model, thinking setting, prompt contract, task, tools and save semantics are
held constant.

## Run identity

Base commit: `945affc8453427b19fd2619cec6cddc6a90f37dc`.
The worktree was dirty for the experiment because the T006-B1 benchmark
switch and its candidate profile were uncommitted; the control default path
retains the pre-switch behavior.

| fact | control | candidate |
|---|---|---|
| commit/worktree | current worktree after T006-A; default behavior unchanged | same worktree; benchmark-only OFF profile |
| case / fixture | `WCASE-2` / `wcase-2-multi-material` | same |
| profile | `ace-writing` | `ace-writing-t006-b1-technique-off` |
| model | `deepseek/deepseek-v4-flash` | `deepseek/deepseek-v4-flash` |
| thinking | `openai_enable_thinking=null`; provider default | same |
| composition id | `fe34cf072ed64dedd38d76aba5da8e24605c48fcffb6f43a0273c9b00b48088f` | `4e2049581eb51b15266f7a99d1757c342dd4ba4a0c80bb0ca51f09778eaf94cf` |
| plugin | `ace-writing@0.2.0`, config `{}` | `ace-writing@0.2.0`, `include_technique_guidance=false` |
| run id | `wcase-2-multi-material` | `wcase-2-multi-material` |
| raw materials | 9/9 | 9/9 |

The composition id differs only because the candidate's frozen plugin config
records the experimental technique switch. The visible tool names remain
`pull_context` and `save_article`; generic capabilities remain disabled.

Fixture identity is the committed WCASE-2 manifest plus the nine raw files.
The runner records each source SHA-256 in both bundles; the aggregate fixture
hash is SHA-256 over the sorted `relative-path + space + file-sha256` lines
(with a trailing newline):

```text
fixture_sha256: ca83f46b82ad3dc85cfdbad45b8cbfa2e3fa91fa47c6d2f7cd00c781f8e21392
```

## Commands

Control:

```text
uv run python tools/run_writing_eval.py WCASE-2 --profile ace-writing \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-control
```

Candidate:

```text
uv run python tools/run_writing_eval.py WCASE-2 \
  --profile ace-writing-t006-b1-technique-off \
  --no-technique-guidance \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-technique-off
```

The `--no-technique-guidance` runner flag controls the initial desk pack. The
candidate profile carries the same setting into `pull_context`, so a model
observation call cannot silently reintroduce the host-selected technique
shards. Experience remains enabled in both profiles.

## Mechanical comparison

Both executions completed, but neither has an accepted quality or evidence
verdict. Values below are runtime facts, not quality judgments.

| metric | control | candidate |
|---|---:|---:|
| execution state | `completed` | `completed` |
| outcome evaluation | `null` / unjudged | `null` / unjudged |
| evidence evaluation | `null` / unjudged | `null` / unjudged |
| requests | 8 | 4 |
| tool calls | 7 | 3 |
| tool counts | `pull_context=1`, `save_article=6` | `pull_context=1`, `save_article=2` |
| input tokens | 93,387 | 29,591 |
| output tokens | 9,377 | 5,683 |
| reasoning tokens | 4,446 | 3,636 |
| cache-read tokens | 57,600 | 22,528 |
| largest input | 16,472 | 9,872 |
| wall clock | 198,575.356 ms | 119,244.722 ms |
| request latencies | 60,056.422; 22,017.835; 21,690.994; 16,606.481; 19,556.543; 19,647.064; 27,800.871; 10,593.072 ms | 57,383.603; 19,079.997; 25,539.721; 16,743.781 ms |
| `pull_context` latency | 443.331 ms | 398.062 ms |
| artifact chars | 1,225 | 1,214 |
| artifact sha256 | `64f8625ebf79c89bd4400470a8664c5f4197062f0821a0a3387ba6c32dcf5e38` | `0233b5b293e0fbaa6c640fd8d5ecd73ecb6fa43627d5f4673411b1e14ffc84da` |

The control and candidate traces have different model trajectories. In
particular, the control made six successful `save_article` calls while the
candidate made two. This is a measured difference, not evidence that the
candidate is better: outcome quality and evidence integrity are still
unknown. It also means a single A/B pair is not enough to generalize runtime
variance or to isolate all provider stochasticity.

The deterministic projection check before the model runs was:

| context projection | control | candidate |
|---|---:|---:|
| raw materials represented | 9/9 | 9/9 |
| experience section | present | present |
| technique section | present | absent |
| initial desk-pack chars | 5,052 | 4,126 |

## Reverse-order variance check

The first pair had a large runtime/trajectory difference (`ON=8/7` versus
`OFF=4/3`). That difference could not be attributed to the technique switch
because the earlier T006-A ON baseline was also only `2/1`. One reverse-order
pair was therefore run under the same fixture, model, thinking setting,
prompt contract, tool surface and save path:

```text
Candidate (technique OFF):
uv run python tools/run_writing_eval.py WCASE-2 \
  --profile ace-writing-t006-b1-technique-off \
  --no-technique-guidance \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-reverse-candidate

Control (technique ON):
uv run python tools/run_writing_eval.py WCASE-2 --profile ace-writing \
  --out workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-reverse-control
```

| metric | reverse candidate (OFF) | reverse control (ON) |
|---|---:|---:|
| execution state | `completed` | `completed` |
| outcome / evidence | `null` / `null` | `null` / `null` |
| requests | 2 | 2 |
| tool calls | 1 | 1 |
| tool sequence | `save_article` | `save_article` |
| input tokens | 8,156 | 10,896 |
| output tokens | 2,680 | 3,969 |
| reasoning tokens | 1,584 | 2,951 |
| largest input | 4,740 | 7,018 |
| wall clock | 66,045.186 ms | 89,034.352 ms |
| artifact chars | 1,281 | 1,219 |
| artifact sha256 | `10e1201cc4304fd18d846836d19495979fb7584d1dec15465b380386a7892b2e` | `7b6456c3df5dfe65382858b6c41db2e18eaf5e8c72db76f97451f80680432d29` |

Across both pairs, the actual tool sequences were:

| run | sequence |
|---|---|
| first control (ON) | `pull_context → save_article × 6` |
| first candidate (OFF) | `pull_context → save_article × 2` |
| reverse candidate (OFF) | `save_article` |
| reverse control (ON) | `save_article` |

The first-request identity was captured immediately after each reverse run,
before the next run reused the same `.zuaef-state` snapshot path:

| first request field | reverse candidate (OFF) | reverse control (ON) |
|---|---:|---:|
| snapshot | `snapshots/0.json` | `snapshots/0.json` |
| prompt sha256 | `95d3e69945ca1a5f52153bb1c2c47f1191e520a29dc3fef83cfd50cec398436b` | `b63cc5ab4ef5f3021f31026efbd661a8a323fad2ad8ded84a70756c85e66664a` |
| prompt chars | 4,537 | 5,463 |
| material ids | M001–M009 | M001–M009 |
| experience projection | present | present |
| technique projection | absent | present |

The two hashes and lengths differ in the expected controlled region: the ON
request contains the technique projection, while both requests contain the
same nine material ids and the same experience projection. The snapshot path
is reused by the runner, so the hashes above were recorded immediately rather
than reconstructed after both runs.

The reverse pair does **not** reproduce the first pair's ON-long/OFF-short
trajectory. The first control's six extra calls were repeated `save_article`
effects, not a stable extra `pull_context` pattern. The current evidence is
therefore a provider/model trajectory-variance signal, not a measured causal
runtime benefit of technique-off. Do not report the first pair as a 40%
speedup or use request/latency reduction as the B1 decision basis.

## Blind human quality gate

The anonymized copies were verified mechanically before recording the review:

```text
A.md sha256 = 64f8625ebf79c89bd4400470a8664c5f4197062f0821a0a3387ba6c32dcf5e38
B.md sha256 = 0233b5b293e0fbaa6c640fd8d5ecd73ecb6fa43627d5f4673411b1e14ffc84da
```

Those hashes map A to the first Control/ON artifact and B to the first
Candidate/OFF artifact. The supplied blind review selected **A clearly over
B**. Its scores were:

| dimension | A / Control ON | B / Candidate OFF |
|---|---:|---:|
| 阅读流畅度 | 8.3 | 6.6 |
| 人写感 / 去 AI 味 | 8.0 | 5.8 |
| 场景感 | 8.6 | 7.5 |
| 信息自然嵌入 | 8.2 | 6.4 |
| 节奏变化 | 8.3 | 5.9 |
| 克制程度 | 8.5 | 6.1 |
| 商业信息完整度 | 8.2 | 8.7 |
| “三联式”人文叙事潜力 | 8.1 | 6.0 |
| 综合 | 8.2 | 6.4 |

The review attributes the gap primarily to narrative control rather than
factual coverage. A lets actions, time and objects carry more of the scene;
B repeatedly completes the pattern `material → explanation → summary →
brand meaning`, including abstract closure after the concrete product facts
have already landed. The reviewer also identified residual generated-writing
signals in A, but still judged A the clearly preferable article.

Evidence interpretation is deliberately narrower than the quality result:
the review identified no material factual-quality regression and noted that
the two drafts used highly overlapping facts, but it did not separately mark
the M002-versus-M008 conflict field or irrelevant-material field pass/fail.
Those subchecks remain `unclear`; they are not silently converted to a full
evidence pass.

## Artifacts and blind review

Machine bundles:

- control: `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-control/`
- candidate: `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-technique-off/`

For blind pairwise review, use only the anonymized copies:

- `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-blind/A.md`
- `workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b1-blind/B.md`

The human reviewer must judge without using machine diagnostics as a quality
proxy. Record the result in
`T006-B1-human-judgment.md` for:

- overall sendability and article quality;
- factual fidelity and conflict resolution (especially M002 vs M008);
- use of core scenes/person material;
- omission of M005/M006/M009;
- scene preservation, structure and language;
- edits still required on the preferred version.

## Semantic ownership check

The candidate removes only the host-selected technique projection. It does
not change raw-material enumeration, material excerpts in this fixture,
experience projection, tool availability, model, prompt contract or save
behavior. The candidate therefore does not add a new host semantic decision;
it removes one.

## Decision

```text
CANDIDATE_QUALITY_REGRESSION / HOST_HEURISTIC_NOT_VALIDATED
```

The technique-off candidate is rejected for promotion because it materially
loses the target editorial outcome. The current ON path remains the
comparison baseline, but this result does **not** prove that Python's keyword
selector is the correct long-term semantic authority: it proves only that
removing the technique projection without replacing the missing writing
behavior is not acceptable.

The next experiment, still inside Phase 2, should test a model-owned way to
decide when technique knowledge is needed or to suppress premature abstraction
without adding a larger style-instruction list. Do not start T006-B2
experience selection or T007 until that observation design is specified and
the evidence subchecks are closed.

## Next smallest experiment

Complete the blind human A/B gate. If candidate is equal/better, remove the
automatic technique preselection. If candidate is worse, do not simply keep
the heuristic; identify the missing model-owned retrieval affordance. If the
review has no meaningful signal, prefer the simpler no-preselection path only
after the evidence/effect gate is explicitly recorded.
