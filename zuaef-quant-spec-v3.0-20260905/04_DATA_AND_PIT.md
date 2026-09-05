# 04 — Data & Point-In-Time Integrity

## Definition

**PIT (Point-In-Time)** means: at decision time `T`, the strategy may only consume facts actually available at or before `T`.

The fundamental rule is:

```text
available_at <= decision_time
```

Not:

```text
report_period <= decision_time
```

Example: a 2025-12-31 annual report published on 2026-04-30 is unavailable to a 2026-03-01 decision.

## Why current trust fails

The latest runtime report marks overall data trust `FAIL`, with PIT contamination as the primary blocker. The system should treat this as a **validation problem, not a host/runtime outage**.

## Required time fields

Every evidence item used in historical/replay decisions should carry, where applicable:

- `event_time` — time the economic/market event happened;
- `source_time` — provider/announcement timestamp if supplied;
- `available_at` — earliest time the strategy is allowed to use it;
- `ingested_at` — when our system obtained it;
- `decision_time` — replay/live decision clock;
- `source_id` and lineage metadata.

For bars, `available_at` must reflect when that bar is complete/observable under the production cadence. Never let a 15:00 daily bar leak into a 10:30 replay.

## Unknown availability policy

For **strict replay/live trading evidence**:

- if `available_at` is required and unknown → `INSUFFICIENT_EVIDENCE` / fail closed;
- do not silently substitute report period/date;
- an optional research-only mode may use approximations but must be labeled `CONTAMINATED` or `NON_PIT` and excluded from promotion evidence.

## Historical membership and survivorship

If universe composition is part of historical/replay validation, use membership valid at `decision_time`. Current index constituents cannot be blindly projected backward.

## Corporate actions

Price/volume adjustments and corporate actions must be explicit and versioned. Replay should be able to state:

- raw price source;
- adjustment method;
- corporate-action records used;
- whether a later revision was required.

## Data trust dimensions

Machine-readable trust should include at least:

- `coverage`
- `freshness`
- `semantic_integrity`
- `source_integrity`
- `pit_integrity`
- `timing_integrity`

A composite status must not hide a failed critical dimension.

## Critical live rule

A production trade permission may use a stricter subset than research. For example, an old fundamental factor could remain informational while fresh price/trading status/risk data must be `PASS`. The schema must make criticality explicit rather than treating every warning identically.
