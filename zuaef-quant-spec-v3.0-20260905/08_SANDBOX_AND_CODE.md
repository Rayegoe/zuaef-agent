# 08 — Sandbox & Code Experiment Environment

## Principle

> **Experiment freely; preserve production truth; never rewrite evidence.**

Code access should be broader than real-money execution access.

## S0 — Scratch

Purpose: fast diagnosis and exploratory analysis.

Allowed:

- Python
- shell
- SQL (SQLite/DuckDB)
- temporary files
- data profiling
- plots/statistics
- disposable code

No production mutation.

## S1 — Replay

Purpose: reproduce past trading days with a frozen historical clock.

Requirements:

- full/compatible Quant runtime copy or isolated data/config surface;
- `decision_time = T` controls every historical read;
- network/provider reads after `T` are forbidden or sanitized;
- output namespace distinct from live forward;
- production cadence can be replayed intraday.

## S2 — Shadow

Purpose: current real-time market data, simulated actions.

Requirements:

- same observation/decision contracts as production where possible;
- no real broker external effects;
- immutable shadow decisions;
- later settlement against real outcomes.

## Agent + Code permissions

Allowed in sandbox:

- branch/diff code;
- run tests;
- vary parameters;
- replay/backtest/walk-forward;
- run sensitivity/ablation/counterfactual studies;
- generate reports;
- create a patch/work packet.

Forbidden:

- direct production strategy overwrite;
- delete/alter frozen evidence;
- rewrite historical observations after outcomes are known;
- deploy a parameter because “backtest got better” without promotion gates.

## Debugging loop

```text
Observe failure/anomaly
  ↓
Collect runtime state/logs
  ↓
Form hypotheses
  ↓
Reproduce in S0/S1
  ↓
Patch sandbox branch
  ↓
unit + integration + replay verification
  ↓
produce diff + evidence
  ↓
explicit promotion/release process
```

## Zero-trigger diagnostic experiment

If production has candidates but zero triggers for 10–15 trading days, Agent must test competing hypotheses rather than loosen production reflexively:

- true absence of opportunity;
- trigger threshold too strict;
- stale/freshness fail-close;
- PIT blocker;
- data/unit bug;
- regime mismatch.

Production remains frozen while variants are tested.
