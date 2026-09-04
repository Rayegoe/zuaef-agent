# Global Product Strategy — Trading Decision System

## 1. Product Definition

ZUAEF Quant is not a backtest project, a report generator, or an evidence dashboard.

Its product is a **continuously operating A-share trading decision assistant** for a small-capital individual investor:

> Reduce the full market to a small set of actionable opportunities, monitor them during trading hours, help manage positions after execution, and learn from real outcomes.

The system succeeds only if it improves the user's allocation of **capital and attention** under uncertainty.

The research harness exists to make this trading loop more trustworthy and more useful. It is not the product by itself.

## 2. The Four Business Objects

The system manages four real business objects:

1. **Market State** — what environment are we in now?
2. **Opportunity** — which stocks deserve scarce attention now?
3. **Position** — after a trade exists, what should happen to the capital already committed?
4. **Capital** — what is the expected benefit/risk of acting versus not acting?

Every major feature must materially improve at least one of:

- opportunity discovery;
- intraday monitoring;
- position management;
- capital protection/allocation;
- learning from realized outcomes.

If it does none of these and does not unblock their truthfulness, it is not a priority.

## 3. One Closed Business Loop

```text
real market
    ↓
slow opportunity selection
    ↓
small active watch universe
    ↓
fast intraday monitoring
    ↓
NO_ACTION / WATCH / NEAR / READY / INVALIDATED
    ↓
human decision / manual execution
    ↓
open position
    ↓
continuous position monitoring
    ↓
HOLD / REDUCE / EXIT
    ↓
real outcome
    ↓
comparison / lesson / research question
    ↓
strategy retained, simplified, changed, or retired
    ↓
real market
```

There is no separate "research product" and "trading product". Research is the learning function of the same loop.

## 4. Three Time Scales

### Slow layer — selection

Cadence: daily or every few hours when justified.

Purpose:

`full market -> eligible universe -> ranked candidates -> small active watch universe`

Uses slower-changing information such as fundamentals, valuation, liquidity, sector state and medium-horizon price context.

### Fast layer — monitoring

Cadence target for the active watch universe: **seconds-to-minutes**, with the initial practical target no worse than roughly one minute when the current quote source allows it.

Purpose:

- update price/volume/relative-state evidence;
- detect NEAR/READY/INVALIDATED transitions;
- alert only on material state changes;
- distinguish "no opportunity" from "system unavailable".

The strategy holding period may be days; monitoring must still be minute-level.

### Position layer — capital management

Once the user records a real or paper trade, the stock is no longer merely a candidate. The system must continuously manage the position context:

- entry and current price;
- unrealized P&L;
- MFE/MAE;
- stop/take-profit/time-exit/strategy invalidation;
- market/sector deterioration when relevant;
- HOLD / REDUCE / EXIT state.

A system that discovers entries but forgets positions is incomplete.

## 5. Strategy Is Replaceable; The Trading Loop Is Stable

S3 is the first research policy, not the identity of the product.

Current S3 hypothesis:

> Among sufficiently sound and tradable companies, short-term sharp declines followed by renewed participation and price stabilization may contain a short-horizon mean-reversion opportunity.

S3 may be supported, simplified, conditioned, or rejected.

The stable product contract remains:

`select -> monitor -> decide -> manage -> observe -> learn`

Do not preserve a weak strategy merely to preserve the project.

## 6. Deterministic Monitor + Agent Escalation

Do not use an LLM as a polling engine.

High-frequency recurring work belongs to deterministic code:

- quotes;
- price/volume conditions;
- relative measures;
- risk thresholds;
- position P&L;
- time-based exits;
- state transitions.

The Agent is invoked on material events or scheduled reviews:

- candidate becomes NEAR/READY;
- trigger is contradicted or invalidated;
- position approaches/enters an exit condition;
- new relevant context creates uncertainty;
- pre-market or close review;
- research review after settled outcomes.

Agent value is interpretation, prioritization, contradiction detection and research hypothesis formation — not repeated arithmetic.

## 7. Human Boundary

Current product is decision support, not autonomous brokerage.

The system may:

- monitor continuously;
- rank and alert;
- recommend WATCH/READY/HOLD/REDUCE/EXIT with reasons;
- record a user-confirmed execution;
- measure outcomes.

Actual capital movement remains a human external-effect boundary unless explicitly changed by a future product decision.

## 8. Business Truth vs Engineering Proof

Engineering proof is necessary but not sufficient.

Tests, audit states, validators, reports and provenance are **supporting controls**. They are not product value by themselves.

Real product evidence is:

- real market inputs;
- real candidate selections;
- real intraday state transitions;
- real alerts;
- real/paper positions tracked through closure;
- real forward D+1/D+3/D+5/D+8 paths;
- real comparison against simple controls/baselines;
- evidence that the system improved selection, timing, risk management, or avoided a bad action.

Mocks and fixtures may test code, but may never be presented as business outcomes.

## 9. "NO_TRADE" Has Two Different Meanings

These must never be conflated.

### Valid no-opportunity outcome

The system is healthy, the active universe was scanned, and no opportunity met the current policy.

This is a legitimate `NO_TRADE`.

### System unavailable / evidence unavailable

Data, timing, semantics or monitoring is not trustworthy enough to evaluate.

This is **not** `NO_TRADE`; it is an operational/trust failure that must be shown as such.

## 10. Product Value Ladder

### Level 1 — Operationally useful

The system can continuously:

- generate a real watch universe;
- monitor it during market hours;
- alert on material opportunity changes;
- accept a user-confirmed position;
- monitor that position to exit/closure;
- record forward outcomes.

### Level 2 — Decision useful

Forward evidence shows that selected/alerted names or managed decisions are more useful than simple controls, or that the system reliably avoids poor trades.

### Level 3 — Demonstrated edge

After realistic costs and market constraints, a bounded policy/context has positive expectancy that survives validation/OOS/forward observation.

Do not claim Level 3 while only demonstrating Level 1 or Level 2.

## 11. How P0–P6 Fit This Strategy

P0–P6 remain the research/assurance spine. They are not replaced.

- **P0** makes the live and historical instruments trustworthy enough to observe reality.
- **P1** makes the backtest/replay a trustworthy comparator rather than an accounting illusion.
- **P2** determines what actually contributes to opportunity quality.
- **P3** determines when/where a mechanism survives and where it fails.
- **P4** lets the Agent choose valuable uncertainties instead of only executing a host script.
- **P5** makes decisions replayable enough to learn from them.
- **P6** turns real forward outcomes into strategy changes.

Critical correction: **forward observation and live product operation start as early as truth gates allow; they are not postponed until the formal P6 research phase.** Formal P6 closes the learning loop; it does not mark the first day we observe the market.

## 12. Strategic Priority Rule

When choosing the next piece of work, use this order:

1. Does the live trading loop currently fail to select, monitor, alert, manage a position, or record an outcome?
2. Is a known truth defect capable of creating a false/missed opportunity or wrong position action?
3. Is the current strategy actually useful versus a simple control?
4. What uncertainty would most improve the next real decision?
5. Only then consider additional engineering structure.

This prevents process correctness from replacing product value while preserving the evidence discipline needed for capital decisions.
