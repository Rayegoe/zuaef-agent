# Codex Master Prompt

Repository: `Rayegoe/zuaef-agent`  
Baseline: `main (verified 2026-09-03 before implementation)`

This spec supersedes v1.1/v1.2.

## Mission

Deliver a business-outcome-first A-checksumre Quant Research & Decision Harness.

Primary results:

1. trustworthy data;
2. trustworthy backtest;
3. causal understanding of candidate + S3;
4. genuine Agent-led research under independent evaluation;
5. immutable decision provenance;
6. forward learning.

## Before Editing

Read all files in this pack, especially `00`, `01`, `02`, `08`, `09`. Inspect actual repo before assuming suggested paths/functions.

First produce a short baseline note tracing:

`candidate build -> active_symbols -> live scan -> Agent brief -> daily render`

and

`strategy -> Qlib -> frozen intents -> quant_core replay -> evidence`.

## Order

P0 -> P1 -> P2 -> P3 -> P4 -> P5.

Do not expand Agent research before P0/P1 truth gates are green.

## Hard Rules

### Outcome first
Every task states question / evidence gap / smallest change / acceptance proof.

### No schema theater
No new field without current consumer. No quant fields propagated into Core. Prefer stable refs/IDs.

### No tool theater
No model-visible tool just because a helper function exists. Existing filesystem/toolsets first.

### Agent must actually think
A0–A7 are scientific controls, not permanent workflow. After them Agent must select evidence-driven questions.

### Deterministic truth remains deterministic
LLM never authors authoritative return/IC/cost/PIT/volume/backtest numbers.

### Decision != Research
Decision Mode frozen. Research Mode may propose mechanisms and isolated code experiments, but no live promotion.

## Stop Conditions

- semantic bug => stop strategy optimization;
- candidate score no value => simplify/demote, don't defend it with more factors;
- S3 robust/OOS failure => record it and let Agent formulate a new mechanism;
- architecture proposal without observed failure => reject.

## Done

Do not close because tests are green. Close only when acceptance gates prove data truth, backtest truth, causal evidence, Agent participation, provenance, and anti-overengineering constraints. Then freeze architecture and move to Forward Learning.
