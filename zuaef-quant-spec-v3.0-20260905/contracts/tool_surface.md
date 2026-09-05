# Agent Tool Surface

## Quant tools

- `quant_status()`
- `quant_attention()`
- `quant_candidates(limit?)`
- `quant_decision(symbol?)`
- `quant_positions()`
- `quant_observations(mode?, since?)`
- `quant_once(idempotency_key)`
- `quant_settle(mode)`
- `quant_replay(spec)`
- `quant_experiment(spec)`

## Evidence tools

- `market_breadth(as_of)`
- `sector_state(sector, as_of)`
- `price_history(symbol, range, as_of?)`
- `intraday(symbol, date, interval, as_of?)`
- `announcements(symbol, range, as_of?)`
- `financials(symbol, as_of?)`
- `corporate_actions(symbol, range, as_of?)`
- `regulatory_events(symbol, range, as_of?)`
- `position(symbol?)`

## Capability boundary

The Agent may chain these tools autonomously for research/diagnosis. Real brokerage execution is absent from this default surface.
