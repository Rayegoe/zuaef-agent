# Quant Intent Baseline — P0

| Field | Value |
|---|---|
| Status | static surface baseline recorded; real-model trajectories NOT RUN |
| Baseline | `main@cf581e5` before/with the P2 semantic-surface additions |
| Date | 2026-09-11 |

## 1. Purpose

The P0 baseline exists to prove how indirect the current path is from a real user intent to existing
Quant reality. It is not a model benchmark and must not be fabricated. The first slice of this spec
(P2) added narrow semantic tools based on the existing implementation, but did not execute a
real-model canary; P3 owns that evidence.

This document therefore separates:

```text
STATIC MODEL-VISIBLE SURFACE BASELINE   measured from composition tests
REAL-MODEL INTENT TRAJECTORY            NOT RUN
```

Do not claim a business outcome or runtime improvement from the static baseline alone.

## 2. Static model-visible surface baseline

Before P2, the Quant capability exposed this model-visible surface:

Resident core:

```text
evaluate_strategy
get_live_signals
record_decision_brief
record_trade_outcome
get_trading_context
get_symbol_context
get_analysis_watchlist
update_analysis_watchlist
```

Deferred via ToolSearch (low-frequency / research):

```text
get_market_context
get_market_intelligence
save_research_packet
get_research_packet
record_customer_evidence
render_quant_business_artifact
```

After P2.1 closure, the initial model-visible surface no longer carries a
legacy broad-tool advantage.

Resident semantic core:

```text
get_symbol_context
evaluate_strategy
record_decision_brief
record_trade_outcome
```

Deferred through ToolSearch:

```text
OBSERVE
get_market_context
get_signal_board
get_positions
get_validation_status

OPERATE
run_live_scan
manage_watchlist

RESEARCH / RECORD COMPATIBILITY
get_market_intelligence
save_research_packet
get_research_packet
record_customer_evidence
render_quant_business_artifact

LEGACY COMPATIBILITY
get_trading_context
get_live_signals
get_analysis_watchlist
update_analysis_watchlist
```

This is the intended progressive-disclosure behavior: a richer semantic surface with the same or a
smaller initial prompt, and no legacy resident bias.

## 3. Static path diagnosis

The current implementation has a rich internal capability set but until P2 few intent-specific
interfaces. The resulting expected path for narrow intents is:

| Golden intent | Pre-P2 likely surface | Problem |
|---|---|---|
| 今天A股为什么大跌？ | `get_market_context` (deferred, discoverable) | correct since Task Boundary Repair, but the surface is narrow relative to the rest of Quant |
| 分析 002415 | `get_symbol_context` | good for diagnosis, but broad analysis may still pull research tools |
| 今天有什么机会？ | `get_trading_context` or `get_live_signals` | broad mixed context or scan run instead of a bounded readiness board |
| 我现在持有什么？ | `get_trading_context` | mixed payload includes READY/NEAR/validation/window data irrelevant to holding state |
| 策略验证到哪一步？ | `get_trading_context` | full mixed projection where a validation accounting block would answer the question |
| 重新扫描今天 | likely `get_live_signals` or generic `run_code`/repo/shell | no explicit operate affordance named after the user's request |
| 把 002415 加入观察 | `update_analysis_watchlist` | exists, but legacy name/transaction model is less directly discoverable than `manage_watchlist` |

The pre-P2 structural issue was:

```text
Implementation Surface >> Semantic Surface
```

This is an inventory diagnosis, not a measured trajectory. The actual request/tool sequences and
generic-escape rate remain to be measured in P3.

## 4. Real-model P3 execution record (completed)

P3 was executed after the P2.1 closure on the local tested tree through the
Gateway interaction path: normalized Telegram `InboundEnvelope`, fresh `/new`
+ `/profile quant-decision` per canary, `GatewayService.handle()` dispatch,
and a capture `SurfaceAdapter`. The model and tools were real; runtime state
was canary-only and the watchlist scope was isolated and restored.

| Field | Value |
|---|---|
| tested tree | `cf581e50b62e` + P0–P2.1 uncommitted patches |
| profile | `quant-decision` |
| model | `deepseek/deepseek-v4-flash-0731` |
| interaction path | `GatewayService.handle()` (normalized Telegram envelope) |
| watchlist scope | `p3gw-canary-watchlist` (restored to empty) |
| result | `P3_FULL_PASS` |
| P4 authorized / status | YES, executed — see `P4_ENGINE_CONSOLIDATION_REPORT.md` |

Actual semantic paths:

| Canary | Prompt | Expected | Actual | Requests |
|---|---|---|---|---:|
| 1 | 策略现在验证到什么程度？ | `get_validation_status` | `load_capability -> search_tools -> get_validation_status` | 3 |
| 2 | 我现在持有什么？ | `get_positions` | `search_tools -> get_positions` | 3 |
| 3 | 今天有什么机会？ | `get_signal_board` | `search_tools -> get_signal_board` | 3 |
| 4 | 重新扫描一下今天。 | `run_live_scan` | `search_tools -> run_live_scan` | 3 |
| 5a | 把600519加入观察。 | `manage_watchlist(add)` | `search_tools -> manage_watchlist` | 3 |
| 5b | 把600519移出观察。 | `manage_watchlist(remove)` | `search_tools -> manage_watchlist` | 3 |
| 6 | 分析一下002415现在的情况。 | `get_symbol_context` | `get_symbol_context` | 2 |
| 7 | 分析今天A股为什么大跌。 | `get_market_context` | `search_tools -> get_market_context` | 3 |
| 8 | 分析今天A股为什么大跌，并告诉我这对现有持仓有什么影响。 | `get_market_context` + `get_positions` | `search_tools -> get_market_context -> get_positions` | 3 |

Canary 1 additionally loaded the `quant-research` skill via
`load_capability` before its search; the expected `get_validation_status`
path was still used. This is recorded as a non-blocking discovery-efficiency
observation, not a P3 failure.

Full user-visible answers, token usage, wall clock and failure taxonomy are in
[`P3_QUANT_CANARY_REPORT.md`](./P3_QUANT_CANARY_REPORT.md) and raw evidence in
[`P3_QUANT_CANARY_RESULTS.json`](./P3_QUANT_CANARY_RESULTS.json).

## 5. Status

- Static surface inventory: recorded above.
- Real-model baseline matrix: **P3 FULL PASS**.
- P3 real-model surface canary: **COMPLETE** (`P3_FULL_PASS`).
- P4 engine consolidation: **EXECUTED** (report at
  `P4_ENGINE_CONSOLIDATION_REPORT.md`; common engine modules only; obeyed the
  no-framework boundary and preserved one owner per reality operation).
- P5 deterministic operator surface: **EXECUTED** (`zuaef-quant` CLI; see
  `P5_OPERATOR_SURFACE_REPORT.md`).
- P5.8 production authority extraction: **EXECUTED** (monitor/bridge/scan/
  quant-core authority moved into `zuaef_quant`; root scripts are thin
  compatibility wrappers; see `P5_8_PRODUCTION_AUTHORITY_REPORT.md`).
- P6 Shadow Product Layer retirement and P7 legacy tool deletion:
  **still separately gated**.
