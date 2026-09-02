# Acceptance Checklist

## A. Repository/upstream
- [ ] Local HEAD/dirty state recorded before edits.
- [ ] Unrelated work preserved.
- [ ] Validated Pydantic/Harness baseline recorded.
- [ ] Harness 0.x is minor-bounded after refresh.
- [ ] ZUAEF Core remains domain-neutral.

## B. Real data
- [ ] AKShare is really called.
- [ ] Historical data is not fixture-only.
- [ ] Current snapshot timestamp is surfaced.
- [ ] Latency/freshness measured.
- [ ] Failure/stale behavior explicit.
- [ ] PIT/universe limitations documented.

## C. Strategy engine
- [ ] Complete minimal StrategySpec.
- [ ] No arbitrary Python from Agent.
- [ ] Baseline produces trades.
- [ ] Costs deducted.
- [ ] Metrics include trade count, expectancy/profit factor, drawdown and net result.
- [ ] Lookahead protection tested.

## D. A-share execution
- [ ] T+1 tested.
- [ ] Suspension tested.
- [ ] Price-limit non-fill tested.
- [ ] Quantity/lot handling tested for supported universe.
- [ ] Commission/minimum commission/stamp duty/slippage centrally configured.
- [ ] Historical rule changes are not represented as one timeless constant.
- [ ] Raw execution prices used.

## E. Replay
- [ ] Replay consumes frozen signals/trade intents, not Qlib final NAV.
- [ ] Qlib/replay divergence reported.
- [ ] Blocked orders visible.
- [ ] Large unexplained divergence prevents a strong strategy claim.

## F. Capability integration
- [ ] `zuaef-quant` is a normal ZUAEF Plugin.
- [ ] Agent-facing domain unit is Pydantic `QuantDecision` Capability.
- [ ] v1 uses simple `Capability(...)` unless subclass need is proven.
- [ ] Capability contains stable instructions + minimal Toolset.
- [ ] No QuantRuntime/second Agent framework.
- [ ] Existing persistence/receipt mechanism remains execution substrate.

## G. Learning
- [ ] Results are durable artifacts/knowledge.
- [ ] Each iteration is a fresh run.
- [ ] Child names parent problem and material mutation/direction change.
- [ ] Agent cannot modify evaluator/rules/costs/data split.
- [ ] Three-run proof demonstrates evidence-dependent next action.
- [ ] Hidden holdout is not exposed every iteration.
- [ ] 10-run A/B required before strong self-learning claim.
- [ ] No 100-run optics loop before 10-run proof.

## H. Live decision
- [ ] Deterministic scanner filters market before LLM.
- [ ] Candidate context includes timestamp/freshness.
- [ ] `NO_TRADE` supported.
- [ ] Decision Brief includes strategy/evidence/risk/invalidation.
- [ ] LLM does not calculate basic indicators.
- [ ] Watcher, if used, is host process not Plugin background task.

## I. Capital boundary
- [ ] v1 cannot automatically place an order.
- [ ] Human retains final execution authority.
- [ ] Paper path works before real feedback is treated as learning evidence.
- [ ] Real outcomes can be recorded.
- [ ] No guaranteed-profit claim.

## J. Outcome-first architecture
- [ ] Real baseline worked before platform features.
- [ ] No experiment DB before measured need.
- [ ] No Promotion/Gate state machine.
- [ ] No schema exists only to move fields between layers.
- [ ] Every significant abstraction names the concrete failure it solves.
