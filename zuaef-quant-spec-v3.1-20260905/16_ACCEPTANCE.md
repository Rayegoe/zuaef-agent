# 16 — Acceptance Criteria

A. Preserve current production:
candidate handoff, M1 monitor, MARKET_CLOSED behavior, positions, skip,
forward settlement, Workbench, six tools, renderer, Bridge.

B. Replay isolation:
explicit namespace; no live-forward counter mutation; no production mutation;
D+1/3/5/8 contract aligned.

C. PIT:
block EOD intraday leak, pre-publication announcement leak, invalid constituent leakage.

D. Agent discipline:
`AGENT_SURFACE_GAP_AUDIT.md` exists; six tools remain compatible;
no new tool without evidence.

E. Market Regime:
new field; deterministic; shadow-only; no production effect.

F. Human override:
SKIP stays canonical and comparable with executed opportunities.

G. Delivery honesty:
PROVEN_CURRENT only after required real-session proactive acceptance, not unit tests.
