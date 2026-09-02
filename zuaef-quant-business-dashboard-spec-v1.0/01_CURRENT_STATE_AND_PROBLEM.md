# 01 — Current State and Problem Statement

## 1. Current repository truth

Current live scanner behavior:
- `tools/quant_live_scan.py` reads `benchmarks/quant/gen1/universe.toml` first.
- That committed file currently contains exactly four symbols:
  - `601233`
  - `002460`
  - `002415`
  - `000009`
- The scanner applies the frozen S3 timing rules and returns `quotes[]` plus bounded `triggers[]`.

Current engineering dashboard:
- `tools/quant_render_dashboard.py`
- `docs/quant/dashboard.html`
- emphasizes proof status, U0–P5.5 stages, model evolution, replay curves, observation logs, artifacts and runtime provenance.

Current research truth:
- Baseline ≈ +0.20% annualized / 24 trades.
- S1 ≈ +0.34% / 29 trades.
- S2 ≈ +0.01% / 9 trades, rejected.
- S3 ≈ +0.37% / 29 trades, frozen as `DEMO_ACTIVE_STRATEGY`.
- Profitability proof remains **NOT YET**.
- Forward live observation has not yet established alpha or Agent decision uplift.

## 2. Product failure

The system currently answers:

> “Did the quant Agent architecture run correctly?”

better than:

> “What is worth looking at in the market today, and why?”

This is the wrong emphasis for the next phase.

## 3. Universe failure

The four current names are **legacy holdings/watchlist**, not a sufficient discovery universe.

Treating them as the default live universe creates three problems:

1. **Opportunity starvation** — four stocks can naturally produce no triggers for long periods.
2. **Experimental ambiguity** — zero triggers may mean the strategy is sparse or merely that the universe is too small.
3. **Anchoring bias** — existing positions dominate attention while better alternatives remain invisible.

## 4. Required separation

```text
Legacy Holdings / Watchlist
    4 user-owned names
    ↓
Shown and diagnosed, but NOT automatically promoted

Discovery Base
    broad, liquid A-share set
    ↓
Value / Quality / Tradeability screening
    ↓
Candidate Pool (target 20–50)
    ↓
Existing deterministic live strategy
    ↓
Action Candidates (0–10)
    ↓
QuantDecision Agent
    ↓
NO_TRADE / WATCH / ENTER_CANDIDATE / ...
```

## 5. Non-goal

Do not solve “more opportunities” by loosening S3 merely to create trades. First expand the **opportunity set** and measure forward evidence.
