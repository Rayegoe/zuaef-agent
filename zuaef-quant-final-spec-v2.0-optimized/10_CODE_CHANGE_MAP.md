# Minimal Code Change Map

Prefer extending current working paths. Do not create a generic trading platform.

## Existing Paths

- `tools/quant_live_scan.py`
  - quote-date-aligned live calculations;
  - safe repeated invocation during market hours;
  - opportunity state evidence;
  - fail closed only for trust conditions that truly block the current decision.

- `tools/quant_build_candidates.py`
  - real-market candidate discovery;
  - active watch universe handoff;
  - factor-analysis export/PIT context where needed;
  - no duplicate market-fetch stack for monitoring.

- `tools/quant_eval_qlib.py`
  - frozen research panel/intents;
  - factor/ablation/OOS hooks;
  - research efficiency, not live execution truth.

- `tools/quant_core.py`
  - independent execution/accounting truth;
  - portfolio state mechanics;
  - only change for real market/accounting defects.

- `tools/quant_render_business_dashboard.py`
  - action-first trading work surface;
  - current watch states;
  - current positions;
  - stale/disconnected/actionability warnings;
  - research/audit details remain secondary.

- `tools/quant_daily.sh`
  - daily slow-layer candidate preparation;
  - end-of-day review/archive where useful;
  - do not force minute-level monitoring through a once-daily shell workflow.

- `plugins/zuaef-quant/zuaef_quant/plugin.py`
  - Decision/Research roles;
  - Agent invoked on material event/review, not every quote refresh.

## Intraday Monitor

Use the simplest mechanism that can continuously refresh the small active watch universe and detect material state changes.

If an existing API/server loop can host it safely, extend it. Otherwise a small dedicated process/helper is acceptable.

Do not introduce Redis/Celery/Kafka/a general scheduler merely to obtain a 30–60 second watch loop.

The monitor must be able to:

- poll/update active watch names;
- detect state transition rather than only raw price movement;
- surface stale/disconnected status;
- trigger a notification/Agent review on material change;
- avoid repeated duplicate alerts without inventing a workflow platform.

## Position Manager

Implement the minimum persistent position continuity required after user-confirmed/paper execution:

- open position;
- current valuation/P&L;
- strategy/risk exit checks;
- HOLD/REDUCE/EXIT transition;
- closure;
- forward outcome linkage.

Prefer a small Quant-local representation over a generic portfolio service.

## Deterministic Helpers

Create only when current files cannot naturally contain the behavior. Existing examples may include semantic validation, scoped anti-leak checks, factor analysis, report review or alert/position helpers.

The list is not an instruction to create one file per concept.

## No New Platform

No Redis/Postgres/Celery/Kafka/vector DB/graph DB/new microservice/workflow engine unless a measured live operating failure proves it necessary.
