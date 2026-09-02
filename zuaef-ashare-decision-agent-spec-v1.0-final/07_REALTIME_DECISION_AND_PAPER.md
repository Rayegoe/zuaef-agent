# Live Decision, Paper and Real Feedback

## 1. Live goal

Answer during a trading session:

> Is there an evidence-backed opportunity now, and is acting better than waiting?

Near-real assistance, not HFT.

## 2. Scanner

Deterministic code, not LLM, computes:
- prices/returns;
- moving statistics;
- volumes/turnover;
- strategy conditions;
- universe filters;
- position conditions.

Broad market → bounded candidates → LLM.

## 3. DecisionContext

Each trigger should contain only useful facts:
- symbol/name;
- timestamp/freshness;
- active strategy;
- exact trigger;
- current price/volume facts;
- market/regime summary;
- strategy historical/forward summary;
- current position if any;
- execution/risk boundary.

Avoid dozens of nullable fields.

## 4. Decision Brief

`ENTER_CANDIDATE` is not an order. The user decides whether to act.

## 5. Watch process

If needed after interactive proof:

```text
quant_watch
  poll current market
  deterministic scan
  no trigger → no LLM
  trigger → bounded ZUAEF decision run
  emit Decision Brief
```

It is a host process, not Plugin background work.

## 6. Paper/shadow

Each Decision Brief can be settled using frozen strategy/rules:
- decision timestamp;
- simulated executable price;
- costs/slippage;
- exit rule;
- paper outcome artifact.

This creates forward evidence without capital.

## 7. Manual real feedback

Record:
- intended vs actual execution;
- quantity;
- fees;
- exit;
- realized PnL;
- optional short divergence reason.

No broker credentials in v1.

## 8. Evidence precedence

```text
real execution evidence > paper forward evidence > historical simulation
```

But sample size matters; a few real trades do not automatically erase long historical evidence.

## 9. Sim-to-real gap

Track:
- inability to fill;
- worse/slower entry;
- different exit;
- underestimated costs/slippage;
- stale signal;
- regime mismatch.

These are future strategy evidence.

## 10. Product safety boundary

v1 does not place orders, guarantee profit, hide drawdown, force a daily trade or treat Agent prose as deterministic market fact.
