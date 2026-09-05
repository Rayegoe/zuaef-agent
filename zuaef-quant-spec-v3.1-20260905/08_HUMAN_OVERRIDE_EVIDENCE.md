# 08 — Human Override / SKIP Evidence

The current system already records `HUMAN_SKIP` plus a forward observation.
Treat this as first-class human-vs-system evidence.

Suggested labels:
- SYSTEM_READY_HUMAN_EXECUTED
- SYSTEM_READY_HUMAN_SKIPPED
- SYSTEM_NEAR_HUMAN_SKIPPED
- SYSTEM_EXIT_ALERT_HUMAN_EXECUTED

Evaluate:
- executed vs skipped forward expectancy;
- tail loss;
- MFE/MAE;
- reason codes for useful human overrides;
- whether Agent explanation improves decisions.

Invariant: `skip` records a human fact and does not mutate opportunity lifecycle.
Do not promote policy changes until sample quality is sufficient.
