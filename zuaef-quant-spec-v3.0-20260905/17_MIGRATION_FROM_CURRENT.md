# 17 — Migration From Current Runtime

## Strategy

Use an **additive strangler-style migration**, not a rewrite.

## Step 1 — Discover and map

Codex must first identify the currently running entrypoints, state directories, services/timers, report renderer, bridge, and candidate/live-monitor modules. Record exact runtime paths and versions in `BASELINE_RUNTIME.md` before changes.

## Step 2 — Add adapters

Wrap existing status/once/candidates/position/evidence behavior behind structured JSON/CLI/API adapters. Do not move core logic just to create architectural neatness.

## Step 3 — Add evidence namespaces

Create explicit mode/namespace separation:

- production/live-forward;
- replay;
- shadow;
- scratch/ephemeral.

Existing production records remain intact.

## Step 4 — Replay clock

Introduce a clock/data-access abstraction at the narrowest viable seam. Production continues to use wall/market time; S1 uses replay time.

## Step 5 — Market regime shadow

Add as a parallel projection. Do not wire it into production entry permission in the first release.

## Step 6 — Agent surface

Expose safe reads and idempotent controls. Keep shell internals private behind the adapter where practical.

## Step 7 — Experiments

Run on copied/isolated config/state. Promotion creates a new version; it never overwrites the active config in place.

## Rollback

Every P0/P1 capability needs a feature flag or independently removable adapter. If new Agent/replay functionality fails, the existing live loop/report/Telegram path must remain usable.
