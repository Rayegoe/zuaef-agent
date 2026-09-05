# 11 — Live Forward Evidence

## Why

Live forward observations are the strongest evidence because they are generated before the outcome is known and naturally preserve the real runtime/data conditions of the day.

## Evidence milestones

Do not use calendar days alone. Count valid, settled, sufficiently independent triggers.

Suggested gates:

- **Operational cold start:** 5–10 trading days to prove the loop remains alive.
- **Preliminary evidence:** ~20–30 valid settled triggers.
- **Early meaningful assessment:** ~50–100 triggers, ideally across different regimes.
- **More credible assessment:** 100+ triggers spanning clear market-state changes.

Time ranges such as 2–4 months or 3–6+ months are only rough expectations; sample count and regime diversity matter more.

## M1 formal audit gate

Trigger the first formal M1 audit when either:

- 20 trading days have elapsed, **or**
- 30 valid forward triggers have settled,

**whichever occurs first**, provided the evidence pipeline has had **zero unresolved integrity failures**.

## Observation record

Minimum useful fields:

- timestamp / available-at clock;
- symbol;
- contemporaneous price;
- market regime (once deployed, or shadow state);
- candidate score/version;
- trigger state and reason;
- every deterministic gate state;
- decision;
- position/risk context;
- +1d/+3d/+5d or actual exit outcome;
- MFE/MAE;
- transaction cost/slippage assumption or actual cost if later available;
- final settlement state.

## Evaluation metrics

Prioritize:

- expectancy after costs;
- distribution and tail loss;
- max drawdown at strategy/account level;
- hit rate only with payoff ratio;
- MFE/MAE;
- performance by market regime;
- `READY` vs `NEAR` separation;
- concentration of profit in a few outliers;
- signal/strategy degradation over rolling windows.

## Zero-trigger policy

If 10–15 trading days pass with a healthy candidate pool but zero triggers:

- diagnose in sandbox;
- do not loosen production merely to manufacture signals;
- test whether the cause is market state, thresholds, stale data, PIT blocking, or a bug.
