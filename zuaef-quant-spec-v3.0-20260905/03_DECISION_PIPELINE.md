# 03 — Decision Pipeline

## Baseline flow

```text
Universe (~800, verify runtime)
  ↓
Hard eligibility filters
  ↓
Candidate scoring/ranking
  ↓
Top-N attention pool (~50 current)
  ↓
Market participation gate          [TARGET_V3]
  ↓
Live timing/trigger evaluation
  ↓
Evidence/risk gates
  ↓
Decision: BUY / NO_BUY / HOLD / EXIT / NO_TRADE
  ↓
Freeze observation + decision
  ↓
Future settlement (+1d/+3d/+5d/exit, MFE/MAE, costs)
  ↓
Evidence update + degradation analysis
```

## Separation of concerns

### Candidate generation

Purpose: reduce the search space. A candidate is **not** a trade signal.

The current score weighting is a `REPORTED_BASELINE`, not a constitutional rule. Keep the active production weights frozen under a versioned config. Weight changes belong in experiments.

### Participation gate

Purpose: determine whether the market environment permits normal participation, selective participation, or no participation.

This gate is evaluated **before** individual-stock permission. See `05_MARKET_REGIME.md`.

### Trigger

Purpose: answer whether the timing evidence is currently sufficient. Trigger vocabulary should map cleanly to:

- `READY`: timing requirement met;
- `NEAR`: close but not permitted;
- `NO`: no actionable timing evidence.

Do not convert `NEAR` into an order merely because an LLM likes the setup.

### Deterministic decision gates

Recommended minimum live-entry gate set:

```text
market_regime != DO_NOT_PARTICIPATE
critical_data_trust == PASS
critical_freshness == PASS
trigger == READY
position_limit == PASS
risk_budget == PASS
symbol_trade_status == PASS
```

If any required gate fails, decision is `NO_BUY` or `NO_TRADE` with machine-readable reasons.

### Exit

Exit logic is independently testable. Do not assume entry optimization and exit optimization should change together. Candidate experiments include fixed stop, trailing stop, time stop, MA exit, volatility stop, and regime-deterioration exit.

## Abstention is a first-class result

`NOT_RUN_TODAY`, `NO_TRADE`, or zero triggers are valid business outcomes when the evidence says not to participate. The system must distinguish:

- no opportunity;
- market closed;
- critical evidence unavailable;
- data stale;
- runtime failure;
- trading disabled;
- strategy gate rejected.
