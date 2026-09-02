# Data and A-Share Market Truth

## 1. Data principle

The MVP must touch real public market data before Agent integration.

Primary source: **AKShare**.

AKShare is an external public-data interface, not an exchange-grade market-data SLA. Measure freshness and failure rather than assuming "real time".

## 2. P0 real-data smoke

Implement a small command proving:
- one stock's real daily OHLCV loads;
- CSI 500/index constituent-related data loads;
- a current A-share market snapshot loads;
- returned timestamps are surfaced;
- request latency is measured;
- row/symbol counts are surfaced;
- errors are not silently replaced with stale data.

Example output:

```text
historical_rows=...
latest_history_date=...
snapshot_symbols=...
snapshot_timestamp=...
request_ms=...
freshness=...
```

## 3. Local cache

Historical data should be cached after successful acquisition.

Minimum metadata:
- source;
- retrieval timestamp;
- date/symbol range;
- enough raw/normalized data to reproduce the strategy run.

Do not build a cache framework. Explicit/daily refresh is sufficient first.

## 4. Qlib ingestion

Qlib is the fast research kernel.

Preferred order:
1. use public Qlib 0.9.7 data/Parquet/DataHandler mechanisms;
2. write only the adapter necessary to make normalized AKShare data consumable;
3. do not build a generic data lake/provider registry.

The first proof may use a bounded CSI 500 subset/date range, then scale only after correctness works.

## 5. Survivorship / historical universe

Do not silently use today's CSI 500 membership for all historical dates and describe it as unbiased historical CSI 500 performance.

Priority:
1. reconstruct point-in-time membership when reliable data is available;
2. otherwise use a documented bounded alternative;
3. record the limitation in every affected Strategy Result.

No `HistoricalUniversePlatform` in v1.

## 6. Tradable MVP universe

Start with a normal tradable CSI 500 subset.

Exclude where reliable status data permits:
- ST/risk-warning names;
- suspended names;
- delisting/abnormal names;
- names without enough lookback;
- instruments whose required execution/trade-status facts cannot be reconstructed.

This is scope reduction, not denial of market complexity.

## 7. Minimum A-share execution truth

Replay must cover failure modes that can manufacture fake alpha:
- T+1 ordinary-share sell constraint;
- suspension/no trade;
- board-specific price-limit behavior;
- limit-up buy / limit-down sell non-fill;
- order quantity/lot rules for the supported universe;
- commission;
- minimum commission where configured;
- sell-side stamp duty;
- slippage;
- signal/execution timing.

Rules must be effective-dated when history changed.

Do not scatter timeless constants such as `LIMIT=0.10`, `LOT=100`, `STAMP=...` through Python. Use one small frozen rules/config source plus deterministic helpers.

## 8. Corporate actions

Research prices may use adjusted series. Replay execution must use raw or reconstructable executable prices plus appropriate corporate-action handling.

Never trade on an adjusted synthetic price.

## 9. Live data

The initial objective is near-real decision assistance, not HFT.

Initial behavior:
- default polling around 60 seconds;
- reduce interval only after measuring AKShare freshness/stability;
- deterministic scan first;
- invoke LLM only on triggers or explicit user request.

If AKShare proves too stale/unreliable, replace the small market-data implementation. Do not redesign Agent/Core.

## 10. Data honesty

If a strategy requires a fact that cannot be reconstructed reliably, return an explicit limitation or invalid result.

Never fabricate point-in-time membership, suspension state, execution price or other missing facts to keep a pipeline green.
