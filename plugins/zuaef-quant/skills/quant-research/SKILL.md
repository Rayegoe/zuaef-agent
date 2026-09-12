---
name: quant-research
description: Quant full-analysis methodology (全面分析 / 深度研究 / 趋势预测 on any A-share symbol). Evidence hierarchy, coverage checklist, Bull/Base/Bear forecast contract, CodeMode research recipes, web-evidence contract, research-packet reuse and degradation rules. Load when the user asks for a full analysis, trend forecast, scenario research, or a research recap on a symbol.
---

# Quant full-analysis methodology

You are doing business research, not executing a fixed pipeline. Pick the
evidence layers the question actually needs; a short factual question never
loads this whole checklist.

## Market-wide task recipe (A股大盘/全市场原因)

Use this recipe for questions such as 今天为什么跌? / A股大跌原因? / 为什么普跌? /
今天市场发生了什么? / 某板块为什么突然下跌?.  The default flow is:

1. Call `get_market_context` exactly once.
2. Inspect `missing`; any unavailable layer stays missing — never substitute
   candidate-pool, watchlist or position data for market-wide evidence.
3. Explain only `OBSERVED` facts from the returned evidence.
4. Build an `INTERPRETATION` / causal chain and label it as interpretation.
5. State `UNKNOWN` / unresolved links explicitly.
6. Answer and END.

Normally do not call `get_symbol_context`, `get_signal_board`,
`get_positions`, `record_decision_brief`,
`record_trade_outcome`, `run_code` or `render_quant_business_artifact` for a
market-wide question unless the user's question explicitly requires them.
Do not append unrelated portfolio EXIT_ALERT facts unless the user asked
what this means for their holdings.

### Scope invariant

A claim's scope may never exceed the scope of the evidence supporting it.
`CANDIDATE_POOL` evidence can say "在当前候选池中，多数股票走弱", never
"A股普跌", "整个市场风险偏好下降" or "券商板块领跌".  `SINGLE_SYMBOL`
evidence can say "长江证券今天下跌", never "券商板块领跌".  Only
`A_SHARE_MARKET_WIDE` (or clearly sourced external market-wide evidence with
source and time) can support a whole-market claim.

### Response layering

Use three visible layers for market-cause analysis:

- OBSERVED: direct fields from the evidence packet.
- INTERPRETATION: the possible causal chain, clearly framed as judgement.
- UNKNOWN: what the evidence cannot prove (for example, price co-movement
  alone cannot prove a single news event was the only cause).

Prediction alignment is not causal validation: a direction match means only
"与该假设方向一致", not "因此因果关系成立".  Previous assistant prose and
conversation memory are not evidence.

## Narrow intent routing (use before loading a broad context)

Match the question to the narrow tool before opening a broad projection:

- today's READY/NEAR board -> `get_signal_board`
- current holdings / exit alerts -> `get_positions`
- strategy validation maturity / PIT status -> `get_validation_status`
- explicit rescan/refresh -> `run_live_scan`
- watchlist view/add/remove -> `manage_watchlist`
- single-symbol quote/diagnosis -> `get_symbol_context`

`get_trading_context` is the broad legacy-compatible projection. Use it only
when the question genuinely combines several scopes, not as the default for a
narrow intent. When the user explicitly asks to refresh/rerun, use
`run_live_scan`.

## Evidence hierarchy (what beats what)

1. Canonical trade/market state — get_signal_board, get_positions,
   get_validation_status, get_symbol_context, get_trading_context
   (host facts: readiness/freshness, holdings/exit alerts, validation
   maturity, quote, market rules, S3 distances).
2. Structured official evidence — get_market_intelligence (notices, company
   news, fundamentals from structured feeds).
3. Structured public evidence — Harness WebSearch/WebFetch results with URLs.
4. Customer-reported evidence — CUSTOMER_REPORTED / UNVERIFIED, provenance
   recorded; influences attention and hypotheses, never strategy state.
5. Sandbox-derived evidence — CodeMode output (DERIVED host facts).
6. Your interpretation — always presented as judgement, never as fact.

## Coverage checklist for a full analysis (全面分析)

- Current market: get_symbol_context (quote + freshness + market rules).
- History/trend/volume: hydrated history; CodeMode statistics when the
  question needs more than eyes on numbers.
- Strategy context: S3 clause distances when the symbol carries history.
- Portfolio context: get_positions (holdings/exit alerts); watchlist
  membership via manage_watchlist(action="list").
- Structured finance evidence: get_market_intelligence.
- Open web research — only when open-ended questions make it materially
  useful (why did it move, industry/policy context): Harness WebSearch /
  WebFetch. Every web fact must carry source, url, published_at when known,
  and observed_at. Never "网上消息显示" without a source.
- Sandbox statistics when useful (recipes below).
- Scenario forecast (contract below) + conditional recommendation.
- Unknowns: name them explicitly. Insufficient evidence is a valid result.

The order is yours; the coverage is what a full analysis must reach or
explicitly report as missing.

## Degradation rules

- Web research fails → complete the technical/history analysis, mark the
  research PARTIAL, say which layer is missing.
- Sandbox fails → fixed evidence still completes; no invented probabilities.
- History cannot hydrate → no trend claims at all; quote-level facts only.
- A missing layer never becomes a guess; the reply states the gap.

## Forecast contract (Bull / Base / Bear)

Never "明天一定涨" and never a target price presented as fact. Each scenario
carries: conditions (what must hold), evidence basis (which layers above),
invalidation (what kills it), main uncertainty. Probabilities only from real
CodeMode distributions with disclosed sample size — never invented numbers.
The conditional recommendation states what would have to be true to act.

## Historical statistics disclosure

Any similar-history / forward-distribution claim must state: sample size,
window definition, forward horizon. Low sample stays low sample — never wrap
it in stable-sounding probability language.

## Validation accounting (never estimate maturity in prose)

Strategy maturity numbers (validation age, observation/settlement counts,
entries, exits) come only from get_validation_status's
`validation_accounting` block (the same ledger block exposed by the broad
`get_trading_context` compatibility projection) — quote them, never sum them
up yourself ("约三周多" is a defect). Lead with `validation_age_trading_days`
(measured in-session scan days; calendar days are secondary context).
Keep the two planes separate in wording: a position in EXIT_ALERT is
still OPEN until the human executes and the ack closes it; an observation
is settled only when its full-horizon (d8) window exists. Name each
position's lifecycle factually (entry date, state, exit trigger,
settled yes/no) rather than summarizing the ledger in one sentence.

## CodeMode research recipes (temporary analysis, read-only /quant-cache)

The sandbox is a minimal Python interpreter: CSVs at
/quant-cache/daily/<code>_qfq.csv (header date,symbol,open,high,low,close,
volume,amount,turnover), read with open(path).read().splitlines() — file
objects are NOT iterable; pathlib lacks glob/iterdir (use os.listdir()); no
statistics/csv/math import or __import__ — write plain arithmetic loops.
Hydration happens host-side BEFORE the sandbox (run_code cannot fetch).

- Forward distribution: sort by date, take the last N sessions matching a
  state definition (e.g. close within ±1% of MA5), collect the next-K-day
  returns from all earlier matches; report min/percentiles/max and n.
- Similar-history: normalize a recent window (returns, volume ratio), find
  the m closest windows earlier in the series by squared distance, report
  their forward outcomes and spread.
- Relative strength: symbol's K-day return minus a peer symbol's or a
  same-slice comparison across several /quant-cache files; rank, don't
  judge.
- Volatility regime: rolling K-day stdev of daily returns (hand-rolled
  loop); report current vs its own history as a percentile.

Every recipe reports n; a sandbox answer without sample size is not done.

## Research packet (durable business artifact)

After a full analysis, persist via save_research_packet (symbol, thesis,
scenarios, supporting facts, counter evidence, risks, invalidation, unknowns,
source references, research_status). Reuse on the next look: read the latest
packet as a PRIOR HYPOTHESIS, then re-verify current quote/evidence — a prior
packet is never current market truth. Conversation history is not evidence.

## Research status semantics

COMPLETE / PARTIAL / INSUFFICIENT_EVIDENCE are business research states.
Runtime states (completed / failed / limit_reached) are a different layer —
never conflate "the run finished" with "the research was complete".

## Customer-reported evidence

"供应商说订单很满" is CUSTOMER_REPORTED / UNVERIFIED: record it with
provenance (record_customer_evidence), let it shape attention, hypotheses and
web search terms — it can never create READY/NEAR, change the candidate pool,
the strategy, or any fill.
