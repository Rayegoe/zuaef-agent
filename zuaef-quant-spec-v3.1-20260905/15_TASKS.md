# 15 — Execution Backlog

## P0 — Freeze current system + strict replay
- [PASS] T000 Capture `BASELINE_RUNTIME.md` before edits.
- [PASS] T001 Verify local HEAD/status vs GitHub main as reviewed on 2026-09-05 17:20 +08; latest push at 2026-09-05 15:43 +08: `feat(quant): add quant-to-Telegram event bridge, v3.0 spec pack, and ops wiring`, preserving local-ahead work.
- [PASS] T002 Map monitor, Workbench, six tools, Bridge, timers, state and delivery paths.
- [PASS] T003 Record proactive Bridge as IMPLEMENTED_NOT_PROVEN until real-session acceptance.
- [PASS] T004 Create `AGENT_SURFACE_GAP_AUDIT.md`; no new model-visible tool before acceptance.
- [PASS] T005 Add/verify evidence namespaces: research/replay/shadow/live_forward.
- [PASS] T006 Align outcome schema on D+1/3/5/8 + MFE/MAE.
- [PASS] T007 Add narrow replay clock/as-of data seam.
- [PASS] T008 Add PIT adversarial tests: EOD leak, future announcement, membership/survivorship.
- [BLOCKED_WITH_EVIDENCE] T009 Implement recent 10-trading-day production-equivalent replay.
- [PASS] T010 Prove replay cannot mutate live-forward or production state.
- [PASS] T011 Generate replay report with per-day blocked/degraded reasons.
- [PASS] T012 Regression-test monitor, Workbench, six tools, renderer, Bridge.

## P1 — Decision context + research
- [PASS] T013 Market Regime shadow with new fields; never reuse `market_no_trade`.
- [BLOCKED_WITH_EVIDENCE] T014 Market/sector breadth evidence.
- [BLOCKED_WITH_EVIDENCE] T015 Announcements/corporate actions with availability semantics.
- [PASS] T016 Verify position/cost-basis evidence gaps first.
- [PASS] T017 Add minute data only where justified.
- [PASS] T018 Experiment Registry around existing evaluator/replay.
- [PASS] T019 S0 Scratch workflow.
- [PASS] T020 Connect S1 replay to experiment records.
- [BLOCKED_WITH_EVIDENCE] T021 S2 live shadow with zero broker effects.
- [PASS] T022 HUMAN_SKIP outcome analysis.

## P2 — Promotion
- [PASS] T023 Formal promote/reject workflow.
- [PASS] T024 Regime/degradation metrics.
- [EXPLICITLY_DEFERRED_BY_SPEC] T025 Broker execution only in separately approved scope.

Prohibited shortcuts:
- no 7th+ quant model tool before gap audit;
- no replacement evaluator without demonstrated need;
- no unauthenticated LAN write exposure;
- no replay/shadow counted as live-forward;
- no Regime encoded into market_no_trade;
- no parameter relaxation just to create triggers.
