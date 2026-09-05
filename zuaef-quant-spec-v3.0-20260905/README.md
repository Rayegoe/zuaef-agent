# ZUAEF Quant — Live Decision & Experiment System Spec Pack v3.0

**Generated:** 2026-09-05  
**Purpose:** Codex-ready implementation pack for the current Quant system, merged from the latest runtime facts, the most recent operator decisions in this conversation, and the GitHub repository baseline.

## Authority order

When sources disagree, use this order:

1. **CURRENTLY_OBSERVED** — latest runtime/report facts supplied by the operator in this conversation.
2. **Runtime artifacts/logs** — concrete local execution evidence when Codex can inspect it.
3. **GitHub baseline** — useful for existing code shape, but explicitly allowed to lag the runtime by hours.
4. **Older specs/docs** — historical intent only.

**Never downgrade or overwrite a newer runtime truth because Git is behind.**

## Product definition

This is **not** a broker-app clone and must not expand into a general securities super-app. It is a private quant decision-and-experiment system for a small retail account:

> market participation decision → candidate compression → deterministic trigger/risk gates → evidence capture → replay/shadow/live validation → Agent-led diagnosis and experimentation.

The system should answer six questions exceptionally well:

1. Should we participate today?
2. If yes, which small set of names deserves attention?
3. Is there a real trigger now?
4. Is an existing position approaching an exit/risk condition?
5. Is the strategy degrading or invalid under the current regime?
6. What hypothesis has the Agent tested, rejected, or promoted next?

## Current runtime card

The latest operator-supplied report is `quant-business-20260904-1647.html` (109.5 KB, self-contained/offline), delivered successfully to Telegram message **107**, run prefix `a97d4047…`.

- Decision: `NOT_RUN_TODAY`
- Triggers: `0`
- Candidate pool: `50`
- Data trust: `FAIL`
  - PIT contamination: primary blocker
  - coverage: `PASS`
  - freshness: `WARN`
  - semantic: `PASS`
  - source: `PASS`
- Profitability: `UNPROVEN`
- S3: frozen
- True trade records: `5`
- Live forward observations: `0`
- M1 evidence: `PARTIAL`
- Host/runtime: healthy; this is **not** a system outage

See `00_SOURCE_OF_TRUTH_AND_CURRENT_STATE.md` for exact status semantics.

## Package map

- `00_SOURCE_OF_TRUTH_AND_CURRENT_STATE.md` — runtime truth, labels, precedence
- `01_PRODUCT_THESIS.md` — product boundary and non-goals
- `02_ARCHITECTURE.md` — target architecture and component boundaries
- `03_DECISION_PIPELINE.md` — candidate → trigger → decision → settlement
- `04_DATA_AND_PIT.md` — Point-In-Time integrity and data contracts
- `05_MARKET_REGIME.md` — participation gate design
- `06_AGENT_CONTROL_API.md` — Agent-facing actions and permissions
- `07_EVIDENCE_RETRIEVAL.md` — on-demand market evidence layer
- `08_SANDBOX_AND_CODE.md` — S0/S1/S2 experiment environments
- `09_REPLAY_SPEC.md` — 10-Day PIT-Safe Replay
- `10_EXPERIMENT_SYSTEM.md` — hypothesis/variant/evaluation/promotion
- `11_FORWARD_EVIDENCE.md` — live evidence milestones and metrics
- `12_RISK_AND_EXECUTION.md` — deterministic risk and external effects
- `13_OBSERVABILITY_TELEGRAM.md` — reports, attention, notifications
- `14_TEST_PLAN.md` — unit/integration/replay/adversarial tests
- `15_ROADMAP.md` — phased implementation
- `16_ACCEPTANCE_CRITERIA.md` — release gates
- `17_MIGRATION_FROM_CURRENT.md` — additive migration, no destructive rewrite
- `18_SECURITY_AND_INVARIANTS.md` — evidence immutability and safety invariants
- `19_OPEN_QUESTIONS.md` — questions Codex must verify rather than assume
- `CODEX_IMPLEMENTATION_BRIEF.md` — exact execution order for Codex
- `contracts/` — CLI/tool/events/state-machine contracts
- `schemas/` — JSON Schemas for machine-readable outputs
- `examples/` — representative runtime/replay/experiment payloads
- `work_packets/` — executable engineering work packets

## Non-negotiable implementation rule

Do not rewrite the working production loop to fit this document. **Extend around proven behavior, isolate experimental behavior, and add verification surfaces first.** A feature that is not verified in the current runtime must remain behind a feature flag or in shadow/replay mode.
