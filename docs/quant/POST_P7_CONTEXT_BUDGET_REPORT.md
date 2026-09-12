# Post-P7 Context Budget Report (R2)

Status: **CONTEXT_BUDGET_PASS**
Spec: ZUAEF Quant Post-P7 Production Reliability Closure Spec v0.1, Part II
Raw evidence: `docs/quant/POST_P7_RELIABILITY_RESULTS.json`
Model: `deepseek/deepseek-v4-flash-0731` (production `.env`); harness
receipts (provider usage) + FileStepStore snapshots + direct composition
measurement. No new telemetry framework was created.

## BASELINE RUNS / FRESH VS LONG SESSION

Conditions: controlled Friday-end fixtures, isolated workspaces, production
env. Long session = the spec §50 six-turn sequence threaded through the
production `start_profile_run` + `prior_semantic_history` (bounded
12-message semantic carryover) seams, one conversation.

Fresh, narrow intent (before the fix):

| Intent | Tool path | Requests | Input tokens | Largest request |
|---|---|---|---|---|
| B1 我现在持有什么？ | search_tools → get_positions | 3 | 43,222 | 15,240 |
| B2 验证到什么程度？ | search_tools → get_validation_status | 3 | 44,865 | 16,157 |
| B3 今天有什么机会？ | search_tools → get_signal_board | 3 | 44,030 | 15,720 |

Long session, narrow turns (before): 45,540 / 47,502 / 46,765 / 47,471 /
49,622 input tokens (turns 2–6), 3 requests each — i.e. long-session narrow
cost ≈ fresh narrow cost + ~4%. The production 151k→207k reading is the
cumulative session sum of the same per-turn pattern (and, when prior
assistant answers are longer than the fixture's, a proportionally larger
bounded window), not unbounded per-turn growth.

## CONTEXT CONTRIBUTORS (measured, not estimated)

Per-request message content (step snapshots, exact):

- fresh narrow final request: 4,006 chars of messages;
- long-session narrow final request (12-message window fully loaded):
  5,323 chars — history, user prompts, assistant prose combined;
- current tool result: ≤ 1,649 chars (bounded payloads).

Composition (direct measurement):

- QUANT_INSTRUCTIONS: 15,086 chars (largest single component);
- other harness capability instructions: 1,529 chars; core: 1,277 chars;
- tool descriptions: 7,724 chars resident + 6,368 chars deferred;
- the remainder of the ~15.7k-token single-request floor (harness system
  assembly, request framing, provider accounting) is **unattributed
  residual** — existing receipts cannot decompose it further, and it is
  reported as such rather than inferred.

## DOMINANT CAUSE (spec §26 classification)

- A. full conversation-history reinjection — **ruled out**: the 12-message
  semantic bound held in every long-session turn (≤ 5.3k chars/request).
- B. large prior tool-result reinjection — **ruled out**: bounded payloads
  (≤ 1.6k chars).
- C. oversized Quant instructions — **dominant identified component**
  (15.1k chars ≈ 3–4× any other measured component).
- D. repeatedly loaded skill/context — absent in narrow turns (one
  `load_capability` in the full-analysis turn, by design).
- E. tool schema/description volume — secondary (resident 7.7k chars).
- F. multiplier — every narrow turn spent its first model request on
  `search_tools` discovery, re-paying the whole fixed floor (≈ 15.7k
  tokens/request) three times per intent.

## MINIMAL FIX (spec §44)

1. **Instruction diet** (`plugin.py`): removed the duplicated zero-trigger
   bullet, compressed the freshness status bullets now that
   `freshness_reason` self-describes each verdict, merged the duplicated
   narrow-routing rule 9 into rule 4, tightened the validation-accounting
   paragraph, and replaced the stale `zuaef-quant-final-spec-v2.0-optimized`
   pointer with the live `zuaef-quant-spec-v3.1-20260905` source of truth.
   15,086 → 14,246 chars. Every hard invariant and every test-pinned phrase
   is preserved.
2. **Narrow-five residency** (`toolset.py`): `get_signal_board`,
   `get_positions`, `get_validation_status`, `run_live_scan`,
   `manage_watchlist` become resident. A narrow intent routes directly:
   3 requests → 2 per turn. This **demotes the P2 deferral authority for
   the five daily-operator intents** on measured evidence; the
   research/delivery tail and the retained `get_trading_context` fallback
   stay deferred behind ToolSearch, and CJK discovery still covers the
   resident tools (rank pins unchanged).

Not implemented (deliberately): further floor reduction beyond the diet and
any conversation-management change. The audit shows history and tool
results are already bounded by existing harness controls; the remaining
floor is instructions/schemas plus unattributed residual, and shrinking the
deferred tail further would trade routing reliability for marginal tokens.

## AFTER RESULTS

| Narrow intent | Before | After | Δ | Path after |
|---|---|---|---|---|
| B1 fresh | 43,222 (3 req) | 28,008 (2 req) | **−35%** | direct get_positions |
| B2 fresh | 44,865 (3 req) | 28,340 (2 req) | **−37%** | direct get_validation_status |
| B3 fresh | 44,030 (3 req) | 28,149 (2 req) | **−36%** | direct get_signal_board |
| Long turns 2–6 | 45.5–49.6k (3 req) | 30.3–32.1k (2 req) | **−33…−36%** | direct, zero escapes |

Long-session narrow turns now sit just above fresh narrow turns
(30.3–32.1k vs 28.0–28.3k) and grow only with the bounded window
(+1.7k tokens across turns 2→6) — the spec §34 "no unbounded linear
history growth" acceptance holds; there is nothing left that scales with
conversation length. Narrow-turn latency dropped 45–49 s → 6–12 s.

## REFERENCE CONTINUITY TEST

`002415现在怎么样？` → direct `get_symbol_context` (28,767 tokens, 2 req);
`把它加入观察。` → `它` resolved to 002415, `manage_watchlist` add executed,
scoped watchlist artifact verified by read-back, and the answer carried the
watchlist-is-not-candidate-pool caveat. Continuity survived the fix.

## CURRENT-FACT REFRESH TEST

Across the six-turn long session every answer was produced from a fresh
tool call in its own run (board/scan/positions/validation each re-read the
canonical artifacts); conversation prose was never consumed as market
evidence, and the instructions' "previous assistant prose is not evidence"
contract is unchanged.

## EVIDENCE QUALITY / ROUTING INVARIANTS (spec §45–§46)

`B1 → get_positions`, `B2 → get_validation_status`, `B3 → get_signal_board`
hold in every benchmark run (also in the long session, zero generic
escapes). Profitability UNPROVEN, PIT CONTAMINATED, missing-stays-missing
and the freshness contract are byte-identical invariants.

## VERDICT

**CONTEXT_BUDGET_PASS** — the reproduced symptom (disproportionate
narrow-intent cost) is explained by a measured decomposition, the fix uses
existing mechanisms only (per-tool residency flag + instruction text), and
no new router, memory runtime, summarizer, or context framework was
introduced. Quant strategy/business semantics are unchanged.
