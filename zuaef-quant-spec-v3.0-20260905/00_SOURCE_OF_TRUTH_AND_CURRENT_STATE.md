# 00 — Source of Truth & Current State

## Status labels

Every requirement in this pack must use one of these meanings:

- **CURRENTLY_OBSERVED** — directly supported by the latest operator/runtime report.
- **REPORTED_BASELINE** — behavior previously observed/discussed and believed present; Codex must verify against the running tree before relying on implementation details.
- **TARGET_V3** — new or strengthened behavior to implement.
- **EXPERIMENTAL** — may run only in sandbox/replay/shadow until promoted.
- **TO_VERIFY_RUNTIME** — unresolved implementation detail; never guess.

## CURRENTLY_OBSERVED — latest run

| Field | State |
|---|---|
| Report | `quant-business-20260904-1647.html` |
| Delivery | Telegram success, message ID `107` |
| Run | `a97d4047…` |
| Host/runtime | healthy |
| Decision | `NOT_RUN_TODAY` |
| Trigger count | `0` |
| Candidate count | `50` |
| Data trust | `FAIL` |
| PIT | contaminated / primary trust blocker |
| Coverage | `PASS` |
| Freshness | `WARN` |
| Semantic integrity | `PASS` |
| Source | `PASS` |
| Profitability | `UNPROVEN` |
| S3 | frozen |
| True trade records | `5` |
| Live forward observations | `0` |
| M1 evidence | `PARTIAL` |

### Interpretation

`NOT_RUN_TODAY + trigger_count=0` is **not** an outage. The host and delivery path are healthy. It means no currently eligible action was produced under the active rules/evidence state.

The system is therefore:

- operationally alive;
- capable of producing and delivering business reports;
- not yet allowed to claim trusted historical performance because PIT is contaminated;
- not yet allowed to claim live profitability because forward evidence is absent/insufficient.

## REPORTED_BASELINE — verify, do not re-invent

The current system has been described as approximately:

1. Universe near `CSI300 ∪ CSI500` (~800 names).
2. Hard exclusions such as risk-warning/ST, `PE <= 0`, insufficient liquidity, insufficient price history, and stale financial data.
3. Candidate scoring approximately `Value 40 + Quality 35 + Tradability 15 + Timing 10`.
4. Compression to roughly 50 candidates.
5. Live/latest observation and timing/trigger evaluation (`READY / NEAR / NO` or equivalent runtime vocabulary).
6. Deterministic trading gates and `NO_TRADE`/entry/exit decisions.
7. Position lifecycle and exit handling; the 5-day moving average has been used as an exit-oriented rule rather than as a universal selection rule.
8. Evidence/report rendering and Telegram delivery.
9. Previous engineering fixes discussed: trading-day alignment, volume-unit normalization/fail-closed behavior, cache schema/metadata migration checks, suspension valuation using last available close, initial-capital metric baseline, frontend/JSON escaping, lifecycle reset after acknowledged sell, and cleanup around exit evaluation.

Codex must inspect the actual runtime tree and retain any working implementation. Do not replace these merely because this spec uses more general names.

## TARGET_V3

The next milestone adds five capabilities **without pretending they already exist**:

1. **PIT-safe Replay Clock** and 10-day recent historical replay.
2. **Market Regime / Participation Gate** above stock-level signals.
3. **Agent Control Surface** for observe/control/decision-support actions.
4. **Evidence Retrieval Layer** for targeted external/context evidence.
5. **Sandbox + Code Experiment Loop** with immutable promotion rules.

## Conflict policy

If Git says one thing but the live report/runtime says another:

1. record the discrepancy;
2. preserve the live behavior;
3. patch the repository toward the runtime truth only after reproducing it;
4. never regress the running system merely to make it match stale Git.
