# 01 — Current Implementation Contract

## M1 monitor
Preserve:
- production-session cadence roughly 30–60s;
- active candidate/watch universe;
- deterministic timing and opportunity lifecycle;
- positions, exit alerts, durable state/alerts, forward settlement.

Business states must remain distinct:
`MARKET_CLOSED`, `SYSTEM_UNAVAILABLE`, `NO_TRADE`, healthy material-event state.
Never convert SYSTEM_UNAVAILABLE into NO_TRADE.

## Canonical human facts
Preserve host actions:
- `ack-buy`
- `ack-sell`
- `skip`

They record human/paper/real facts, never broker orders.
`skip` writes `HUMAN_SKIP` plus a SKIP forward observation and does not alter the opportunity state machine.

## Workbench
Preserve current reads and loopback writes, including `/api/quant/now`,
`ack-buy`, `ack-sell`, and `skip`.
Do not expose unauthenticated write endpoints to LAN as an Agent-control shortcut.

## Frozen six-tool QuantDecision surface
1. evaluate_strategy
2. get_live_signals
3. record_decision_brief
4. record_trade_outcome
5. get_trading_context
6. render_quant_business_artifact

Do not casually add tool 7+. First produce `AGENT_SURFACE_GAP_AUDIT.md`.

## Bridge
Bridge is the single proactive Quant Telegram delivery authority.
- NEW_READY, POSITION_EXIT_ALERT -> Agent interpretation; Bridge sends.
- connection/data/position facts -> deterministic copy.
- Agent failure -> deterministic fallback.
- Telegram failure -> do not checkpoint past failed delivery.
- delivery identity is independent of byte cursor.
- recovery is deterministic, not inferred by Agent.
- daily continuity uses the same implementation as Dashboard.

## Forward contract
Use D+1/D+3/D+5/D+8 and MFE/MAE consistently across live, replay and shadow.

## Research evaluator boundary
Existing `evaluate_strategy` is research infrastructure, not strict production-equivalent PIT replay.
Known limitation includes current CSI500 membership applied historically.
Therefore:
`research != strict replay != live_forward`.
