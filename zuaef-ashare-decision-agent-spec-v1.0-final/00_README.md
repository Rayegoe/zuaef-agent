# ZUAEF A-Share Decision Agent — Final Spec Pack

**Spec ID:** `ZUAEF-ASHARE-001`  
**Version:** `1.0-final`  
**Freeze date:** `2026-08-28`  
**Target:** `Rayegoe/zuaef-agent`

## One-sentence definition

Build the smallest working A-share decision capability that helps a small-capital retail trader make faster, evidence-based decisions from real market data, and lets the existing ZUAEF Agent improve strategies through repeated simulation and real-market feedback.

## First-principles objective

```text
real market data
+ large historical sample
+ deterministic strategy evaluation
+ LLM strategy search/reflection
+ simulation/paper/real feedback
        ↓
less intuition-only trading
        ↓
better evidence-backed capital decisions
        ↓
more credible attempts to produce short-term cashflow
```

Profit is an empirical target, never a software guarantee.

## Core architecture

```text
ZUAEF Agent Core
      │
      ├── existing upstream capabilities
      │     StepPersistence / context controls / ToolSearch where justified
      │
      ▼
zuaef-quant Plugin                 ← ZUAEF packaging/composition boundary
      │
      ▼
QuantDecision Capability           ← Pydantic AI agent-facing extension unit
      │
      ├── stable domain instructions
      └── QuantToolset
             ├── evaluate_strategy()
             ├── get_live_signals()
             └── record_trade_outcome()
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
     AKShare       Qlib     independent replay
```

`QuantDecision` should initially use the lightweight upstream `Capability(...)` primitive. Do not create a custom `AbstractCapability` subclass unless a concrete hook/wrapper/per-run-state requirement appears.

## Business outcomes

Only two outputs are primary:

1. **Decision Brief** — whether there is a worthwhile opportunity now, why, under what conditions, and what invalidates it.
2. **Strategy Result** — what was tested, what changed, what evidence returned, what failed, and what the next run should learn.

Runtime receipts, DB rows, workflow states, gate objects and status transitions are not business outcomes.

## Build order

```text
U0 upstream compatibility refresh
P0 AKShare real-data proof
P1 one complete strategy on real history
P2 independent execution replay
P3 QuantDecision capability in ZUAEF
P4 3 fresh-run strategy evolution proof
P5 live/near-live scan → Decision Brief
P6 paper/shadow feedback
P7 manual small-capital outcome recording
```

Do not implement a later phase to compensate for an earlier phase that does not work.

## Contents

- `01_PRODUCT_PRD.md` — product objective and user outcomes
- `02_ARCHITECTURE.md` — technical architecture and authority boundaries
- `03_CAPABILITY_PLUGIN_CONTRACT.md` — Capability / Plugin / Toolset relationship
- `04_DATA_AND_MARKET.md` — AKShare, Qlib ingestion and A-share execution truth
- `05_STRATEGY_AND_EVALUATION.md` — StrategySpec, evaluator, replay, anti-overfit
- `06_AGENT_LEARNING_LOOP.md` — LLM self-learning loop
- `07_REALTIME_DECISION_AND_PAPER.md` — current-market assistance and forward feedback
- `08_IMPLEMENTATION_PLAN.md` — implementation phases
- `09_TASKS.md` — concrete tasks
- `10_ACCEPTANCE_CHECKLIST.md` — acceptance criteria
- `11_CODEX_MASTER_PROMPT.md` — implementation instruction
- `12_UPSTREAM_LOCK.toml` — audited upstream state
- `13_DECISIONS_AND_NON_GOALS.md` — final architecture decisions
- `templates/` — Strategy/Result/Decision/config examples

## Highest-priority rule

> Do not build a quant platform. Connect the existing ZUAEF Agent to real A-share data and mature quant engines, prove that one complete strategy can be evaluated honestly, then let the Agent iteratively improve decisions from evidence. Add architecture only after a concrete failure proves it necessary.
