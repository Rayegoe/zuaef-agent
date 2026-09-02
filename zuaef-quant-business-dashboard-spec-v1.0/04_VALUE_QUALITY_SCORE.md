# 04 — Value / Quality / Tradeability Score

## 1. Objective

Find **cheap enough + financially credible + tradeable** companies; do not confuse “low PE” with “good value”.

## 2. Composite

Default v1 score:

```text
Value         40
Quality       35
Tradeability  15
Timing        10
--------------
Total        100
```

Timing contributes only to ranking/attention. A real trade action still requires the existing deterministic live trigger.

## 3. Value — 40 points

Recommended components:

| Metric | Weight | Interpretation |
|---|---:|---|
| Industry-relative PE(TTM) percentile | 15 | cheaper than peers, positive earnings only |
| Industry-relative PB percentile | 10 | useful especially with ROE context |
| Own 3Y valuation-history percentile | 10 | “cheap versus itself” |
| Dividend yield / shareholder return | 5 | prefer persistent cash return, not one-off payout |

Negative PE is not “very cheap”; it is missing/invalid for PE scoring.

## 4. Quality — 35 points

| Metric | Weight | Interpretation |
|---|---:|---|
| 3Y average ROE / sector-relative ROE | 10 | capital efficiency |
| Operating cash flow / net profit | 10 | earnings quality |
| Revenue + profit stability/growth | 10 | avoid melting-ice-cube value traps |
| Balance-sheet safety | 5 | industry-aware leverage / solvency |

For financial companies, replace industrial cash-flow/leverage logic with sector-appropriate ROE/PB/dividend/capital-quality metrics available from the data source. If unavailable, downgrade coverage; do not fabricate.

## 5. Tradeability — 15 points

| Metric | Weight |
|---|---:|
| recent turnover amount / liquidity | 10 |
| sufficient price history / normal quote availability | 5 |

This score is not a momentum score; it answers whether a small account can realistically enter/exit.

## 6. Timing — 10 points

Derived from existing S3-compatible fields:
- 5-day pullback;
- 20-day volume ratio;
- close/price strength.

A stock can rank high fundamentally but remain `WAIT_TIMING`.

## 7. Red flags

Red flags do not silently disappear into the composite number.

Examples:
- `NEGATIVE_EARNINGS`
- `CFO_BELOW_NET_PROFIT_PERSISTENT`
- `HIGH_LEVERAGE_REL_SECTOR`
- `ROE_DETERIORATION`
- `PROFIT_GROWTH_NEGATIVE`
- `VALUATION_DATA_STALE`
- `FINANCIAL_DATA_STALE`
- `INSUFFICIENT_HISTORY`
- `LOW_LIQUIDITY`
- `SOURCE_DEGRADED`

The dashboard must show red flags as text/chips.

## 8. Tiers

Suggested presentation bands:

```text
A  >= 75  and no critical red flag
B  60–74
C  50–59
DROP < 50 or failed eligibility
```

These are ranking bands, not buy ratings.

## 9. Data sources

Use current AKShare interfaces where available, with caching and provenance. Relevant capabilities documented by AKShare include:
- `stock_financial_analysis_indicator` — financial indicators;
- `stock_zh_valuation_comparison_em` — peer valuation comparison;
- `stock_zh_dupont_comparison_em` — peer ROE/DuPont comparison;
- `stock_zh_valuation_baidu` — PE/PB/cash-flow valuation history;
- `stock_value_em` — historical PE/PB/PEG/PS/PCF;
- `stock_individual_spot_xq` — current PE/PB/dividend/market fields;
- `stock_zh_a_spot` — broad Sina quote/turnover snapshot.

Because EastMoney has already failed from one deployment network, every source path must expose:

```text
source
retrieved_at
freshness
fallback_used
coverage
```

No single EastMoney-only API may become a mandatory runtime dependency for the business dashboard.
