# Version and Capability Policy

## 1. Version policy

### Production

Pin Harness by minor while it remains 0.x:

```text
>=X.Y,<X.(Y+1)
```

This is appropriate because minor releases may contain breaking changes during 0.x development.

### Follow cadence

Do not auto-upgrade production.

When a new minor appears:

1. note the release;
2. run the compatibility lane when the changes are relevant or the lag becomes operationally costly;
3. promote only after gates pass.

### Current reference

Production declared line:

```text
pydantic-ai-harness >=0.27,<0.28
pydantic-ai >=2.35.3,<3
```

Upstream candidate as of 2026-09-05:

```text
pydantic-ai-harness 0.29.x
pydantic-ai-slim >=2.38.0 upstream floor
```

## 2. Capability policy

### Principle

Upstream availability is a catalog fact. Production admission is a ZUAEF business/runtime decision.

### Required admission questions

For any new capability, reuse the repository Capability Admission Protocol:

1. What reproduced failure exists without it?
2. What mechanism does it add?
3. What model-visible tools/instructions/hooks/settings appear?
4. What request/token/context/latency cost does it add?
5. Can a narrower deterministic/toolset solution solve it?
6. Does A/B improve the target outcome?
7. Which profile/task class needs it?
8. What evidence would later justify removal?

## 3. Current watchlist

### PromptInjectionDefender

Potentially relevant to open-web research, competitive intelligence and untrusted fetched content.

Status: `EXPERIMENTAL_CANDIDATE`, not production-admitted.

Admission evidence would require a reproduced indirect-prompt-injection risk/failure on an actual ZUAEF research surface plus acceptable quality/runtime cost.

### Guardrails

Status: `NOT_ADMITTED` globally.

Add only for a precise input/tool/output contract that existing typed/tool policy does not satisfy.

### DynamicWorkflow

Status: `EXPERIMENTAL` only.

Possible future fit: bounded fan-out/chain/vote research where one scripted orchestration measurably reduces round trips or improves isolation.

Do not make it the default topology.

### Spend

Status: `NOT_ADMITTED`.

Current run-local limits are not the same mechanism. Admit Spend only for a real cross-window/per-tenant/currency budget requirement.

### Researcher/Coder

Status: `DELEGATE_OR_PROFILE_CANDIDATE`.

Reuse the combined capability only when a task class benefits from the full stack. Do not replace ZUAEF core with a generic Coder.

### CapabilityCreation

Status: `QUARANTINED_FROM_PRODUCTION_CORE`.

Runtime-created capabilities conflict with current frozen composition/authority assumptions unless a future explicit architecture decision redefines that contract.

### Full durable execution backends

Status: `NOT_ADMITTED`.

Current StepPersistence-based continuation is intentionally lighter. Temporal/DBOS/etc. require a failure/contract that the current pause/resume seam cannot satisfy.
