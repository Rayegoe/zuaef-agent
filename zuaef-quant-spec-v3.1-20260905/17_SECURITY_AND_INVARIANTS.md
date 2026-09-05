# 17 — Security & Integrity Invariants

1. Frozen evidence is append-only/versioned.
2. Replay/shadow/scratch cannot write production evidence.
3. Strict replay enforces availability time.
4. Experiments cannot mutate active production config.
5. Deterministic runtime is final permission authority.
6. Real broker effects are outside v3.1.
7. Workbench write API stays loopback-only.
8. Bridge is the single proactive Quant Telegram delivery authority.
9. Bridge-triggered Agent runs cannot independently deliver the same event.
10. Delivery retry cannot duplicate trading evidence.
11. `market_no_trade` keeps its existing meaning; it is not Regime.
12. HUMAN_SKIP is a human fact, never a synthetic fill.
13. research/replay/shadow/live_forward cannot be relabeled across boundaries.
14. No feature accretion without a concrete decision/research hypothesis.
15. No new model-visible quant tool without a gap audit.
