# T003 — WCASE-1 current baseline

Status: `BASELINE_FROZEN`

This is a diagnostic record only. T003 changed no production source, Agent
composition, prompt, capability setting, writing tool, or revision behavior.

## Run identity

- Commit: `62fb9f7ee48e4a3b15ac1730243801c37d8351ad`
- Case: `WCASE-1`
- Run id: `wcase-1-single-source`
- Profile: `ace-writing`
- Composition id: `fe34cf072ed64dedd38d76aba5da8e24605c48fcffb6f43a0273c9b00b48088f`
- Loaded plugin: `ace-writing@0.2.0`
- Provider/model observed in snapshots: `deepseek` / `deepseek-v4-flash`
- Logical settings observed by the runner: `openai:gpt-5.2` with
  `compat_model=deepseek-v4-flash`, request limit `12`
- Material count: `1` (`M001`, `interview-and-product-notes.md`)

The worktree was already dirty before T003. The commit above identifies the
code snapshot used by the run; it is not a claim that the worktree was clean.

## Baseline metrics

| Metric | Observed value |
|---|---:|
| execution state | `completed` |
| outcome | `Returned the result to the current user.` |
| outcome evaluation | `null` — no human quality verdict recorded |
| evidence evaluation | `null` — no formal evidence verdict recorded |
| requests | `2` |
| tool calls | `1` |
| input tokens | `20,295` |
| output tokens | `14,562` |
| reasoning tokens | `13,680` |
| cache-read tokens | `3,200` |
| cache-miss tokens | `17,095` |
| wall clock | `128,204.782 ms` |
| largest request input | `17,342 tokens` |
| request latencies | `[123,624.836, 4,471.917] ms` |
| tool counts | `{"save_article": 1}` |

The artifact was created at `artifacts/wcase-1-single-source/final.md`; the
receipt recorded a completed `save_article` effect, no unresolved effects, and
sha256 `9c00c3c736f187cdd22a8e6ea8d908506664ae744a1a4f92a7861ce12b970cda`.
The tool result reported 923 characters; the persisted record reads 924
characters including its trailing newline.

## Model-request anatomy

Only observable messages, tool calls/results, provider usage, and Harness
timestamps are used here. Provider reasoning content is not interpreted.

### Request 1

- Runtime: `04:56:18.312280Z` → `04:58:21.937116Z`
- Provider usage: input `2,953`, output `14,312`, reasoning `13,657`,
  cache-read `256`
- State before request: a fresh run with the one host-ingested material and a
  bounded desk pack already in the prompt. No earlier model observation or
  tool result existed.
- Observable semantic decision: emit the complete article and call
  `save_article` with the selected Markdown payload.
- Justification: the initial assignment, constraints, and source material were
  new semantic input; the model had to choose content, framing, factual
  restraint, and the final artifact.

### Request 2

- Runtime: `04:58:21.964592Z` → `04:58:26.436509Z`
- Provider usage: input `17,342`, output `250`, reasoning `23`, cache-read
  `2,944`
- State change since request 1: `save_article` returned success with the
  artifact path, character count, and sha256.
- Observable semantic decision: return a completion/presentation message and
  take no further action.
- Justification: the model received a new mechanical success result, but no
  new business or source information. This continuation is protocol/control
  work rather than a new content decision.

The second request's input grew from `2,953` to `17,342` tokens after the first
response, tool arguments, and tool result were appended to the transcript.

## Tool-call anatomy

| Position | Tool | Classification | New information/state | Model judgment required | Equivalent earlier observation |
|---:|---|---|---|---|---|
| 1 | `save_article` | `EXTERNAL_ACTION` | Persisted the model-selected article and returned path, length, and sha256. | Yes: the model selected the complete Markdown and chose when to submit it. | No earlier save or equivalent artifact existed. |

`pull_context` was model-visible but was not called. The initial host desk pack
already contained the single bound material, so no model-visible material
observation call occurred.

## Model-visible surface

The receipt composition snapshot recorded:

- plugin `ace-writing@0.2.0` only;
- `capabilities_allowed=false`;
- `defer_tools=false`;
- `generalist=null`;
- no recorded deferred capability catalog.

The effective current production writing settings had Planning and Skills
disabled, along with the other generic capabilities disabled by the existing
`composition_settings` seam. T003 did not change those settings.

The ACE writing toolset exposed exactly two tools:

- `pull_context(query)`: search bound sources for one remaining semantic need;
- `save_article(markdown)`: persist the complete article.

Relevant toolset instructions told the model that the host provides a bounded
desk pack, that the model owns meaning/selection/viewpoint/factual restraint,
that `pull_context` should be used only for a concrete unanswered question,
and that the completed article must be submitted with `save_article`.
The prompt also supplied the assignment, audience, constraints, one material,
fact-boundary guidance, and host-projected learning/example context.

## Runtime smells

### Observed

- **Process-for-process / presentation turn:** request 2 followed a successful
  artifact write and added no new business evidence; it only produced the
  completion response.
- **Context snowball:** provider input grew from `2,953` tokens on request 1 to
  `17,342` on request 2. The transcript carried the first response's large
  output, the 975-character tool arguments, and the tool result into the
  second request.
- **Unused optional surface:** `pull_context` was exposed but unused because
  the host had already projected the only material. This is a surface fact,
  not yet a causal removal decision.

### Not observed in this trajectory

- repeated observation;
- retry without information;
- validation chatter (`check_claim` was not called);
- history-search/reconstruction calls;
- generic capability gravity in the model-visible surface;
- dual authority or benchmark overfit.

`save_article` is not classified as mechanical transport: its payload is the
semantic artifact chosen by the model, so the external action remains
model-owned in this baseline.

## Raw and normalized records

- Raw bundle: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/bundle.json`
- Raw pass record: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/draft-record.json`
- Normalized baseline: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/draft-normalized.json`
- Artifact: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/draft.md`
- Harness events: `.zuaef-state/steps/wcase-1-single-source/events.jsonl`
- Receipt: `.zuaef-state/receipts/wcase-1-single-source.json`

The normalizer's raw pass record does not carry the model-visible tool list, so
the normalized baseline's top-level `model_visible_tools` was filled from the
observed composition/toolset surface (`pull_context`, `save_article`). The raw
usage and effect facts were not rewritten.

## Unknowns

- No human outcome/evidence verdict was recorded for this fresh run.
- Tool arguments are not retained as normalized signature data, so repeated
  semantic signatures cannot be computed.
- The acceptance of the generated prose itself is not inferred from
  `execution_state=completed`.

## Verification

- Fresh current-path run: completed with the raw bundle emitted.
- Normalizer tests: `8 passed`.
- Current profile/composition checks: `2 passed`.
- Normalized-record consistency assertion: passed.
- `git diff --check`: passed.

## Decision

`KEEP_CHANGE` is not applicable: T003 made no optimization change. This record
freezes the current trajectory for T004 comparison.

## Next task

T004 — Minimal WCASE-1 path.
