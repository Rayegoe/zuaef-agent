# Implementation Plan

Each phase must end in a usable proof, not a class hierarchy.

## U0 — Upstream compatibility refresh

Goal: align with current Pydantic capability primitives without rewriting ZUAEF.

Actions:
- record local HEAD + dirty status;
- validate target baseline Pydantic AI 2.35.3 + Harness 0.27.x;
- run existing full regression;
- update context controls to window-relative settings if regression-proven;
- confirm CodeMode metadata selector compatibility;
- update upstream baseline record;
- minor-bound Harness after validation.

Stop if upgrade requires broad unrelated architecture changes. Isolate/report instead of rewriting Core.

## P0 — Real-data proof

Deliver:
- AKShare history;
- current snapshot;
- cache;
- timestamp/latency/freshness output.

No Agent.

## P1 — One real strategy

Deliver:
- minimal StrategySpec;
- fixed price/volume baseline;
- Qlib/vector evaluation;
- trades and after-cost metrics.

No evolution.

## P2 — Independent replay

Deliver:
- frozen signals/trade intents;
- independent event replay;
- A-share execution constraints;
- cross-engine comparison.

## P3 — QuantDecision capability

Only after evaluator works:
- create `zuaef-quant` plugin;
- lightweight `QuantDecision Capability(...)`;
- QuantToolset;
- profile;
- one real Agent run writing Strategy Result.

No Core business changes.

## P4 — 3-run evolution

Fresh S1→S2→S3, one material mutation per child when possible, comparative evidence and clear receipts/artifacts.

No 100-run loop.

## P5 — Live/near-live Decision Brief

Deliver:
- active-strategy deterministic scanner;
- current snapshot;
- compact context;
- Decision Brief;
- measured freshness.

Start interactively. Add watcher only when needed.

## P6 — Paper/shadow

Deliver paper settlement, daily review, sim-vs-paper comparison and restraint when samples are insufficient.

## P7 — Manual small-capital real feedback

Deliver manual outcome recording, sim/paper/real comparison and next reflection using real evidence.

No automatic broker API.

## Post-MVP expansion rule

Only after a measured failure/need:
- faster paid/broker feed;
- SQLite index;
- additional universes;
- intraday strategies;
- richer sizing;
- news/fundamental capability;
- broker integration;
- subagents/workflow.

Every expansion must name the observed problem it solves.
