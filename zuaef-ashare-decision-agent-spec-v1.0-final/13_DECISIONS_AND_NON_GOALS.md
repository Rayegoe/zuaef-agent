# Architecture Decisions and Non-Goals

## ADR-001 — Cashflow/decision quality first
Optimize usefulness and evidence quality of small-capital decisions. First proof is one real strategy + real data + honest replay.

## ADR-002 — ZUAEF Core stays domain-neutral
Quant enters through existing Plugin composition. No Core business logic unless a platform bug is independently demonstrated.

## ADR-003 — QuantDecision is a Capability
Follow current Pydantic extension model. Plugin packages/composes; lightweight Capability bundles stable domain instructions + Toolset.

## ADR-004 — Mature frameworks compute; LLM searches/interprets
AKShare acquires, Qlib evaluates quickly, independent replay verifies executable behavior, Agent proposes/refines strategy.

## ADR-005 — Strategy is the business search unit
Complete strategy, not isolated factor, is the object that can create or destroy cashflow.

## ADR-006 — Artifact-first
No experiment database at MVP. Add an index only after measured retrieval pain.

## ADR-007 — No workflow-state platform
Research validity checks remain functions/evaluator results. Implementation phases are not runtime gates. No Promotion engine.

## ADR-008 — Hidden holdout stays hidden
Repeated LLM search cannot read every evaluation partition.

## ADR-009 — Live scanner is deterministic host logic
Broad market scanning is not a forever-running Agent.

## ADR-010 — Human order authority in v1
Paper and manually recorded real outcomes validate value before broker integration.

## ADR-011 — Architecture follows failure evidence
Do not add DB/provider framework/graph/multi-agent/RL/dashboard/broker because it may be useful later. Add only after a concrete failure makes it the smallest solution.

## ADR-012 — Latest framework does not mean every capability enabled
Use Capability as the extension primitive and existing StepPersistence/context controls. Add SpendLimits when needed. Do not enable CodeMode/SubAgents/DynamicWorkflow/Browser/Memory for fashion.
