# ZUAEF Quant v3.1 — Live Decision + PIT Replay + Agent Research Platform

Baseline: GitHub main as reviewed on 2026-09-05 17:20 +08; latest push at 2026-09-05 15:43 +08: `feat(quant): add quant-to-Telegram event bridge, v3.0 spec pack, and ops wiring`
Date: 2026-09-05
Status: EXECUTABLE SPEC PACK

v3.1 fully replaces v3.0. It absorbs the latest shipped Workbench, six-tool QuantDecision surface,
`HUMAN_SKIP`, proactive Telegram Bridge, and systemd wiring instead of treating them as future work.

North star:
`observe -> decide/abstain -> record human action/skip -> settle -> diagnose -> experiment -> shadow -> forward -> promote/reject`

Read first:
1. `00_SOURCE_OF_TRUTH.md`
2. `01_CURRENT_IMPLEMENTATION_CONTRACT.md`
3. `02_PRD.md`
4. `03_ARCHITECTURE.md`
5. `09_PIT_SAFE_REPLAY.md`
6. `15_TASKS.md`
7. `18_CODEX_MASTER_PROMPT.md`

Status labels:
- PROVEN_CURRENT
- IMPLEMENTED_NOT_PROVEN
- CURRENT_CONTRACT
- TARGET_V31
- EXPERIMENTAL
- TO_VERIFY_RUNTIME
