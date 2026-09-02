# T006-B6 — OFF baseline stability check (observation)

Status: COMPLETE — verdict `B: NO_STABLE_SEMANTIC_FAILURE_MECHANISM`.
Under identical fixed OFF conditions, eight protocol-strict OFF runs produced
only three scattered minor evidence failures (5/8 clean); no predeclared family
reproduces in a clear majority; logical-strength and responsibility families
flagged in B3/B4 do NOT recur in any fresh run. Stochastic synthesis variance
remains material. Evidence returned to Supervisor. NO next engineering
intervention chosen (STOP per approval).

Date: 2026-08-24
Baseline: `1b0e46bbf5e67de00a194c3e5b68638b230434f7` (current code, unchanged)

## Purpose

Determine whether the evidence-preservation failures seen across T006-B3/B4
are stable properties of the REAL-AGENT-TRUST-1 OFF trajectory, or dominated by
ordinary stochastic synthesis variance. Observation only — no implementation,
no tuning after intermediate outputs.

## Frozen identity (all five runs identical)

| fact | value |
| --- | --- |
| case | `REAL-AGENT-TRUST-1` |
| profile / technique | `ace-writing-t006-b1-technique-off`, `--no-technique-guidance` (OFF) |
| model | `deepseek/deepseek-v4-flash-0731` via OpenRouter |
| request / tool budget | `12 / 40`, total-token unset |
| prompt / instructions | unchanged; NO synthesis-boundary instruction (`observation_controls.synthesis_boundary_instruction = False` for all 5) |
| tools / retrieval | `pull_context`, `save_article`; retrieval available and unused except control-4 (one `pull_context`) |
| evidence desk pack | byte-identical to B5: 14,733 chars, sha `d9620a987ffe` (all five runs) |
| first-request prompt | 15,300 chars, no boundary rule, all five runs |
| code | zero changes in this iteration |

## Runs (5 fresh independent OFF-control runs)

| run | status | requests | tools | chars | note |
| --- | --- | --- | --- | --- | --- |
| control-1 | completed | 4 | save_article | 2,029 | |
| control-2 | completed | 2 | save_article | 2,178 | |
| control-3 | completed | 10 | save_article | 2,176 | |
| control-4 | completed | 5 | pull_context, save_article | 2,308 | one retrieval on `企业微信 AI开放能力 字节 飞书 豆包 委托式办公` (returned 12,390-char pack) |
| control-5 | completed | 2 | save_article | 2,604 | |

All five first-request prompts are byte-identical: 15,300 chars, desk pack sha
`d9620a987ffe`, boundary rule absent (verified from persisted run snapshots;
per-run `context/` preserved).

## Adjudication (same five classes as B5; rubric identical)

Same class definitions as T006-B5 rubric: 1 attribution/source-role,
2 claim scope, 3 logical-strength, 4 responsibility subject, 5 unsupported
concrete detail. Blind record: `.../t006-b6/blind-b6/REVIEW.md`. Mapping:
`A=control-1, B=control-2, C=control-4, D=control-3, E=control-5`.

| artifact (run) | c1 | c2 | c3 | c4 | c5 | counted |
| --- | --- | --- | --- | --- | --- | --- |
| A (control-1) | 0 | 0 | 0 | 0 | 0 | 0 |
| B (control-2) | 0 | 0 | 0 | 0 | 1 | 1 minor |
| C (control-4) | 0 | 0 | 0 | 0 | 0 | 0 |
| D (control-3) | 0 | 0 | 0 | 0 | 0 | 0 |
| E (control-5) | 0 | 0 | 0 | 0 | 0 | 0 |

The single counted failure: B `企业已经用了几十年工作流、RPA和自动化平台` vs
desk pack M005 `…使用工作流、RPA和自动化平台多年` — class-5 temporal-figure
drift (minor). Borderline observations recorded but not counted: first-person
voice echo of M001's plugin-deep-dive (B/C/D, genre re-telling), harness-
qualifier vagueness in D's 50%-failure restatement (`在当前可执行的框架下`),
attribution looseness in B's `用评测原话讲`.

Business quality guard: PASS for all five — each remains an article with an
argument, viewpoint and progression; none is an evidence audit report.

## Stability across the OFF trajectory (all available OFF samples)

Strict five-class protocol runs (8 total): B5-control-1 (c2 benchmark-scope
minor), B5-control-2 (c5 figure 10→5 min minor), B5-control-3 (0), B6-control-1
(0), B6-control-2 (c5 duration 多年→几十年 minor), B6-control-3 (0, border c2),
B6-control-4 (0), B6-control-5 (0).

Human-judgment OFF samples (2 total, different protocol): B3-Z flagged
over-strong necessity language (`any layer`/`cannot`) + responsibility
ambiguity; B4-Q flagged benchmark generalization + strengthening jointly-
influencing layers into individually necessary conditions + blurring traceable
execution with organizational responsibility.

| failure family | strict 5-class OFF (8 runs) | human OFF (B3-Z, B4-Q) |
| --- | --- | --- |
| c2 benchmark-scope generalization | 1 counted + 1 borderline | B4-Q |
| c5 concrete-detail / figure drift | 2 (10→5 min; 多年→几十年) | not assessed this way |
| c3 logical-strength / necessity amp. | 0 in all 8 | B3-Z, B4-Q |
| c4 responsibility-subject blur | 0 in all 8 | B3-Z, B4-Q |
| c1 attribution / source-role | 0 counted (voice-echo borderlines) | — |

## Primary question

> Do the same proposition-level failure families reproduce consistently across
> fresh OFF runs?

**No.** Interpreting the three-branch rule:

- **A (stable narrow family in clear majority): not supported.** The most-
  recurring strict family (c5 detail drift) appears in 2/8 runs (25%). No
  family reaches a majority.
- **B (failures vary in type and occurrence; stochastic variance material):
  best fit.** Per-run counts vary 0–1 minor (5/8 clean), and type varies
  (c2 in one run, c5 in another, c1 style notes). The two families that most
  motivated the B3/B4 concern — necessity/logical-strength amplification and
  responsibility-subject blur — reproduce in ZERO of the eight fresh
  protocol-strict runs.
- **C (isolate one narrow stable failure): partial only.** c5 concrete-detail
  drift is the only family with any recurrence (25%), but with different
  content each time (10→5 min; 多年→几十年), i.e. a diffuse figure/duration
  dysfluency, not the same narrow proposition or boundary recurring. That does
  not meet C's "one narrow stable failure" bar.

Verdict: **B.** Current evidence does not support treating one specific
semantic failure mechanism as stable on the OFF trajectory; stochastic
synthesis variance remains material. Base rate observed: ~1 minor evidence
failure per ~2.7 OFF runs, of varying family, with no family in a clear
majority.

## Incidental observation (n=1, not an experiment)

The single run that called `pull_context` (control-4, on the 企业微信/字节/委托
section) produced the most exact M004 fidelity in the batch (WorkBuddy, MiniMax
Code, Kimi Work, Codex list all correct). Retrieval-supporting the contended
section correlated with cleaner attribution in this one sample. Reported for
context only; not actionable under this approval's no-next-step rule.

## Consistency with prior iterations

- Supports T006-B5's `WEAKEN_PRIMARY_HYPOTHESIS`: if the failures are mostly
  stochastic rather than a stable compression tendency, a single appended
  instruction cannot be expected to yield a material reproducible reduction —
  consistent with B5's null result.
- Cautions the Supervisor: the specific qualifier-failure families that the
  B3 full-desk-pack adjudication reproduced (necessity language, benchmark
  scope, responsibility blur) are intermittent, not steady-state properties of
  the OFF writer under identical fixed conditions.

## Artifacts

- `workspace/artifacts/writing-v0.2/eval/REAL-AGENT-TRUST-1/t006-b6/{control-1..5}/` — bundles, drafts, records, `context/` (first prompts, full conversations; control-4 also `pull-context-result.md`)
- `.../t006-b6/blind-b6/` — rubric (reused), artifacts A–E, mapping, REVIEW.md
- This report.

## Result block

```text
NO_STABLE_SEMANTIC_FAILURE_MECHANISM_ON_OFF
STOCHASTIC_SYNTHESIS_VARIANCE_MATERIAL
FAMILIES_VARY_IN_TYPE_AND_OCCURRENCE
NO_FAMILY_IN_CLEAR_MAJORITY
B3_B4_LOGICAL_AND_RESPONSIBILITY_FAMILIES_NOT_REPRODUCED (0/8 strict runs)
QUALITY_GUARD_PASS (5/5 articles)
ZERO_CODE_CHANGE
STOP_AFTER_OBSERVATION
```
