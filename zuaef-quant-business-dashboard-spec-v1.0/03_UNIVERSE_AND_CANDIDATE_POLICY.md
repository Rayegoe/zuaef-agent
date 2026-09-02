# 03 — Universe and Candidate Policy

## 1. Universe taxonomy

### `legacy_watchlist`
Purpose: diagnose existing holdings / historical trapped positions.

Initial symbols are migrated from current `benchmarks/quant/gen1/universe.toml`.

New file:

```toml
# benchmarks/quant/gen1/legacy_watchlist.toml
schema = 1
name = "legacy_watchlist"
symbols = ["601233", "002460", "002415", "000009"]
```

These four names are never treated as “best opportunities” merely because the user owns them.

### `discovery_base`
Default v1:

```text
CSI300 ∪ CSI500
```

Why:
- much broader than four names;
- bounded versus all-A;
- generally liquid enough for small-capital execution;
- compatible with existing CSIndex/AKShare data direction.

If one index source fails, use last valid cached membership and mark freshness.

### `candidate_pool`
Target size:

```text
20–50 names
```

Generated off-hours/manual, not every 60 seconds.

### `action_candidates`
Existing live strategy filters `candidate_pool` and returns at most 10 deterministic triggers.

## 2. Candidate eligibility

Hard exclusions before scoring:
- ST / *ST / risk-warning name.
- Missing or stale essential valuation/financial fields beyond configured freshness budget.
- Non-positive latest price.
- Insufficient daily history for timing calculation.
- Latest reported earnings <= 0 for standard industrial companies.
- Clearly unusable liquidity (v1 threshold stored in policy, not code).

Financial-sector exception:
- banks / brokers / insurers should not be rejected by industrial leverage/CFO rules;
- use sector-aware fields and show `sector_model=financial`.

## 3. Ranking philosophy

Do not build a hidden “magic AI score”.

Every rank must expose:
- raw metrics;
- normalized percentile/rank;
- missing fields;
- red flags;
- score reasons.

Industry-relative ranking is preferred for PE/PB/ROE where cross-industry comparison is misleading.

## 4. Sector concentration guard

Top candidate list must not become a disguised single-sector bet.

Default:

```text
max 4 names per first-level industry in top 30
```

If industry data is unavailable, do not fake diversification; mark concentration status `unknown`.

## 5. Candidate persistence

Generated artifacts:

```text
workspace/artifacts/quant/business/candidate_snapshot.json
data/quant-cache/candidates/active_symbols.json
```

`candidate_snapshot.json` is auditable evidence.
`active_symbols.json` is the small runtime handoff consumed by live scan.
