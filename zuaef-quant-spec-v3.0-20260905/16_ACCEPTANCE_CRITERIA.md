# 16 — Acceptance Criteria

## Release v3 foundation — required

### A. No regression of current production

- latest working live/host/report/Telegram path continues to operate;
- market-closed path does not produce fake events;
- existing deterministic gates retain behavior unless a separately approved production change says otherwise.

### B. Machine-readable control surface

- Agent can query status/candidates/decisions/positions/observations;
- Agent can invoke safe control actions with explicit mode and idempotency;
- all results identify strategy/runtime mode and reason codes.

### C. PIT-safe replay

- 10 recent trading days replayed where data permits;
- intraday time boundary enforced;
- adversarial future-data test passes;
- replay and live-forward evidence are impossible to confuse programmatically.

### D. Experiment isolation

- production config/evidence cannot be mutated by S0/S1/S2;
- variant changes are explicit and reviewable;
- experiment outcome has an immutable lifecycle.

### E. Market regime shadow

- deterministic 3-state output exists;
- output has reason codes/as-of/version;
- no effect on production orders/decisions until separately promoted.

### F. Evidence/report transparency

Dashboard/report explicitly distinguish:

- host/runtime health;
- data trust/PIT;
- production trigger/decision;
- replay results;
- live forward results;
- experiments/shadow results.

## M1 evidence gate

First formal audit at 20 trading days or 30 settled forward triggers, whichever first, with no unresolved evidence-pipeline integrity failure.

## Non-acceptance examples

The project is **not** accepted merely because:

- HTML got more pages;
- more indicators were added;
- replay generated many trades by relaxing rules;
- an LLM produced a convincing explanation;
- backtest CAGR improved on the same tuned sample.
