# Acceptance Gates

## A. Product / Trading Assistant

A project that only produces reports/backtests is not accepted as a usable trading assistant.

Minimum operational acceptance:

- real market inputs produce a real active watch universe;
- active watch universe can refresh during trading hours at a practical seconds-to-minutes cadence (initial target approximately <=60s when source latency allows);
- material opportunity state changes are surfaced without requiring manual page refresh;
- `NO_TRADE` is distinguishable from stale/unavailable/untrusted system state;
- a user-confirmed real or paper BUY can be recorded as an open position;
- open positions are monitored continuously for strategy/risk/exit conditions;
- HOLD/REDUCE/EXIT-relevant changes can alert the user;
- closed/settled observations produce forward outcome records;
- business pages do not rely on mock/test/demo values as current results.

Before calling Trading Assistant v0.1 operational, run it through at least several consecutive real trading sessions and record failures instead of masking them.

## B. Decision Usefulness

Operational function alone does not prove edge.

Track whether:

- selected/watch names outperform or otherwise improve on simple matched/random/liquidity controls over the strategy horizon;
- READY states are more informative than WATCH controls;
- invalidation/exit actions reduce downside or protect capital;
- Agent review adds measurable value beyond deterministic triggers.

No favorable difference => simplify or change the policy; do not add complexity to defend it.

## C. Data Truth

- deliberately wrong volume semantics => validator blocks actionable live evaluation;
- future-data adversarial input => scoped anti-leak test fails;
- financial data is unavailable before its real availability date for historical claims;
- stale/disconnected live feed cannot be displayed as current;
- unavailable evidence cannot be relabeled `NO_TRADE`.

## D. Quant Research

- Composite score can produce 5d/8d IC/RankIC/quantile evidence when sample allows;
- no incremental value => candidate score may be demoted/simplified;
- all sibling trials remain visible;
- insufficient sample => no fake DSR/PBO precision;
- headline return is net;
- unsupported market events cannot silently enter a trusted baseline.

## E. Agent

- at least one non-preprogrammed research question;
- Agent references relevant Lesson/Forward evidence;
- hypothesis is falsifiable;
- Agent can reject its own hypothesis;
- Agent cannot change evaluator/cost/split and call the result comparable;
- high-frequency polling does not depend on continuous LLM calls.

## F. Decision Replay

- two material runs/observations on one day remain distinct;
- previous decision artifacts are not rewritten to match later knowledge;
- a sampled old decision can reconstruct market evidence, active policy, Agent judgment, user action (if any) and later outcome.

## G. Anti-Architecture

- no new persistent structure without a current consumer;
- no new model-visible tool without a real action/effect rationale;
- no generic workflow/DB/platform introduced for hypothetical scale;
- no engineering metric is allowed to substitute for operational or market usefulness.

## H. Forward Honesty

- `forward_settled=0` => no hit-rate claims;
- PIT contamination / unsupported accounting / incomplete OOS => no proven-profitability claim;
- observation-only or paper results are not presented as realized capital performance.

## I. Regression

Preserve existing default/quant tests, lint, fail-closed universe behavior, financial sector-aware behavior and no autonomous broker action.

Passing regression is necessary but never sufficient for product acceptance.
