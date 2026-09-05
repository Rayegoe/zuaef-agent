# 07 — Evidence Retrieval Layer

## Why

If Agent only sees the same 50 candidate scores that Quant already computed, it becomes a narrator rather than an investigator. But importing every feature of a securities app is unnecessary.

Use **targeted retrieval** after Quant narrows the problem.

## Priority 1 evidence

1. Market and sector breadth.
2. Exchange/company announcements.
3. Corporate actions and trading-status changes.
4. Current positions and cost basis.
5. Minute-level price/volume needed by active timing rules.

## Priority 2

- regulatory events;
- targeted current news;
- financing/margin or ETF/flow context when an experiment justifies it;
- sector/industry classifications and state.

## Defer by default

- Level-2/order-book depth;
- bulk sell-side research ingestion;
- community/social feeds;
- generic “money flow” metrics whose construction is opaque.

These should be added only when a specific hypothesis shows they can improve a measured bottleneck.

## Suggested tool surface

```text
get_price_history(symbol, start, end, as_of?)
get_intraday(symbol, date, interval, as_of?)
get_announcements(symbol, start, end, as_of?)
get_financials(symbol, period?, as_of?)
get_market_breadth(as_of)
get_sector_state(sector, as_of)
get_corporate_actions(symbol, start, end, as_of?)
get_regulatory_events(symbol, start, end, as_of?)
get_news(symbol_or_topic, start, end, as_of?)
get_position(symbol?)
```

## Retrieval invariants

- Historical/replay retrieval must accept and enforce `as_of`.
- Evidence returned to Agent includes source and availability timestamps.
- If provider data cannot honor historical availability, mark it non-PIT and exclude it from strict replay promotion evidence.
- Announcements begin as **risk/event filters**, not automatic alpha signals.
