# Final Execution Plan

This plan has one product loop and one sequential research/assurance spine.

The research spine remains P0→P6. **Do not interpret that as permission to postpone real-market operation until P6.** Live observation and forward collection begin as soon as the relevant truth gate allows them.

## Continuous Business Operating Thread

Throughout implementation, maintain the smallest real-market loop possible:

```text
real market
→ active watch universe
→ intraday monitor
→ material alert/state change
→ user-confirmed/paper position when applicable
→ position monitor
→ forward outcome
```

During early truth work this may operate in observation-only mode. It must still use real market inputs; fixtures stay in tests.

The operating thread exists to reveal whether the project is becoming useful and to generate forward evidence that cannot be reconstructed later.

---

## P0 — TRUST THE INSTRUMENTS

Question: are live/historical facts and temporal semantics trustworthy enough to observe the market?

- volume semantic truth;
- coverage/freshness/source separation;
- PIT status;
- anti-leak behavior;
- timing alignment;
- independent execution/accounting truth where required.

**Product obligation during P0:** keep a real observation loop alive when safe. A trust failure must stop actionable alerts, not stop all product learning.

**Exit:** known truth failures are either fixed or explicitly blocking; anti-leak scope is honest; live observation cannot silently turn unavailable data into `NO_TRADE`.

## P1 — TRUST THE BACKTEST / REPLAY

Question: is historical performance a usable comparator rather than an execution/accounting illusion?

- Qlib vs independent replay reconciliation;
- corporate-action handling or explicit exclusion where material;
- net costs;
- PIT-clean/qualified research dataset for the claims being made;
- OOS lock;
- trial/search lineage.

**Product obligation by P1 exit:** the live loop should be able to produce a small watch universe, monitor it at a practical minute-level cadence, surface material opportunity transitions, accept a user-confirmed/paper position and monitor that position to closure.

This is the minimum operational Trading Assistant v0.1. If this cannot run, P1 is not a product milestone regardless of backtest quality.

## P2 — FIND WHAT ACTUALLY HELPS SELECTION/TIMING

Question: do candidate score and S3 components improve real opportunity quality?

- factor IC/RankIC/quantile;
- A0–A7 controls;
- simple matched/random/liquidity baselines;
- exit attribution;
- forward selected-vs-control observation as it accumulates.

**Exit:** Causal Research Review identifies what contributes, what does not, and what remains unknown. Weak components are simplified/demoted instead of defended.

## P3 — TEST ROBUSTNESS AND CONTEXT

Question: is the result stable, or is it conditional on market/sector/context/search luck?

- walk-forward;
- bull/bear/sideways;
- high/low volatility and liquidity;
- market/sector/relative-price context probes;
- search-adjusted warning;
- DSR/PBO only when meaningful;
- untouched OOS.

Context conditioning begins here as a research hypothesis, not a prebuilt architecture.

**Exit:** we know where the mechanism appears to work, where it fails, and how much of that statement survives OOS.

## P4 — MAKE AGENT A REAL RESEARCHER

Question: can the Agent turn real failures/outcomes into better research questions?

- Research Log / Lessons / Open Questions;
- recall;
- Agent chooses uncertainty;
- bounded hypothesis;
- isolated experiment implementation if needed;
- deterministic evaluation;
- contradiction/next question.

**Exit:** at least one non-preenumerated Agent-led research run materially updates a Lesson or strategy priority.

## P5 — REPLAY EVERY MATERIAL DECISION

Question: can we reconstruct enough of a past opportunity/position decision to learn from it?

- immutable real observations/reports;
- actual strategy/input references;
- Agent decision context;
- position/action timeline;
- stale/unavailable status;
- later forward outcome linkage.

Do not make report machinery more important than the decision itself.

**Exit:** a sampled historical decision can be reconstructed sufficiently to answer what was known, what was decided, what action occurred and what happened later.

## P6 — FORMAL FORWARD LEARNING

Forward collection has already been running. P6 formalizes the learning loop:

- D+1/3/5/8;
- MFE/MAE;
- realized/manual/paper exit and net outcome;
- selected-vs-control comparison;
- review packet;
- Lesson update;
- CONTINUE / ADJUST / RETIRE.

**Exit:** at least one real forward outcome changes a Lesson, trading rule priority or research question.

## Freeze Rule

Freeze architecture when the system can continuously:

`select -> monitor -> alert -> manage -> observe -> learn`

and the research spine is trustworthy enough for the claims being made.

After that, default mode is operating and learning. Reopen engineering only on real data, strategy, monitoring, position-management, Agent or operational failure.
