# T004 — WCASE-1 minimality & outcome proof

Initial decision before the human outcome gate: `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`

Final T004 decision after T004G: `CURRENT_PATH_ALREADY_MINIMAL`

This is a proof record only. T004 changes no production runtime, Agent
composition, prompt, capability setting, writing tool, or model configuration.

## OUTCOME STATUS

Authoritative benchmark run:

- Commit: `62fb9f7ee48e4a3b15ac1730243801c37d8351ad`
- Case/run: `WCASE-1` / `wcase-1-single-source`
- Raw record: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/draft-record.json`
- Normalized record: `workspace/artifacts/writing-v0.2/eval/WCASE-1/t003-current/draft-normalized.json`
- Artifact: `workspace/artifacts/wcase-1-single-source/final.md`
- Source/material: `benchmarks/writing-cases/WCASE-1/raw/interview-and-product-notes.md`
- Material id: `M001`; rights: `study-only`

Task contract:

- Assignment: 根据客户提供的素材写一篇面向普通消费者的公众号文章。
- Audience: 普通消费者
- Constraints: 约 900–1200 字；不虚构采访现场；产品事实必须来自原始材料；不编造用户评价。

Artifact facts:

- Execution state: `completed`.
- Persisted article length: 924 characters including the trailing newline;
  the tool result reported 923 characters after trimming.
- `save_article` completed once; no unresolved effects remained.
- Receipt/artifact sha256: `9c00c3c736f187cdd22a8e6ea8d908506664ae744a1a4f92a7861ce12b970cda`.
- Source sha256: `6cf28e7a551a7b6ac63369adc157642830ea66e68a5880a07ccc08a306d02611`.

Integrity distinction:

- Operational/effect integrity: mechanically verified by the receipt, artifact
  fact and settled `save_article` effect.
- Article outcome quality at initial capture: `UNVERIFIED`.
- Article factual/evidence quality at initial capture: `UNVERIFIED`.

At initial capture, the normalized record had `outcome_pass: null` and
`evidence_pass: null`, and the WCASE-1 human judgment was still
`PENDING-HUMAN`. Execution success, artifact existence and a source hash are
not by themselves a prose-quality or claim-level evidence verdict. The
human-gated result is recorded in the closure addendum below; the initial
unknown is retained here as part of the original observation.

## CURRENT MINIMAL LOOP

```text
host task + bounded desk pack
  → Request 1: write article and call save_article(markdown)
  → save_article result: path, character count, sha256
  → Request 2: return completion/presentation text
  → completed receipt
```

Frozen T003 measurements:

| Metric | Value |
|---|---:|
| model requests | 2 |
| tool calls | 1 |
| tool counts | `save_article: 1` |
| input tokens | 20,295 |
| output tokens | 14,562 |
| reasoning tokens | 13,680 |
| wall clock | 128,204.782 ms |
| largest request input | 17,342 tokens |
| request latencies | 123,624.836 ms; 4,471.917 ms |
| repeated observations | none observed |

### Request 1 — semantic construction and settlement action

Request 1 received the assignment, audience, constraints, bounded desk pack and
the source material as new semantic input. The model selected facts, framing,
structure, factual restraint, language and the complete Markdown payload. It
then chose when to submit that payload through `save_article`.

This request is necessary for the current task: those choices are editorial
semantics and must remain model-owned. `save_article` is an artifact
submission (local deliverable persistence) whose payload is the
model-selected artifact, not mechanical receipt writing.

### Request 2 — protocol/presentation continuation

After `save_article` returned success, Request 2 received the saved path,
character count and sha256. No new source fact, human delta, validation failure
or changed business state arrived. The observed output only completed the
conversation and presented the result.

Classification: `PRESENTATION` / protocol control, not a new semantic decision.

## REQUEST 2 PROTOCOL ANALYSIS

The current path uses `save_article` as a normal PydanticAI function tool. In
PydanticAI 2.2.0, a successful function-tool result is appended to the model
history and the agent continues until it receives a final model output. This
explains the second request in the observed trajectory.

The upstream `end_strategy="early"` mechanism is not a drop-in solution here:
its documented scope is successful output tools, whereas `save_article` is a
normal function tool in the ACE toolset. Turning `save_article` into an output
tool would change the output schema, composition contract and receipt/settlement
path. Its benefit and outcome safety have not been measured.

No safe native mechanism was found that terminates this current function-tool
run immediately after `save_article` succeeds. A host-side early exit or a
custom terminal protocol would duplicate or move Harness semantics and is
outside this experiment.

## PULL_CONTEXT ADMISSION ANALYSIS

Observable model-visible definition in the current ACE writing toolset:

- Tool name: `pull_context`
- Description: 67 characters
- Parameter schema: 108 compact JSON characters; one required string parameter,
  `query`
- Metadata: `code_mode: true`
- Toolset writer instructions: 671 characters
- Exact provider token cost of each definition is unavailable; Request 1's
  total provider input was 2,953 tokens.

The tool exists for a semantic observation need: the model may ask for a
bounded source-context projection when the desk pack leaves a concrete question
unanswered. The timing and query depend on editorial interpretation, so the
host must not call it automatically or select its query.

WCASE-1 did not call `pull_context`. The desk pack already contained the one
bound material, and no failure, repeated retrieval, missing-fact loop or
context-selection error was observed. Its presence is therefore an admitted
profile surface, not a demonstrated WCASE-1 failure. Unused is not by itself a
removal reason; no dynamic task-specific routing is justified by this run.

## DOMINANT COST

Request 1 dominates the run:

- Latency: 123,624.836 ms, approximately 96.4% of the 128,204.782 ms wall
  clock.
- Provider usage: 2,953 input tokens, 14,312 output tokens and 13,657
  reasoning tokens.
- The persisted initial request contains a 3,901-character user prompt and a
  1,948-character instruction field; exact per-component token attribution is
  unavailable.

Request 2 is cheaper in time but exhibits context growth:

- 4,471.917 ms latency;
- 17,342 input tokens, 250 output tokens and 23 reasoning tokens;
- input grew from 2,953 to 17,342 tokens after the first response, tool
  arguments and tool result entered the transcript.

These are mechanical observations only. T004 does not change the model,
reasoning settings, prompt, context composition or output protocol.

## MEASURED FAILURE

No accepted business-outcome or factual/evidence failure was established in
the run. At initial capture, the human outcome/evidence gate was still
unknown.

Measured runtime smells:

1. Request 2 is a protocol/presentation turn with no new business evidence.
2. The transcript causes Request 2's input to grow to 17,342 tokens despite a
   250-token response and 23 reasoning tokens.

At initial capture, neither smell was sufficient to justify a production
change: eliminating Request 2 would require a new output/settlement contract
or a non-native terminal path. The later human gate confirms that the current
accepted outcome does not pay for that change.

## CODE CHANGE JUSTIFIED? YES/NO

`NO`.

The current trajectory is already a credible minimal candidate. The human
outcome/evidence gate is now resolved below, so no production runtime change
is justified by this experiment.

## DECISION

Initial pre-gate decision: `OUTCOME_UNVERIFIED_BLOCKS_OPTIMIZATION`

This decision does not claim that two requests are theoretically optimal. It
records that the current path is already small, the only observed excess turn
has a native protocol explanation, and the missing outcome verdict prevents a
responsible optimization experiment.

## NEXT EXPERIMENT

Human outcome/evidence adjudication of the exact T003 artifact against the
WCASE-1 source and constraints, with no runtime change. This was the pending
gate at record creation and is closed by the addendum below.

## T004G — Human outcome/evidence gate (closed)

Human quality anchor supplied for this run:

- `final(3).md` — `QUALITY: ACCEPT / REFERENCE`.
  The corresponding local canonical artifact is
  `workspace/artifacts/wcase-1-single-source/final.md` with sha256
  `9c00c3c736f187cdd22a8e6ea8d908506664ae744a1a4f92a7861ce12b970cda`.
- `final-revised.md` — `QUALITY: REJECT AS QUALITY REGRESSION`, with the
  regression characterized as consumer-guide/说明书化 structure, repeated
  advisory templates, explicit checklist logic, flattened human presence,
  overly regular paragraph functions, and a summary-heavy ending. The local
  comparator is `workspace/artifacts/wcase-1-single-source/final-revised.md`
  with sha256 `bb0a8660dfe4ce7b56c4a0a7fbe9b218864388c5a41137486f98a4424382c0d4`.

The accepted artifact preserves the human material rather than smoothing it
away: Wang Xiaolin's personal use opens the piece, the seasonal redness is
rendered as a concrete consumer difficulty, the 32-person trial retains 2
people with no obvious change and 4 withdrawals, the paragraphs move through
the material narratively, and the ending remains restrained rather than
repeating purchase advice. The rejected comparator is more orderly but is a
prose-quality regression, not an improvement to the WCASE-1 outcome.

Explicit gate values for the accepted WCASE-1 artifact:

```json
{
  "outcome_pass": true,
  "evidence_pass": true
}
```

`evidence_pass` is the human WCASE gate for faithful preservation of the
provided material and its imperfect trial result; it is not a claim of
independent medical efficacy validation. The raw run record remains
unchanged, while the normalized record now carries these explicit human
verdicts.

## Final T004 closure

The current WCASE-1 path is accepted as minimal enough for this profile:

- 2 model requests;
- 1 `save_article` call;
- `pull_context` unused;
- accepted article outcome and evidence gate;
- no production code change.

The second request is still a native protocol/presentation continuation after
the function-tool result. T004 does not introduce a one-request terminal
mechanism merely to improve the request count. That would change the
submission/settlement contract without a demonstrated outcome need.

Final verdict: `CURRENT_PATH_ALREADY_MINIMAL`.

Stop after T004/T005 in this change. The next task is T006, which is not
started here.
