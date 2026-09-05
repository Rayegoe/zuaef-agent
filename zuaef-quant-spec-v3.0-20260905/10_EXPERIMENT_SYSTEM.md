# 10 — Experiment System

## Experiment lifecycle

```text
PROPOSED
  ↓
RUNNING_S0 / RUNNING_S1
  ↓
REJECTED  or  REPLAY_PASS
                  ↓
              SHADOW
                  ↓
          FORWARD_EVALUATION
                  ↓
          PROMOTED / REJECTED
```

## Required experiment record

- `experiment_id`
- human/Agent hypothesis stated before evaluation
- baseline strategy/config version
- exactly what changed
- data/evidence scope
- expected causal mechanism
- primary metric(s)
- risk/guardrail metrics
- pre-declared rejection condition where practical
- run IDs
- result summary
- promotion state

## First experiment families

### Candidate count

`Top 30 vs 50 vs 80` — measure trigger quality and concentration, not just signal count.

### Score weights

Current reported baseline is value/quality heavy. Explore whether a short-cycle small-account strategy benefits from more tradability/relative-strength/timing weight, while treating fundamentals more as quality/risk filters.

### Trigger sensitivity

Vary one threshold at a time (e.g. volume ratio) and observe trade count, expectancy, drawdown, stability, and regime dependence.

### Market regime

Compare no regime gate vs shadow regime gate; evaluate whether it avoids negative-expectancy periods without eliminating the opportunity set.

### Exit policy

Hold entry fixed and test exit families independently.

## Anti-overfit rules

Forbidden loop:

```text
bad result → tweak parameter → rerun same data → good result → production
```

Required loop:

```text
problem → hypothesis → isolated change → replay/walk-forward → shadow → new forward evidence → promotion decision
```

Do not optimize dozens of parameters simultaneously. Prefer ablations and small causal experiments.

## Production freeze

Production config receives a stable version. Experiments reference it but cannot mutate it in place. Promotion creates a new production version with an audit trail.
