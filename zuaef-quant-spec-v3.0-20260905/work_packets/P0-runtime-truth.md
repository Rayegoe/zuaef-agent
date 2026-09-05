# WP0 — Runtime Truth & Structured Status

## Goal
Expose current working state to Agent/Code without changing production strategy behavior.

## Tasks
1. Create `BASELINE_RUNTIME.md` before edits.
2. Map existing status/once/candidate/monitor/evidence/report/bridge paths.
3. Add a stable JSON status projection conforming approximately to `schemas/quant_status.schema.json`.
4. Include candidate/trigger counts, decision, host health, trust dimensions, profitability/evidence counts, mode, versions.
5. Add tests proving zero-trigger is not reported as runtime outage.

## Acceptance
- Current latest behavior can be represented without semantic loss.
- Existing CLI/report path still works.
- No strategy/config/risk rule change.
