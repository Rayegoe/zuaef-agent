# 00 — Source of Truth

Priority when sources disagree:
1. current local running tree/services/logs/canonical artifacts/latest reports;
2. current Git `main` at or after GitHub main as reviewed on 2026-09-05 17:20 +08; latest push at 2026-09-05 15:43 +08: `feat(quant): add quant-to-Telegram event bridge, v3.0 spec pack, and ops wiring`;
3. this v3.1 pack;
4. older specs/docs.

Never reset a working runtime to satisfy stale documentation.

Reviewed Git baseline: GitHub main as reviewed on 2026-09-05 17:20 +08; latest push at 2026-09-05 15:43 +08: `feat(quant): add quant-to-Telegram event bridge, v3.0 spec pack, and ops wiring`.

Confirmed in that baseline:
- M1 live monitor and `WATCH/NEAR/READY/INVALIDATED/EXECUTED`;
- canonical `ack-buy/ack-sell/skip`;
- D+1/D+3/D+5/D+8 forward observations plus MFE/MAE;
- Trading Workbench and loopback write adapters;
- frozen six-tool QuantDecision capability;
- Telegram document delivery;
- one-shot Quant Telegram Bridge and systemd timer;
- event-driven Agent interpretation for material events.

Latest operator business facts before this pack:
- candidates 50; triggers 0; decision `NOT_RUN_TODAY`;
- host/runtime healthy;
- data trust FAIL, PIT contamination primary blocker;
- coverage PASS, freshness WARN, semantic PASS, source PASS;
- profitability UNPROVEN; true trade records 5; live forward observations 0; M1 PARTIAL;
- Telegram report delivery succeeded.

Proof boundary:
The proactive `Runtime -> alert -> Bridge -> Agent(E1/E2) -> Bridge -> Telegram` path is
`IMPLEMENTED_NOT_PROVEN` until a real A-share session demonstrates zero-user-initiation end-to-end receipt.
Unit tests or manual artifact delivery do not promote this to PROVEN_CURRENT.
