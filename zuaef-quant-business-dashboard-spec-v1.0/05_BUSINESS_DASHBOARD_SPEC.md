# 05 — Quant Business Dashboard Specification

## 1. Page identity

Title:

```text
ZUAEF Quant Decision Dashboard
```

Subtitle:

```text
Market opportunities, candidate evidence, live timing, and forward results.
```

Do NOT lead with `ENGINEERING FREEZE`, `U0`, `P5.5`, `Harness`, or test counts.

## 2. First viewport — decision first

Top KPI strip:

1. **Today Decision** — latest Agent action or `NOT_RUN_TODAY`.
2. **Live Triggers** — `n`.
3. **Active Candidates** — candidate pool size.
4. **Forward Settled Trades** — count.
5. **Strategy Evidence** — `UNPROVEN / WEAK / FORWARD_BUILDING / ...`.

Primary warning beneath:

```text
Historical S3 evidence is weak; Profitability Proof is NOT YET.
```

## 3. Section: Today’s Action Candidates

If triggers exist, table columns:
- symbol / name;
- industry;
- price;
- value score;
- quality score;
- composite score;
- 5d pullback;
- 20d volume ratio;
- trigger time;
- Agent action if a brief exists;
- invalidation / main risk.

If no triggers:

```text
NO ACTION CANDIDATE
No eligible stock currently meets the deterministic timing rule.
```

Do not fill the space with forced recommendations.

## 4. Section: Value / Quality Opportunity Board

Show top 20–30 candidate stocks even when there is no timing trigger.

Columns:
- Rank
- Symbol / Name
- Industry
- Tier
- Composite
- Value
- Quality
- Tradeability
- PE(TTM)
- PB
- Dividend Yield
- ROE
- Valuation percentile
- Timing state: `WAIT / NEAR / TRIGGER`
- Top 1–2 reasons
- Red flags

Interactions can remain simple client-side sort/filter. No frontend framework.

## 5. Section: Legacy Holdings / Trapped Positions

The four user watchlist stocks appear here, not as the default opportunity universe.

For each:
- latest price;
- same value/quality score used for new candidates;
- whether it would independently qualify for candidate pool;
- current timing state;
- `LEGACY_ONLY` if it fails discovery policy;
- primary fundamental weakness / red flag;
- no emotional “cost basis recovery” framing.

Critical question displayed:

> “If you did not already own this stock, would it enter today’s candidate pool?”

## 6. Section: Strategy Evidence

This replaces “model evolution” as the main quant evidence card.

Show:

```text
Status                 UNPROVEN
Best historical annualized   ~0.37%
Historical trades             29
PIT/member bias               YES
Forward triggers              n
Forward settled trades        n
Forward hit rate              only after enough observations
```

Baseline/S1/S2/S3 comparison remains available in a collapsible detail.

Rename:

```text
模型进化 -> 策略实验历史
```

## 7. Section: Forward Evidence

Show only real forward observations:
- date/time;
- candidate universe size;
- trigger count;
- action;
- entry if manually executed;
- +1/+3/+5/+8 day path where available;
- MFE / MAE where available;
- settlement status.

No synthetic placeholder trades.

## 8. Section: Data Quality

Expose:
- candidate snapshot timestamp;
- quote timestamp;
- financial statement freshness;
- valuation source;
- coverage `%`;
- degraded sources;
- missing fields.

If coverage is below the configured acceptance threshold, show a visible `DATA DEGRADED` banner and refuse to present A-tier rankings as complete.

## 9. Engineering link

Bottom/right navigation:

```text
Engineering / Audit Details → /engineering
```

The audit dashboard remains accessible but no longer dominates the operator flow.
