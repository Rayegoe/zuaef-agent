# WP3 — Market Regime / Participation Gate (Shadow)

## Goal
Compute `DO_NOT_PARTICIPATE / SELECTIVE / NORMAL` using small, auditable market-state inputs.

## Tasks
- define deterministic rule version 0.1;
- add breadth/volatility/liquidity inputs with as-of timestamps;
- emit reasons and snapshot/version IDs;
- run recent PIT-safe replay;
- run live shadow projection;
- compare with production outcomes.

## Constraint
Must not block or alter production entries in first release.
