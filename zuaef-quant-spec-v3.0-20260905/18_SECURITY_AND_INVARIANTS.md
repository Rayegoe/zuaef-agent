# 18 — Security, Integrity & Non-Negotiable Invariants

1. **Evidence immutability:** frozen observations/decisions/settlements are append-only or otherwise tamper-evident through storage/version controls.
2. **Mode isolation:** replay/shadow/scratch cannot write production evidence or brokerage effects.
3. **No silent future data:** strict replay reads enforce `available_at <= decision_time`.
4. **No silent strategy mutation:** experiments cannot alter active production config.
5. **Deterministic risk authority:** LLM cannot bypass hard gates.
6. **External-effect boundary:** real orders/cancels require explicit external-effect authorization.
7. **Idempotency:** retries of control/delivery cannot duplicate state-changing actions.
8. **Traceability:** every decision is attributable to strategy version, data snapshot/clock, and gate reasons.
9. **Fail closed:** unknown critical data/risk state prevents new capital exposure.
10. **Dashboard is not truth:** presentation failure cannot overwrite/redefine runtime/evidence state.
11. **No evidence laundering:** contaminated historical/backtest/replay results cannot be relabeled as live forward.
12. **No feature accretion without hypothesis:** Level-2/news/research/community integrations require a defined decision/research use case.
