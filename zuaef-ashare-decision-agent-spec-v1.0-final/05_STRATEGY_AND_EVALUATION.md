# Strategy and Evaluation Protocol

## 1. Strategy is the search unit

A factor can help, but cashflow comes from a complete executable strategy.

```text
Strategy = Universe + Entry + Exit + Holding + Risk boundary + Position sizing
```

## 2. Minimal StrategySpec

StrategySpec is an unavoidable execution ABI, not a workflow schema.

Example:

```toml
schema = 1
name = "volume_pullback_reversal"
universe = "csi500"
entry_expression = "..."
exit_expression = "..."
max_holding_days = 5
stop_loss_pct = 0.03
take_profit_pct = 0.06
position_fraction = 0.10
max_positions = 5
```

Do not add lifecycle, promotion, approval or workflow status. Do not allow arbitrary Python.

## 3. Expression strategy

Reuse Qlib expressions/operators where practical. Do not invent a general ZUAEF quant DSL.

If Qlib expressions cannot directly express a specific exit/execution rule:
- keep features/signals declarative;
- implement the minimal host-owned deterministic execution rule.

Validate exact supported operators and offset semantics against installed Qlib 0.9.7.

## 4. One material mutation

Each Agent child strategy changes one major idea when possible:
- threshold;
- holding horizon;
- exit condition;
- regime filter;
- one signal clause.

Avoid changing universe + entry + exit + sizing + costs simultaneously.

## 5. `evaluate_strategy()`

Owns:

```text
validate spec
→ resolve frozen data/protocol
→ fast Qlib/vector test
→ freeze signals/trades
→ independent event replay
→ OOS/robustness metrics
→ evidence artifacts
→ bounded result
```

The Agent cannot change evaluator, market rules, costs or benchmark inside the same experimental generation.

## 6. Metrics

Primary business evidence:
- trade count;
- net PnL/net return;
- expected PnL/return per trade;
- profit factor;
- maximum drawdown;
- average holding period;
- cost drag.

Supporting:
- win rate;
- average win/loss;
- turnover;
- Sharpe/Sortino;
- IC/RankIC when applicable.

Never optimize win rate alone.

## 7. Independent replay

Replay must be sufficiently independent from Qlib.

Input:
- frozen candidate signals/trade intents;
- raw market data;
- frozen execution/rule/cost config.

Not input:
- Qlib final NAV.

Output:
- executed/unfilled trades;
- NAV/returns;
- drawdown;
- turnover/costs;
- blocked-trade reasons.

Surface Qlib/replay divergence. A predeclared tolerance may live in benchmark config, e.g. annualized-return difference <= 3 percentage points. Large unexplained divergence makes the strategy result untrustworthy.

## 8. Replay runtime

First evaluate a maintained Backtrader-compatible runtime; `backtrader-next` is the preferred current candidate because it is actively maintained and supports modern Python.

If integration evidence shows that it materially complicates the MVP, a small independent deterministic replay is acceptable only if A-share failure-mode tests are strong and the code remains small/auditable.

Borrow ABQ's dual-engine pattern, not its constants blindly.

## 9. Anti-overfit protocol

Repeated Agent search turns any repeatedly exposed test set into training data.

Therefore separate information roles:

### Iterative research window
Agent-visible every iteration. Use walk-forward/time splits inside it.

### Promotion test
Host-only, bounded use for promising finalists. Detailed metrics are not written into ordinary Agent-readable iteration history.

### Champion holdout
Hidden from Agent. Used rarely/finally. Never fed back into iterative search.

### Forward paper/real
Begins at deployment freeze time. Never rewritten retroactively.

Exact boundaries are frozen in `benchmark.toml` before a benchmark generation starts.

Do not call a repeatedly queried set "sealed test".

## 10. Robustness minimum before active use

- sufficient trade sample;
- after-cost result;
- neighboring parameter sensitivity;
- time/regime stability;
- no obvious single-period dependence;
- replay consistency;
- no leakage failure.

Do not build a gate framework. Evaluator returns evidence; Agent interprets it.

## 11. Reward

No RL in v1.

Use observable business metrics. A candidate with higher gross return but worse costs/drawdown is not automatically better.
