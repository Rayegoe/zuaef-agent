# CODEX MASTER PROMPT

You are implementing the ZUAEF Quant v3.0 spec pack in the **currently running local project**, not reconstructing the project from GitHub alone.

## Source priority

1. current running tree, services, logs, state and latest reports;
2. current operator/runtime facts in this pack;
3. GitHub as a structural baseline;
4. older docs/specs.

GitHub may lag the deployed/runtime tree by hours. Never reset or overwrite local work merely to match remote Git.

## Before any file edit

Create `BASELINE_RUNTIME.md` containing:

- branch/current tree status and remote relationship;
- uncommitted/unpushed changes;
- exact running Quant/bridge services or timers;
- exact existing commands/modules for status, tick/once, candidate build, live monitor, positions/exit, observations/settlement, report rendering and Telegram delivery;
- active state/evidence paths;
- active production strategy/config identity;
- currently verifiable trigger vocabulary and polling cadence;
- known PIT/data-trust implementation;
- discrepancies between runtime and this spec/Git.

Do not clean/reset/stash/checkout/merge until the baseline is captured and preserving local runtime work is guaranteed.

## Mission

Preserve the working production loop while adding, in order:

1. structured runtime status;
2. isolated evidence namespaces;
3. PIT-safe replay clock and recent 10-trading-day replay;
4. Agent L0/L1 observe/control surface;
5. Market Regime shadow gate;
6. priority Evidence Retrieval;
7. S0/S1/S2 experiment lifecycle.

Do not implement autonomous real-money broker execution in this scope.

## Non-negotiable invariants

- no replay/shadow record may increment live-forward counters;
- no data with availability after replay decision time may be consumed;
- experiments never overwrite active production strategy/config or frozen evidence;
- deterministic gates, not LLM prose, control trade permission;
- missing critical evidence fails closed;
- Telegram/report delivery retry cannot duplicate a decision;
- new capabilities remain feature-flagged/shadow-only until accepted;
- do not widen scope into a broker-app clone.

## Required evidence before completion

Show:

- changed files and rationale;
- commands/tests run and results;
- proof current production/report/Telegram path is preserved;
- 10-day replay summary or an explicit data-blocking reason per failed day;
- proof of future-data blocking;
- proof replay/live-forward counter isolation;
- Agent structured status/control demonstration;
- known limitations;
- explicit next decision: promote, continue shadow, or reject.

Read `README.md`, `SPEC.md`, `TASKS.md`, `CODEX_IMPLEMENTATION_BRIEF.md`, then execute the P0 work packets in order.
