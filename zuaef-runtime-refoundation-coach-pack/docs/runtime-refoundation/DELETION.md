# DELETION — Complexity Retirement Ledger

## Purpose

Re-foundation fails if every old abstraction remains "just in case".

This file defines how code loses production authority.

## Statuses

### KEEP — proven invariant
Cross-domain correctness/security/execution boundary.

### PROFILE-ONLY
Useful, but only in measured deployments.

### EXPERIMENTAL
Benchmark or A/B surface only.

### QUARANTINE
Retained for comparison/migration; not production authority.

### DELETE
No current authority and no needed reference value.

## Initial suspects

These are **investigation targets**, not pre-approved deletions:

- default global Planning exposure;
- broad Skills exposure for single-purpose tasks;
- status/plan actions that exist only for observability;
- full-history revision reconstruction;
- item-by-item domain observation where batching preserves semantic ownership;
- repeated claim-check loops over unchanged evidence;
- duplicated domain and generic knowledge/file surfaces;
- model-visible mechanical state transitions;
- compatibility flags whose only purpose was a superseded architecture.

## Deletion proof

Before deleting a behavior:

1. identify its current caller/authority;
2. identify the failure it was originally intended to solve;
3. confirm a new path covers required behavior or that the failure no longer exists;
4. run affected unit/integration/real-model benchmarks;
5. delete code, tests and docs that describe the obsolete authority;
6. avoid leaving two equal "official" paths.

## No zombie architecture

Do not leave:

```text
legacy path
new path
"temporary" compatibility layer
old flags
old docs
old tests
```

all indefinitely active.

A migration phase must end with authority consolidation.

## Deletion is not success by itself

Removing a capability that was actually necessary is a regression.

The desired result is:

```text
less model-boundary complexity
with equal or better accepted outcome
```

