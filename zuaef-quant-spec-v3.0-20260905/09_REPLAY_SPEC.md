# 09 — 10-Day PIT-Safe Replay

**Priority:** P0.  
**Purpose:** create fast diagnostic/evidence value while live forward data accumulates.

## Important semantic boundary

Replay evidence is **not live forward evidence**.

Keep separate counters:

```text
Historical Backtest
Recent PIT-Safe Replay
Live Forward
```

Never increment `live_forward_observations` from replay.

## Scope

Start with the most recent **10 trading days** for which required data is available. Expand to 20 then 60 only after the 10-day pipeline is verified.

## Time-machine rules

For replay point `T`:

1. Runtime clock reports `T`.
2. Every market/fundamental/event read must enforce `available_at <= T`.
3. A bar not yet complete at `T` cannot be used as if complete.
4. Current/future index composition may not leak backward.
5. Later corrections/revisions must either be reconstructed correctly or clearly label the run degraded.
6. The production strategy/config version under test must be explicit.

## Intraday cadence

If production observes at multiple times during the day, replay those times. Do not run only at 15:00 and claim to know what 10:30 would have seen.

Example:

```text
09:35 → observation/decision
10:00 → observation/decision
10:30 → observation/decision
...
14:30 → observation/decision
```

Use actual production cadence if different.

## Settlement

After a replay decision is frozen, the evaluator may reveal later data and calculate:

- +1d / +3d / +5d return where applicable;
- realized exit return;
- MFE (maximum favorable excursion);
- MAE (maximum adverse excursion);
- estimated costs/slippage;
- rule compliance.

## 10-day output

The report must show:

- trading days replayed;
- observation count;
- candidates and triggers per day;
- decisions by reason;
- settled trigger count;
- PIT blocked/degraded events;
- runtime/evidence-pipeline failures;
- expectancy/dispersion only where sample size permits;
- explicit warning that this is replay, not live forward.

## Acceptance

- no read after replay clock in an adversarial leakage test;
- repeated run with same inputs/config is deterministic;
- replay evidence cannot appear in live-forward counters;
- at least one synthetic test proves an EOD bar cannot leak intraday;
- report can explain every zero-trigger day as either valid no-trigger or blocked/degraded.
