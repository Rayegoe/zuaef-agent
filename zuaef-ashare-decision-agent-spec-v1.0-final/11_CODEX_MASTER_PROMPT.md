# Codex Master Prompt — ZUAEF A-Share Decision Agent v1.0

Implement this pack against the current local `Rayegoe/zuaef-agent` checkout.

## Highest-order objective

Build the smallest working business loop that improves evidence available to a small-capital A-share trader.

**Do not build a quant platform.**

## Repository authority

First record:

```bash
git status --short --branch
git rev-parse HEAD
```

Local HEAD/worktree is implementation authority. Preserve unrelated dirty work. Do not reset, clean, discard, commit or push unless explicitly instructed. Remote SHAs in `12_UPSTREAM_LOCK.toml` are audit references only.

## Architecture constraints

- Keep ZUAEF Core business-domain neutral.
- Use existing Plugin API.
- Represent the domain as a lightweight Pydantic AI `QuantDecision` Capability containing stable instructions + minimal QuantToolset.
- Do not introduce custom `AbstractCapability` subclass until a concrete need requires hooks/wrapping/per-run capability state.
- Reuse StepPersistence, receipt and composition mechanisms.
- No second Agent runtime.
- No Manager/Registry/Coordinator/Orchestrator/StateMachine without concrete failure evidence.
- Artifacts are business truth; no experiment DB required in v1.

## Upstream rule

Perform U0 separately before Quant integration:
- validate Pydantic AI 2.35.3;
- validate Harness 0.27.x;
- run full existing regression;
- minor-bound Harness after validation;
- if upgrade requires broad unrelated refactoring, stop/report rather than rewriting Core.

## Strict business phase order

### P0 — Real data
Do not create Agent integration before real AKShare smoke works.

Prove real daily history, CSI500-related data, current market snapshot, timestamps/freshness/latency and simple cache.

### P1 — One strategy
Build one fixed complete strategy from real data. Produce trades and after-cost metrics.

### P2 — Replay
Replay frozen trade intents independently under A-share constraints. Never use Qlib final NAV as replay input.

### P3 — QuantDecision
Only now wrap the proven evaluator in existing ZUAEF Plugin/Capability composition.

### P4 — Three fresh runs
Agent reads prior Strategy Result, proposes one material mutation, evaluates, reflects, ends. Repeat fresh.

### P5 — Live
Deterministic scanner on current data, only triggers to Agent, Decision Brief output.

### P6/P7
Paper first, then manually recorded real outcomes.

## Market integrity

Do not silently fake point-in-time universe, historical suspension/risk status, execution price, price limits or costs. If missing data prevents a claim, report the limitation.

Do not scatter timeless A-share constants through Python. Use a small effective-dated/frozen rules config and deterministic functions.

## Strategy integrity

- StrategySpec is minimal execution ABI.
- No arbitrary Python.
- Agent cannot modify evaluator/rules/costs/data split/benchmark.
- One material mutation per child when possible.
- Net/cost/drawdown/trade evidence outranks attractive prose.

## Holdout integrity

Do not expose the final holdout to every iterative run.

Maintain iterative research, bounded host-only promotion test, hidden champion holdout and forward paper/real period.

## Live integrity

- broad scan deterministic;
- LLM gets bounded candidates;
- `NO_TRADE` valid;
- `ENTER_CANDIDATE` is not an order;
- no broker API in v1.

## Stop conditions

Stop/report the concrete blocker instead of building more framework if:
- AKShare is too stale/unavailable for the claimed use;
- Qlib cannot produce the fixed baseline;
- replay cannot represent required execution semantics honestly;
- PIT/tradeability gaps invalidate the intended claim;
- upstream refresh requires unrelated Core redesign.

## Required final implementation report

1. `BASELINE`: local HEAD, dirty state, upstream versions.
2. `REAL DATA`: functions/endpoints used, timestamps, freshness/latency, limitations.
3. `BASELINE STRATEGY`: exact strategy, window, metrics, artifact paths.
4. `REPLAY`: engine, A-share rules, Qlib/replay divergence, blocked trades.
5. `CAPABILITY`: plugin files, QuantDecision construction, tools, Core diff confirmation.
6. `LEARNING`: S1/S2/S3 and evidence changing each next action.
7. `LIVE/PAPER`: only if actually completed.
8. `REGRESSION`: commands/results.
9. `NOT BUILT`: deferred architecture/features.

Never claim completion when only scaffolding exists.
