# T005 — WCASE-1 surface admission proof

Decision: `NO_REMOVAL_JUSTIFIED`

This is an admission review only. T005 changes no production runtime, Agent
composition, prompt, capability setting, writing tool, or model
configuration.

## Target profile/task class

- Profile: `ace-writing`
- Case: WCASE-1 single-source article
- Current run: 2 model requests, 1 tool call (`save_article`)
- Generic capabilities: OFF in the writing profile

## Reproduced failure without each surface

None.

The fresh T003/T004 trajectory completed with an accepted article and an
explicit evidence gate. It did not show plan/status choreography, repeated
observation, claim-check loops, history reconstruction, missing-source
failure, or output degradation attributable to any remaining surface.

## Current model-visible surface

The production toolset is defined in
`plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py`:

| Surface | Current role | WCASE-1 observation | Admission result |
|---|---|---|---|
| `pull_context(query)` | Semantic observation when the desk pack leaves one concrete question unanswered | Exposed; called 0 times | Keep; no failure caused by exposure |
| `save_article(markdown)` | Artifact submission of the model-selected local deliverable | Called once; settled successfully | Keep; model owns payload and timing |
| Writer instructions | Model-facing domain guidance and boundaries | Present in the writing toolset | Keep; no competing generic capability |
| `code_mode=true` metadata on `pull_context` | Transport/tool metadata on the optional observation tool | No call, therefore no measured CodeMode benefit or harm | No change justified |

The exact current definitions are visible at `build_writing_toolset()`
(lines 403–429); `save_article_impl()` persists the submitted artifact
(lines 373–386). The code graph and T003 receipt both show the two-tool
surface. `pull_context` being unused is a surface fact, not a demonstrated
failure.

## Generic capability review

Planning, Skills, FileSystem, Knowledge, ToolOutputLimits and the generalist
surface are already OFF in the writing profile. They are not removed in T005:
there is no remaining WCASE-1 evidence that their current absence fails the
task, and no exposed generic capability is causing the observed trajectory.

Step persistence/receipts remain operational execution evidence, not a
model-visible writing capability. T005 does not alter their authority.

## Runtime cost

| Metric | WCASE-1 value |
|---|---:|
| requests | 2 |
| tool calls | 1 |
| tool counts | `{"save_article": 1}` |
| input tokens | 20,295 |
| output tokens | 14,562 |
| reasoning tokens | 13,680 |
| largest input | 17,342 |
| wall clock | 128,204.782 ms |

The definition/instruction token cost of the unused `pull_context` surface is
not isolated in the provider record. No causal exposure penalty is therefore
claimed or invented.

## Alternatives considered

- Remove `pull_context`: rejected because the tool gives the model a bounded,
  model-timed semantic observation path when the initial desk pack leaves a
  concrete question unanswered.
- Automatically call or host-select `pull_context`: rejected because query
  choice and timing are semantic and must remain model-owned.
- Remove or auto-trigger `save_article`: rejected because the model selects
  the complete Markdown payload and decides when it is ready for submission;
  changing that would alter artifact-submission semantics.
- Remove generic capabilities: no current writing-profile surface to remove;
  they are already OFF.

## A/B result

No A/B removal experiment is justified by this case. The control already has
an accepted outcome, and no candidate failure was reproduced. This is a
zero-code admission verdict, not a claim that the surfaces are universally
necessary for every writing task.

## Admission scope

Keep `pull_context` and `save_article` in the `ace-writing` profile. Their
continued presence is conditional on the model retaining semantic authority
over observation timing/query and artifact payload/submission timing.

## Withdrawal condition

Re-open admission only after a fresh trace demonstrates one of:

- the exposed surface causes measurable context/selection/output degradation;
- a narrower deterministic or upstream primitive preserves the same outcome
  while removing the surface's model-boundary burden;
- a profile-level task contract no longer needs the corresponding semantic
  decision.

## Final decision

`NO_REMOVAL_JUSTIFIED`.

Stop after T005. WCASE-2 host-preselection audit and A/B observation designs
are T006 work and are intentionally not started here.
