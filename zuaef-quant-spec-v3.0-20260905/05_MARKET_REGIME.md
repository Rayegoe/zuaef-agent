# 05 — Market Regime / Participation Gate

**Status:** TARGET_V3, initially shadow-only.

## Purpose

Before asking “which stock should be bought?”, answer “should a weakly informed small retail participant be in this market state at all?”

This is deliberately above stock-level triggers.

## Initial state model

Use three production-relevant states first:

- `DO_NOT_PARTICIPATE`
- `SELECTIVE`
- `NORMAL`

`AGGRESSIVE` may exist later but should not be necessary for v3 acceptance.

## Inputs — start simple

Do not invent a large factor zoo. Start with auditable, low-dimensional inputs such as:

- index trend/return/realized volatility;
- market breadth: advancing/declining ratio, fraction above relevant moving averages;
- sector breadth/dispersion;
- turnover/liquidity change;
- trigger success/failure/degradation metrics from recent forward observations;
- abnormal market/trading status.

All inputs need `as_of`/`available_at` semantics.

## Output contract

Output:

- `regime`
- `confidence` (optional numeric, never a substitute for gates)
- `reason_codes[]`
- `as_of`
- `input_snapshot_id`
- `model_or_rule_version`
- `mode`: `shadow | production`

## Rollout

1. Implement deterministic baseline.
2. Run shadow-only against current production decisions.
3. Replay recent 10/20/60 trading days PIT-safely.
4. Measure whether it reduces bad exposure without merely suppressing all trades.
5. Promote only after explicit evidence review.

## Interaction with signals

Recommended semantics:

```text
DO_NOT_PARTICIPATE → no new entries regardless of symbol READY state
SELECTIVE          → higher entry/risk threshold; lower exposure
NORMAL             → standard production thresholds
```

Do not let Agent prose override `DO_NOT_PARTICIPATE`.
