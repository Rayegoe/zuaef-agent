# 04 — Decision Pipeline

Current production:
`CSI300∪CSI500 -> hard exclusions -> scoring -> Top-N(~50) -> M1 observation -> WATCH/NEAR/READY/INVALIDATED -> deterministic gates -> human attention -> ack/skip -> D+1/3/5/8 settlement`.

v3.1 initially adds Market Regime only as a parallel shadow projection.

Do not flatten:
- MARKET_CLOSED
- SYSTEM_UNAVAILABLE
- DATA_UNTRUSTED
- NO_TRIGGER
- NO_TRADE
- RISK_BLOCKED
- DO_NOT_PARTICIPATE
- HUMAN_SKIP

Future promoted regime semantics, only after evidence:
- DO_NOT_PARTICIPATE: no new entries
- SELECTIVE: tighter threshold/lower exposure
- NORMAL: normal rules
