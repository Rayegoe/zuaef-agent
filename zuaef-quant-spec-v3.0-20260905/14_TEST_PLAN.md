# 14 — Test Plan

## Unit tests

- PIT availability predicate boundaries;
- daily/minute bar completion rules;
- trust aggregation and criticality;
- regime state transitions;
- gate reason-code stability;
- experiment state machine;
- evidence namespace separation;
- idempotency keys.

## Integration tests

- `once` when market closed returns a non-action state and creates no fake trigger;
- candidate → trigger → decision → observation → settlement;
- report renders from structured state;
- Telegram retry does not duplicate decision;
- Agent read/control calls do not bypass gates;
- sandbox never writes production evidence/config.

## Replay adversarial tests

1. Future announcement timestamp injected → replay must block it.
2. EOD daily bar queried at 10:30 → unavailable.
3. Future/current index membership projected backward → detected or blocked.
4. Provider row revised after T → run marked degraded unless historical version is available.
5. Randomized future values changed → decisions before T remain byte/semantically identical.

## Data integrity tests

- price/volume units;
- duplicate bars;
- missing trading days;
- date/timezone alignment;
- cache metadata vs rows/date range;
- stale data fail-closed;
- corporate action adjustment consistency;
- suspension valuation behavior.

## Experiment tests

- variant cannot mutate baseline config;
- experiment records predate outcome evaluation;
- promotion requires declared gates;
- rejected experiment remains queryable;
- identical run seed/input/config is reproducible where deterministic.

## Runtime smoke

- status
- once
- candidates
- observations
- settle
- report generation
- Telegram bridge
- replay dry-run
- shadow experiment dry-run
