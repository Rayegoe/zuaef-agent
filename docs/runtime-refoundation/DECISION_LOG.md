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

## ADR-RF-004 — T000 Coach pack installed

Decision:
- coach pack installed per INSTALL.md (skill, docs/runtime-refoundation, prompts, templates);
- AGENTS.md amended with runtime-complexity rules and coach routing per AGENTS_AMENDMENT.md;
- BUILD_MANIFEST.json regenerated; no runtime code changed.

Evidence:
- pack verified against its own MANIFEST.json before install (29/29 sha256);
- skill script tests pass (1/1);
- repository suite after install: 599 passed, 2 pre-existing failures in tests/test_production_writing.py caused by uncommitted in-flight edits to examples/production_writing.py, unrelated to this installation.

Status: accepted; T000 complete. Next: T001 metrics normalization.

