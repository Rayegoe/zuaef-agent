# Codex Master Prompt

Repository: `Rayegoe/zuaef-agent`
Baseline: `main (verified 2026-09-03 before implementation)`

This spec supersedes v1.1/v1.2.

## Read Order

Read all files, but begin with:

1. `00_GLOBAL_STRATEGY.md`
2. `00_START_HERE.md`
3. `01_OUTCOME_AND_ANTI_PATTERN.md`
4. `08_EXECUTION_PLAN.md`
5. `09_ACCEPTANCE_GATES.md`

## Mission

Deliver a business-outcome-first A-share trading decision system with a trustworthy research/learning spine.

The operational loop is:

`select -> monitor -> decide -> manage -> observe -> learn`

The system must become useful in real market hours, not only correct in offline reports.

Primary results:

1. a small real watch universe from the real market;
2. practical minute-level intraday monitoring and material alerts;
3. position monitoring after user-confirmed/paper execution;
4. trustworthy live/historical facts and replay;
5. causal understanding of candidate + S3;
6. genuine Agent-led research under independent evaluation;
7. real forward learning.

## Before Editing

Inspect the actual repository before assuming suggested paths/functions.

Trace both:

`market -> candidate build -> active watch universe -> live monitor -> material alert -> Agent decision -> user action -> position monitor -> outcome`

and

`strategy -> research panel -> frozen intents -> independent replay -> comparison -> lesson`.

Identify where the first chain is not yet operational. Do not let the second chain consume all implementation capacity while the first remains unusable.

## Research Order

P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 remains the assurance/research order.

However:

- real forward observation begins as early as truth gates allow;
- the live trading loop should remain running in observation mode whenever safe;
- by P1 exit the system must meet Trading Assistant v0.1 operational acceptance.

## Hard Rules

### Business outcome first

Every task states the real failure/uncertainty, affected trading outcome, smallest change and acceptance evidence.

### No process-as-product

Tests, validators, reports and audit states support the product. They do not constitute product success.

### No fake business outputs

Mocks/fixtures may test code but cannot appear as current market outcomes.

### No architecture theater

No new field/structure/tool/service without a current consumer or observed failure.

### Deterministic high-frequency loop

Do not use the LLM as a quote polling engine. Deterministic code owns repeated calculations and position checks; Agent runs on material events/reviews.

### Agent must actually think

After scientific controls, Agent must select evidence-driven research questions and may reject its own hypotheses.

### Deterministic truth remains deterministic

LLM never authors authoritative return/IC/cost/PIT/volume/backtest numbers.

### Decision != Research

Live Decision Mode is frozen. Research Mode may propose experiments but cannot silently promote them to capital use.

## Stop / Redirect Conditions

- semantic/timing/live-data bug capable of false alerts => fix before actionable live use;
- live loop cannot select/monitor/manage positions => prioritize product loop over optional research infrastructure;
- candidate score no value => simplify/demote;
- S3 robust/OOS failure => record/reject and research a new mechanism;
- no operational or decision usefulness after forward observation => do not defend the project with more engineering;
- architecture proposal without observed failure => reject.

## Done

Do not close because tests are green or P0–P6 documents exist.

The system is done for this phase only when:

- a real market day can be watched continuously;
- material opportunities can alert the user;
- a recorded position can be monitored until closure;
- real outcomes are captured;
- the research spine is trustworthy enough for its claims;
- the architecture remains minimal.
