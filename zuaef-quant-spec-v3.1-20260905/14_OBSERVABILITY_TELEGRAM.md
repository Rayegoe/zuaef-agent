# 14 — Workbench / Observability / Telegram

Current implementation is a contract, not a TODO.

Preserve Workbench truth distinctions:
- NOW from durable artifacts;
- heartbeat != last_scan;
- data_trust != runtime availability;
- action queue and durable timeline;
- current positions;
- loopback-only human-action writes.

Preserve Bridge:
- single proactive Telegram delivery authority;
- E1/E2 Agent interpretation only;
- deterministic copy for system/data/position facts;
- deterministic fallback if Agent fails;
- checkpoint after successful delivery;
- source reset safety;
- recovery determined by host evidence;
- daily continuity shares Dashboard truth implementation.

v3.1 may add replay/shadow/experiment summaries to presentation, but must not mix them with live truth.

Until next real-session zero-initiation event receipt succeeds:
`proactive_event_delivery = IMPLEMENTED_NOT_PROVEN`.
