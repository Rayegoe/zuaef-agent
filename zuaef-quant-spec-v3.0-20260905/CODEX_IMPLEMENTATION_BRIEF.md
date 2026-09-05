# Codex Implementation Brief

## Mission

Extend the **currently running** ZUAEF Quant system into a live decision + PIT-safe replay + Agent experiment platform **without regressing the working runtime/Telegram pipeline and without treating stale Git as the sole truth**.

## Mandatory first action — baseline, no edits

1. Inspect current working tree, branch, `git status`, last local commit and `origin/main`.
2. Inspect running user/system services, timers and recent Quant/bridge logs.
3. Identify exact current commands/modules for status, once/live monitor, candidate generation, positions/exit, evidence/settlement, report rendering and Telegram delivery.
4. Capture current successful behavior and the latest runtime report if present.
5. Write `BASELINE_RUNTIME.md` using the labels from this pack.
6. **Do not reset, clean, checkout, stash, merge or overwrite uncommitted runtime work.**

## Work order

### WP0 — Preserve runtime truth

- add/verify machine-readable status snapshot;
- include mode, strategy version, trust dimensions, trigger/candidate counts, forward/replay counts, host health;
- no strategy behavior change.

### WP1 — PIT-safe replay foundation

- introduce replay clock / as-of data access seam;
- enforce `available_at <= decision_time`;
- create separate replay evidence namespace;
- add leakage adversarial tests;
- replay recent 10 trading days at production-equivalent intraday cadence.

### WP2 — Agent action surface

- structured read actions first;
- idempotent safe controls next;
- explicit reason/error taxonomy;
- no broker effects.

### WP3 — Market Regime shadow

- deterministic three-state participation gate;
- reason codes and versioned inputs;
- shadow-only, not production-blocking yet.

### WP4 — Evidence Retrieval v1

- breadth;
- announcements;
- corporate actions;
- current positions/cost basis;
- required minute-level price/volume.

Historical mode must honor as-of availability or label evidence non-PIT.

### WP5 — Experiment Manager + S0/S1/S2

- immutable hypothesis/variant/run/result records;
- sandbox config isolation;
- replay and live-shadow execution;
- promotion/rejection state machine.

## Engineering constraints

- Reuse existing paths/modules/contracts wherever they already solve the job.
- Prefer adapters over rewrites.
- New features are feature-flagged or shadow-only until validated.
- Tests must prove namespace isolation and future-data blocking.
- Do not widen scope into a broker terminal.
- Do not add a database/framework solely for architectural aesthetics; use the smallest durable mechanism compatible with current runtime.
- Do not silently normalize trust failures into warnings.

## Completion evidence

At the end provide:

1. changed file list and why;
2. exact commands run;
3. test results;
4. 10-day replay summary;
5. proof replay count does not alter live-forward count;
6. proof a future-data adversarial test is blocked;
7. proof current live report/Telegram path still works or, if market closed, its smoke-equivalent path;
8. known limitations;
9. next promotion decision, not just “done”.
