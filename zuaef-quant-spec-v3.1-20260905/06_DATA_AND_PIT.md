# 06 — Data & PIT

Strict rule at decision time T:
`available_at <= T`.

Track where applicable:
event_time, source_time, available_at, ingested_at, decision_time, source, lineage, revision_state.

A report period is not an availability timestamp.
Unknown financial publication availability => strict replay blocks/excludes that factor.

An EOD bar cannot leak into an intraday replay.
Current index constituents cannot silently be projected backward in strict replay.

If historical membership cannot be reconstructed:
- use a genuinely frozen historical candidate/universe artifact; or
- mark the replay day PIT_BLOCKED/DEGRADED.

Never fall back to current `csi500_subset` research evaluator and call it production replay.

Trust dimensions stay separate:
coverage, freshness, semantic_integrity, source_integrity, pit_integrity, timing_integrity, runtime_availability.
