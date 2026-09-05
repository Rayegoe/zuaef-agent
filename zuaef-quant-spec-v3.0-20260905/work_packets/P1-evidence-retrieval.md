# WP4 — Evidence Retrieval v1

## Goal
Give Agent independent, targeted evidence after Quant narrows the candidate set.

## Priority
1. market/sector breadth
2. announcements
3. corporate actions/trading status
4. current positions/cost basis
5. minute price/volume

## Tasks
- provider adapters with source/as-of metadata;
- strict historical `as_of` support or explicit non-PIT labeling;
- bounded retrieval and caching;
- Agent tool registration;
- risk-filter interpretation for announcements.

## Non-goal
Do not bulk-import Level-2, sell-side research, or social feeds.
