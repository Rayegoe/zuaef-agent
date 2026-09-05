# 05 — Agent Surface

Use existing six tools first.

`get_trading_context` is the main L0 current-state projection and already includes much of:
status, trust, availability, heartbeat, last scan, READY/NEAR, exit alerts, positions,
recent material events and forward counts.

`get_live_signals` is a direct scan tool; the Agent must not become the polling engine.

`record_trade_outcome` records canonical human/paper execution facts; it is not a broker tool.

`evaluate_strategy` is bounded research evaluation; it is not strict PIT replay.

Before any new model-visible tool, create `AGENT_SURFACE_GAP_AUDIT.md` with:
- business outcome;
- why six existing tools cannot solve it;
- whether host composition/CLI adapter can solve it;
- why model visibility is necessary;
- idempotency/safety effects.

Default decision: prefer composition/host adapter over expanding the model-visible surface.
