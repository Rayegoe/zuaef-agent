# TASKS — Execution Backlog

## P0 — do first

- [ ] T000 Capture `BASELINE_RUNTIME.md`; no edits before this is complete.
- [ ] T001 Map running service/timer/entrypoints/state/report/Telegram bridge.
- [ ] T002 Add stable machine-readable runtime status projection.
- [ ] T003 Add explicit evidence namespaces: live-forward / replay / shadow / scratch.
- [ ] T004 Introduce replay clock / as-of read boundary at the narrowest viable seam.
- [ ] T005 Add PIT availability enforcement and future-data adversarial tests.
- [ ] T006 Replay the most recent 10 trading days at production-equivalent cadence.
- [ ] T007 Add replay settlement/report, with counters separated from live-forward.
- [ ] T008 Add Agent L0 read surface.
- [ ] T009 Add idempotent Agent L1 safe-control surface.
- [ ] T010 Regression-test existing live report + Telegram delivery path.

## P1 — after P0 acceptance

- [ ] T011 Add deterministic three-state Market Regime in shadow mode.
- [ ] T012 Add market/sector breadth evidence.
- [ ] T013 Add announcements and corporate-action evidence.
- [ ] T014 Verify/add current position and cost-basis evidence.
- [ ] T015 Verify/add minute price/volume evidence needed by current timing rules.
- [ ] T016 Add Experiment record/lifecycle.
- [ ] T017 Add S0 Scratch integration.
- [ ] T018 Connect S1 Replay to experiments.
- [ ] T019 Add S2 live Shadow decisions.
- [ ] T020 Run first controlled experiments: candidate count, one trigger threshold, regime gate, exit policy.

## P2 — explicitly deferred

- [ ] T021 Formal strategy promotion workflow after sufficient evidence.
- [ ] T022 Broker execution/reconciliation only under a separately approved external-effect scope.

Each task is complete only with tests + evidence, not merely code changes.
