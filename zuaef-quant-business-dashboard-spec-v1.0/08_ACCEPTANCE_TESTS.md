# 08 — Acceptance Checklist

## A. Business correctness

- [ ] First viewport contains no U0/P1/P5 jargon.
- [ ] First viewport shows Today Decision, Live Triggers, Active Candidates, Forward Settled Trades, Strategy Evidence.
- [ ] `Profitability Proof = NOT YET` / equivalent `UNPROVEN` status is prominent.
- [ ] No dashboard text implies +0.37% historical annualized is a proven edge.

## B. Universe correctness

- [ ] The four legacy symbols are visible under Legacy Holdings.
- [ ] They do not automatically define candidate/action universe.
- [ ] Candidate pool has a target 20–50 names when source coverage permits.
- [ ] Candidate pool provenance and timestamp are visible.
- [ ] Empty candidate pool is an error/degraded condition, not `NO_TRADE`.

## C. Candidate evidence

- [ ] Each candidate exposes raw valuation/quality metrics.
- [ ] Each candidate exposes score reasons.
- [ ] Each candidate exposes red flags.
- [ ] Negative earnings do not receive a “cheap PE” advantage.
- [ ] Sector concentration cap is enforced deterministically.
- [ ] Financial-sector handling is explicit or marked unsupported/degraded.

## D. Live decision boundary

- [ ] `/api/scan` scans candidate universe, not legacy watchlist.
- [ ] `/api/watchlist` scans only legacy watchlist.
- [ ] Live trigger remains deterministic.
- [ ] LLM never scans the full discovery base.
- [ ] `ENTER_CANDIDATE` remains a candidate, never an order.

## E. Data quality

- [ ] Source and retrieval timestamp stored for essential datasets.
- [ ] Essential coverage computed.
- [ ] Coverage below threshold produces `DATA DEGRADED`.
- [ ] Cached/fallback data is timestamped, not presented as fresh.
- [ ] EastMoney outage cannot be silently swallowed.

## F. Engineering regression

- [ ] Existing engineering dashboard still renders.
- [ ] Existing quant replay tests remain green.
- [ ] Quant plugin tests remain green.
- [ ] New candidate/routing tests pass.
- [ ] `ruff check` clean.
- [ ] No broker/scheduler/database/framework added.

## G. Operator proof

A human should be able to run:

```bash
uv run --group quant python tools/quant_build_candidates.py
python3 tools/quant_render_business_dashboard.py
python3 tools/quant_serve.py
```

and see a page that answers:

> “What should I pay attention to today, why is it on the list, and what evidence is still missing?”
