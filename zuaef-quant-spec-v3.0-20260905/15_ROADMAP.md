# 15 — Roadmap

## P0 — Preserve truth + unlock fast evidence

### P0.1 Runtime truth snapshot

Expose machine-readable current status and version identifiers without changing strategy behavior.

### P0.2 PIT-safe replay foundation

Implement replay clock, availability gate, namespace separation, and adversarial tests.

### P0.3 Recent 10-day replay

Run the current production strategy/config through recent PIT-safe intraday replay; produce a report separate from live forward.

### P0.4 Agent L0/L1 action surface

Structured observe/control tools: status, once, attention, candidates, decisions, positions, observations, settle, replay.

**P0 outcome:** Agent can safely inspect/control the loop and we can diagnose trigger behavior without waiting weeks.

## P1 — Decision quality + research loop

### P1.1 Market Regime shadow gate

Three-state deterministic participation gate, shadow-only first.

### P1.2 Evidence Retrieval v1

Breadth, announcements, corporate actions, positions/cost, intraday data.

### P1.3 Experiment Manager

Hypothesis/variant/run/result/promotion records with S0/S1/S2 separation.

### P1.4 Shadow experiments

At minimum candidate-count, trigger-sensitivity, regime, and exit experiments.

**P1 outcome:** Agent becomes an investigator/researcher, not merely a reporter.

## P2 — Evidence-based promotion and optional execution integration

- live-forward degradation metrics;
- strategy promotion/rejection workflow;
- broker execution contract/reconciliation only if evidence gate is met;
- emergency/kill-switch and external-effect authorization.

## Explicitly defer

- broad broker-app feature parity;
- Level-2;
- social/community;
- large sell-side research corpus;
- autonomous production strategy self-modification.
