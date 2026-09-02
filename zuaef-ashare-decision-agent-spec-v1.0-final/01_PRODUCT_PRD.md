# Product Requirements — A-Share Decision Agent

## 1. Problem

A small-capital A-share trader commonly suffers from four weaknesses:

1. cannot scan thousands of securities consistently;
2. decisions are dominated by recent impressions and intuition;
3. historical base rates are rarely checked before acting;
4. losses are explained narratively rather than converted into testable strategy changes.

The product turns this into an evidence loop.

## 2. Product boundary

The product is an **A-share decision assistant**, not an autonomous trader and not a guarantee of investment return.

The user keeps final order authority in v1.

## 3. Jobs to be done

### Before market
- summarize market regime and active strategies;
- identify whether the environment is favorable for any validated strategy;
- produce a watch universe rather than a stock-tip list.

### During market
- deterministically scan real/near-real market data;
- surface only triggered candidates;
- generate a compact Decision Brief with evidence;
- return `NO_TRADE` when appropriate.

### Before a trade
Answer:
- which validated strategy triggered;
- how many comparable observations exist;
- after-cost expectancy and failure modes;
- whether current regime resembles useful historical/forward regimes;
- entry condition, invalidation condition, expected holding window;
- major execution risk.

### After market
- settle paper outcomes;
- record manually executed real outcomes;
- compare intended vs actual execution;
- avoid strategy changes when evidence is insufficient.

### Periodically
- read accumulated Strategy Results;
- identify the most important failure/opportunity;
- mutate one material strategy element;
- re-evaluate;
- preserve evidence whether the mutation helped.

## 4. Primary outputs

### Decision Brief
Allowed actions:
- `NO_TRADE`
- `WATCH`
- `ENTER_CANDIDATE`
- `HOLD`
- `REDUCE`
- `EXIT`

These are presentation decisions, not runtime workflow states.

Every actionable brief must contain strategy, trigger evidence, sample size, after-cost evidence, regime context, holding window, invalidation/risk boundary and why acting is preferable to waiting.

### Strategy Result
Human/Agent-readable artifact containing:
- parent strategy;
- one material change;
- hypothesis and falsification;
- deterministic evidence;
- OOS/replay evidence;
- failure explanation;
- conclusion and next research direction.

## 5. MVP scope

- Market: China A shares.
- Primary universe: CSI 500 tradable subset.
- Historical frequency: daily.
- Live assistance: near-real snapshots.
- Typical holding: 2–10 trading days.
- Direction: long-only.
- Default historical signal timing: information available by T close, execution T+1 open.
- Human executes orders manually.
- Position context may initially be manually entered.

## 6. Not MVP

No automatic broker orders, leverage/shorting, futures/options, HFT, graph runtime, generic multi-agent framework, RL, general experiment platform, web dashboard before business proof, or news/fundamental agents before the price/volume loop proves useful.

## 7. Business success metrics

System-level:
- candidate briefs with complete evidence;
- `NO_TRADE` behavior when no validated opportunity exists;
- repeated-invalid-strategy rate;
- simulation-to-paper divergence;
- paper-to-real execution gap;
- after-cost expectancy;
- paper/real maximum drawdown;
- frequency of mutations that improve pre-declared held-out/forward evidence.

Learning proof compares:
- A: Agent cannot read prior Strategy Results;
- B: same model/task/evaluator, prior Strategy Results available.

Learning is supported only if B reduces repeated failure and improves pre-declared OOS/forward outcomes.

## 8. Failure criteria

MVP is not accepted if:
- AKShare is mocked rather than really called;
- data freshness is not measured;
- current constituents are silently used as historical membership;
- Qlib profits depend on impossible execution and no replay catches it;
- LLM computes indicators instead of deterministic code;
- Agent emits arbitrary executable Python;
- iterative search repeatedly sees the final holdout;
- tool success is described as proof of trading value;
- the implementation becomes a platform before one real baseline works.
