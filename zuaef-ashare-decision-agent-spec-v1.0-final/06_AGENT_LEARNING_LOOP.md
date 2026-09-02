# Agent Self-Learning Strategy Loop

## 1. Definition

"Self-learning" in v1 means:

> A fresh ZUAEF run reads durable evidence from prior strategy attempts, identifies a specific failure/opportunity, proposes one testable strategy mutation, receives deterministic market evidence, and uses that evidence to change the next search direction.

It does not mean editing its own source, changing evaluator rules, online fine-tuning, RL or an infinite conversation.

## 2. Loop

```text
read prior Strategy Results
        ↓
identify largest unresolved problem
        ↓
state falsifiable hypothesis
        ↓
propose one material StrategySpec mutation
        ↓
evaluate_strategy()
        ↓
read evidence
        ↓
write Strategy Result
        ↓
end run
        ↓
fresh run
```

## 3. Fresh-run rule

Every iteration is a new `Agent.run`.

Benefits:
- causal attribution;
- bounded context;
- clear receipts;
- no hidden chat-history dependence;
- A/B history exposure can be tested.

## 4. Research memory

Authoritative learning memory is:
- Strategy Results;
- evidence artifacts;
- paper outcomes;
- real outcomes.

Generic chat Memory is not trading truth.

## 5. Required reasoning in each result

Without creating a large record class, the Agent must answer:
- What is the parent's biggest evidence-backed problem?
- What one change is being made?
- Why might it help?
- What would falsify the idea?
- What did evidence show?
- What should the next run do?

## 6. Behavioral constraints

- never invent evidence;
- never change rules/costs/data split to make a strategy pass;
- `NO_CHANGE` is acceptable when evidence is insufficient;
- avoid repeatedly tuning the same parameter after structural failure;
- distinguish historical fit from safe activation;
- state uncertainty and data limitations.

## 7. Three-run proof

First autonomous proof is exactly 3 fresh runs.

Passing means:
- each child references prior evidence;
- each mutation is explainable;
- evidence is real/deterministic;
- the next direction changes because of evidence.

Three successful LLM calls are not proof.

## 8. Ten-run learning test

Only after 3-run proof.

Compare:
- A: history/results hidden;
- B: same model/task/evaluator, prior Strategy Results available.

Track repeated invalid strategies, duplicates, repeated known failures, iterative research metrics, host-only promotion/holdout metrics and paper/forward behavior when available.

Do not run 100 iterations until 10-run evidence shows learning rather than random search.

## 9. Spend

Three runs need only a host iteration limit.

Before materially larger autonomous batches, use upstream Harness `SpendLimits` instead of building a custom budget ledger.

## 10. Active strategy authority

Agent may recommend activation/replacement. Human/host owns the active-strategy set in v1.

A single fresh backtest cannot silently alter live money decisions.
