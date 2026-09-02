# 06 — Minimal Data Contracts

These are artifact shapes, not a new schema framework. Use plain dict/JSON and existing TOML helpers.

## 1. `candidate_snapshot.json`

```json
{
  "as_of": "2026-09-03T08:30:00+08:00",
  "base_universe": "csi300_plus_csi500",
  "base_count": 800,
  "eligible_count": 243,
  "candidate_count": 30,
  "coverage": 0.93,
  "sources": {
    "financial": "sina",
    "valuation": "baidu_or_cached_fallback",
    "quotes": "sina_or_tencent"
  },
  "candidates": [
    {
      "symbol": "000001",
      "name": "...",
      "industry": "...",
      "tier": "A",
      "composite_score": 78.4,
      "value_score": 32.1,
      "quality_score": 28.6,
      "tradeability_score": 11.2,
      "timing_score": 6.5,
      "metrics": {
        "pe_ttm": 7.1,
        "pb": 0.8,
        "dividend_yield_pct": 4.2,
        "roe_3y_pct": 11.4,
        "cfo_to_net_profit": 1.12,
        "debt_ratio_pct": 48.0,
        "valuation_percentile_3y": 0.23
      },
      "reasons": ["low valuation vs peers", "cash earnings quality acceptable"],
      "red_flags": [],
      "data_freshness": {
        "financial_date": "2026-06-30",
        "valuation_at": "2026-09-02"
      }
    }
  ]
}
```

## 2. `active_symbols.json`

```json
{
  "as_of": "...",
  "source": "candidate_snapshot",
  "symbols": ["..."],
  "count": 30
}
```

Live scanner only needs this bounded handoff.

## 3. Candidate coverage rules

Required business-page fields:
- base count;
- essential-data-covered count;
- candidate count;
- source failures.

Default fail-closed threshold:

```text
essential coverage < 80%
=> candidate snapshot status = DEGRADED
=> no A-tier completeness claim
```

The page may still display cached candidates, clearly timestamped.

## 4. No migration DB

Do not add SQLite for candidate ranking v1. JSON artifacts and current cache conventions are sufficient.
