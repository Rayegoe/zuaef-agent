# ZUAEF Quant Final Spec v2.0

**Status:** FINAL / EXECUTABLE / BUSINESS-ALIGNED
**Repo:** `Rayegoe/zuaef-agent`
**Verified baseline:** `main (verified 2026-09-03 before implementation)`
**Date:** 2026-09-03

Read `00_GLOBAL_STRATEGY.md` first. It defines what the product is; P0–P6 define how we make that product trustworthy, testable and learnable.

## North Star

> 为小资金 A 股个人投资者提供一个持续运行的交易决策助理：从全市场压缩出少量值得关注的机会，在交易时段持续盯盘，在用户成交后继续管理持仓，并用真实结果不断修正策略。

The shorter operational form is:

`select -> monitor -> decide -> manage -> observe -> learn`

The research form remains:

> 更少的无依据交易、更高质量的可解释决策、更可靠的策略证据，并持续从真实结果中学习。

These are not competing goals. The second exists to make the first trustworthy.

## This Version Does Not Change the Project Into a Platform

This version still replaces v1.1/v1.2. It is not a platform reconstruction. It closes the existing real data, Qlib, independent replay, candidate discovery, live scan, business dashboard and `zuaef-quant` Agent into one Outcome-First trading and research loop.

## Product Success

Success requires both **operational usefulness** and **research truth**.

### Operational usefulness

1. Real market data produces a small daily active watch universe.
2. During trading hours, that universe is refreshed at a practical seconds-to-minutes cadence and material state changes can alert the user.
3. A user-confirmed trade becomes a managed position, not a forgotten candidate.
4. Every watched/entered position accumulates real forward outcomes.

### Research truth

1. `NO_TRADE / WATCH / READY / HOLD / REDUCE / EXIT` is based on trustworthy inputs and a frozen policy for that run.
2. Historical results are not created by future information, invalid availability assumptions, missing costs or repeated search disguised as one test.
3. Agent research can propose, reject or revise hypotheses rather than only execute host-selected parameter changes.
4. Old decisions can be replayed well enough to understand what was known, what was decided and what later happened.

## Success Is Not

- new schema/class/service count;
- tool-call count;
- number of badges/KPIs;
- prettier backtest returns;
- number of passing tests;
- a complete P0/P1/P2 checklist with no useful live trading loop.

## Existing Capabilities To Preserve

- AKShare + Tencent data plane;
- Qlib research environment;
- `quant_core.py` independent A-share execution truth;
- CSI300∪CSI500 candidate discovery;
- sector-aware financial model;
- fail-closed live scan;
- Business / Engineering dashboard;
- `zuaef-quant` plugin;
- `UNPROVEN` / forward observation.

**Do not rewrite these without an observed business failure.**
