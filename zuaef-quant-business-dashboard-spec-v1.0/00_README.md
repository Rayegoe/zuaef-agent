# ZUAEF Quant Business Dashboard + Candidate Discovery Spec v1.0

**Target repo:** `https://github.com/Rayegoe/zuaef-agent`

## 0. Decision

This package changes the product emphasis from **engineering proof** to **quant decision usefulness** without replacing the proven engineering audit trail.

### Keep
- Existing `docs/quant/dashboard.html` as **Engineering / Audit Dashboard**.
- Existing Qlib + independent replay + QuantDecision + live scanner.
- Existing active strategy `benchmarks/quant/gen1/active.toml`.
- Human order authority; no broker execution.

### Add
- New default **Quant Business Dashboard**: `docs/quant/business.html`.
- A deterministic **candidate discovery pipeline** that expands beyond the current four legacy holdings.
- Value / quality / tradeability scoring with explicit raw metrics and red flags.
- Separation of three universes:
  1. `legacy_watchlist`: current four historical holdings / trapped positions.
  2. `candidate_pool`: broader evidence-ranked alternatives.
  3. `action_candidates`: deterministic live triggers among eligible candidates.

### Do not add
- Broker integration.
- Autonomous order placement.
- Scheduler / daemon / queue / DB / new manager layer.
- Full-market LLM stock picking.
- News-sentiment or analyst-report ranking in v1.
- New strategy mutation S4/S5 merely to populate the page.

## 1. Why this exists

The current dashboard proves the software works, but it overweights:
- U0–P5.5 engineering stages;
- PASS/FAIL engineering proof cards;
- scan latency and brief latency;
- Agent/harness provenance.

The trading user instead needs answers to:
1. Is there an actionable opportunity today?
2. Which stocks are worth further attention?
3. Why are they candidates?
4. Are they cheap for a reason (value trap risk)?
5. How strong is the strategy evidence?
6. How much forward evidence has accumulated?

The current committed live universe is only four user-specified names. Those names remain visible, but they must not define the opportunity set.

## 2. Product principle

> **Business page answers market questions. Engineering page explains how the answer was produced.**

The LLM must never receive thousands of stocks and improvise picks. Candidate discovery is deterministic and bounded before Agent reasoning.

## 3. Primary output

After implementation:

```text
python3 tools/quant_serve.py

http://127.0.0.1:8787/              -> Quant Business Dashboard
http://127.0.0.1:8787/engineering   -> existing engineering/audit dashboard
/api/scan                            -> live scan over active candidate universe
/api/watchlist                       -> live view of legacy holdings
```

Candidate refresh is an explicit off-hours/manual action:

```bash
uv run --group quant python tools/quant_build_candidates.py
```

Daily Agent decision remains explicit:

```bash
bash tools/quant_daily.sh
```

## 4. Acceptance sentence

The work is complete when a user can open the business page and, without reading U0/P1/P5 terminology, understand:
- today’s decision;
- top value/quality alternatives;
- current live triggers;
- why each candidate is ranked;
- red flags and data freshness;
- why the strategy is still unproven.
