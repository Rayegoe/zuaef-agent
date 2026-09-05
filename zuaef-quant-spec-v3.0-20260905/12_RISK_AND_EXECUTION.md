# 12 — Risk & Execution

## Principle

LLM reasoning must never be the final permission layer for capital-changing actions.

## Deterministic risk gates

At minimum represent explicitly:

- market participation permission;
- symbol eligibility/trading status;
- data freshness/trust;
- trigger readiness;
- max position size;
- portfolio concentration;
- sector concentration when relevant;
- risk budget / loss budget;
- duplicate/order lifecycle state;
- exit urgency.

## External effects

Real brokerage actions are external effects. v3 may prepare the interface but should keep real order execution disabled by default until:

- live forward evidence reaches the agreed gate;
- order idempotency/reconciliation exists;
- broker/account state is verified;
- emergency stop/kill switch is tested;
- operator explicitly enables the external-effect path.

## Human role

During current M1:

- Agent may recommend/prepare;
- deterministic core may permit/deny;
- human retains final real-money action unless a later release explicitly changes that policy.

## Fail-closed conditions

Examples:

- critical fresh price unavailable;
- trading status unknown;
- data unit/semantic mismatch;
- conflicting open-order/position state;
- production strategy version unknown;
- evidence store unavailable;
- external-effect authorization absent.
