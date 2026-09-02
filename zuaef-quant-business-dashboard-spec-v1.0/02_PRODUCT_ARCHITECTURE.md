# 02 — Product Architecture

## 1. Two dashboards, not one overloaded page

### A. Quant Business Dashboard — new default

Path:

```text
docs/quant/business.html
```

Purpose:
- daily decision surface;
- candidate ranking;
- live action candidates;
- legacy holding diagnosis;
- forward evidence.

### B. Engineering / Audit Dashboard — preserve existing page

Path:

```text
docs/quant/dashboard.html
```

Purpose:
- U0–P5.5 proof chain;
- data provenance;
- replay / Qlib evidence;
- runtime / artifact traceability;
- engineering regressions.

Do not delete or collapse the audit page into the business page.

## 2. Runtime flow

```text
                       OFF-HOURS / MANUAL REFRESH
CSI300 + CSI500 membership
          ↓
fundamental + valuation + quality data
          ↓
tools/quant_build_candidates.py
          ↓
workspace/artifacts/quant/business/candidate_snapshot.json
          ↓
data/quant-cache/candidates/active_symbols.json
          │
          ├────────────────────────────┐
          │                            │
          ▼                            ▼
quant_live_scan.py               business renderer
          │                            │
          ▼                            ▼
/api/scan                     docs/quant/business.html
          │
          ▼
0..10 deterministic triggers
          │
          ▼
QuantDecision Agent
          │
          ▼
Decision Brief
```

Legacy holdings are a separate lane:

```text
benchmarks/quant/gen1/legacy_watchlist.toml
          ↓
/api/watchlist
          ↓
Business Dashboard “Legacy Holdings” card
```

## 3. Server routes

Modify `tools/quant_serve.py` minimally:

```text
GET /              -> business.html
GET /business      -> business.html
GET /engineering   -> dashboard.html
GET /api/scan      -> active candidate live scan
GET /api/watchlist -> explicit live scan of legacy watchlist
```

No framework migration. Keep `http.server` / loopback-only implementation.

## 4. Agent boundary

The Agent does NOT build the candidate pool.

Agent-visible market set:

```text
candidate pool
    ↓ deterministic rank/filter
active symbols
    ↓ deterministic timing trigger
0..10 triggers
    ↓
LLM reasoning
```

This preserves the current “evidence before intuition” boundary.
