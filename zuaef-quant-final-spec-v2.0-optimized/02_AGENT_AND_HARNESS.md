# Agent Participation + Live Decision Harness

## Core Division of Labor

The Agent is not the polling loop.

### Deterministic layer

Owns repetitive/high-frequency facts:

- market quotes;
- price/volume/relative-state calculations;
- strategy conditions;
- position P&L;
- stop/take-profit/time-exit checks;
- live state transitions;
- execution/accounting truth.

### Agent layer

Owns lower-frequency, higher-value judgment:

- interpret a material state transition;
- prioritize competing opportunities;
- explain why/invalidation/uncertainty;
- detect contradiction between signal and context;
- review a position when something material changes;
- propose research hypotheses from failures and forward outcomes.

Do not call an LLM every polling cycle merely to prove Agent participation.

## A. Decision Mode

Used for current-market decisions. Active strategy is frozen; data/evaluator/cost/market rules are host-owned.

Decision Mode may be triggered by:

- pre-market/daily candidate review;
- WATCH -> NEAR/READY;
- READY -> INVALIDATED;
- position enters a material HOLD/REDUCE/EXIT condition;
- scheduled close review.

Agent must:

1. read deterministic market/position evidence;
2. combine it with candidate quality, risk and current data state;
3. return the appropriate business action among `NO_TRADE / WATCH / READY / HOLD / REDUCE / EXIT`;
4. explain why, invalidation and uncertainty;
5. write a concise Decision Brief when a material decision exists.

Decision Mode does not research, tune parameters or change strategy code.

## B. Research Mode

Agent may:

- read Research Log / Lessons / Open Questions / forward evidence;
- choose a high-value uncertainty;
- propose an economic mechanism and falsifiable hypothesis;
- design ablation/factor/exit/context tests;
- propose a new factor/entry/exit/event mechanism;
- when necessary, drive an Engineering Agent/Codex in an isolated experiment worktree;
- read deterministic evaluator results;
- compare against parent/baseline/simple controls;
- reject its own hypothesis;
- update Lesson impact and Next Question.

Forbidden:

- changing the active strategy inside a live run;
- changing evaluator/cost/split and then self-declaring success;
- automatic promotion to capital use;
- deleting failed experiments;
- saving only winners.

## Agent Participation Proof

At least one Research Run must contain a non-host-prewritten chain:

`recall -> choose uncertainty -> hypothesis -> experiment -> deterministic evidence -> comparison -> reject/support -> lesson -> next question`

Fixed A0→A7 controls alone do not satisfy this.

## Live Operational Requirement

The active watch universe must be monitorable during trading hours without relying on the Agent to stay awake.

Target behavior:

```text
watch universe
  -> deterministic refresh every practical seconds/minutes
  -> no material change: no Agent call
  -> material state change: persist event + optionally invoke Agent + alert user
```

If the market feed is stale/unavailable, the system must say unavailable, not silently preserve a previous live conclusion.

## Harness

Reuse Pydantic AI/Harness for run persistence, effect boundaries, lineage and observability where relevant. Do not create a Quant-specific Agent runtime.

Operational monitoring is allowed to be simpler than the Agent harness; do not force the intraday polling loop through an LLM workflow engine.

## Crash / External Effects

External actions with capital or irreversible side effects are never silently retried.

Current broker action remains outside autonomous scope. User-confirmed trades may be recorded and monitored.
