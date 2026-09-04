# Business Dashboard Final Shape

The dashboard is a **trading work surface**, not a research status report.

## Top of Page — Four Business Questions

### 1. 现在需要我做什么？

Show material actions first:

- READY opportunity;
- INVALIDATED opportunity;
- position HOLD/REDUCE/EXIT alert;
- no action required;
- system unavailable/stale.

If there is a material action, this section must be more visually prominent than engineering badges.

### 2. 今天盯什么？

Show a compact active watch universe, ideally small enough for a human to understand:

- symbol/name;
- current lifecycle state (`WATCH / NEAR / READY / INVALIDATED`);
- current price and only strategy-relevant live measures;
- why it is on the list;
- invalidation/risk;
- latest material change time.

Candidate rank is not a buy recommendation.

### 3. 我现在有什么仓位？

For user-confirmed real or paper positions show:

- entry / current price;
- P&L;
- holding sessions;
- MFE/MAE where available;
- stop/take-profit/time/strategy invalidation conditions;
- current `HOLD / REDUCE / EXIT` state;
- latest position alert.

If no position exists, say so plainly.

### 4. 为什么可以/不可以相信当前判断？

Show a compact trust summary only to the extent it changes actionability:

- live data health;
- semantic state;
- historical PIT state;
- anti-leak scope;
- strategy evidence state;
- forward settled count.

A trust failure that prevents trading must be shown at the top as an operational failure, not hidden among lower badges.

## Alert Behavior

The UI should not require continuous staring.

Material state transitions should be eligible for active notification through the currently available notification surface. The first implementation may be local/browser/system notification; do not build a notification platform until needed.

Examples:

- WATCH -> NEAR;
- NEAR -> READY;
- READY -> INVALIDATED;
- open position approaches/enters EXIT condition;
- live data becomes stale/disconnected.

Avoid repeated alerts when nothing materially changed.

## Research View

Show baseline/ablation, IC/RankIC/quantile, exit attribution, walk-forward, regime/context breakdown, cost and search warnings.

This page explains whether the policy is useful. It must not crowd out the live trading work surface.

## Engineering/Audit View

Show data sources, artifact references, repository revision, Agent traces, semantic/PIT/anti-leak/test gates and operational diagnostics.

Engineering state is supporting evidence, not the primary user task.

## Research Memory Summary

Lessons/Open Questions/latest review may appear below the primary trading surface or in Research View. They are not one of the top four homepage questions.

## Prohibited Dashboard Failure Modes

- CI dashboard as product homepage;
- schema explorer/tool timeline/token monitor;
- stale live results shown as current;
- operational failure mislabeled as `NO_TRADE`;
- mock/demo business rows shown without unmistakable separation;
- dozens of KPIs displacing opportunities and positions.
