# 12 — Experiment System

Do not rebuild the evaluator.

Existing `evaluate_strategy` and P0.5 dual-engine reconciliation are research infrastructure.
v3.1 adds governance/orchestration around them.

Lifecycle:
PROPOSED
-> S0_DIAGNOSIS
-> RESEARCH_EVAL and/or S1_REPLAY
-> REJECTED or REPLAY_PASS
-> S2_SHADOW
-> LIVE_FORWARD_EVAL
-> PROMOTED / REJECTED

Experiment record:
experiment_id, pre-stated hypothesis, baseline version, exact one-variable change,
mechanism, evidence namespace, data window, primary metric, risk metric,
rejection condition, run IDs, result, limitations, promotion state.

First families:
- Top 30 vs 50 vs 80;
- one trigger threshold at a time;
- Market Regime;
- exit policy with entry fixed;
- HUMAN_SKIP value analysis.

Forbidden:
bad result -> tune same sample -> good result -> production.

Required:
problem -> hypothesis -> isolated change -> replay/walk-forward -> shadow ->
new live-forward evidence -> promotion/rejection.
