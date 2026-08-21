# Decision Log

Append decisions. Do not rewrite history.

## ADR-RF-001 — Preserve repository, re-found runtime path

Decision:
- no greenfield rewrite;
- retain validated assets;
- construct minimal runtime path from zero optional capabilities;
- re-admit complexity through benchmarks.

Reason:
- current failure is architectural assumption/runtime fitness, not unusable codebase state.

Status: accepted by coach pack.

## ADR-RF-002 — Writing is canary, not architecture owner

Decision:
- WCASE exposes runtime failures;
- Writing-specific fixes remain domain-local unless demonstrated cross-domain.

Status: accepted by coach pack.

## ADR-RF-003 — Capability availability is not production admission

Decision:
- upstream existence/reuse never justifies default model exposure.

Status: accepted by coach pack.

