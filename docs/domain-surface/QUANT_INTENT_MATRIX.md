# Quant Intent Surface Matrix

| Field | Value |
|---|---|
| Status | P2 + P2.1 implemented; P3 real-model canary PASS; P4 engine consolidation executed (see `P4_ENGINE_CONSOLIDATION_REPORT.md`); P5/P6 executed and P6 closed (see `P6_CLOSURE_REPORT.md`); P7 READY, not started |
| Baseline | local working tree @ `cf581e5` plus P0–P4 patches |
| Date | 2026-09-12 |

This matrix records real user intents and the semantic surface that answers them. It is an
engineering checklist, not an ontology, runtime schema or workflow definition. A row without a real
user demand must not be added just to complete the table.

Legend:

- `native` — existing first-class semantic tool.
- `P2 new` — added in the first semantic-surface slice; deferred via ToolSearch.
- `legacy compat` — callable and tested, deferred from the resident surface; not preferred for narrow intents.
- `P3 PASS` — real-model canary reached the expected semantic tool on the Gateway bridge seam.

| User intent | Semantic tool | Reality source | Side effect | Status |
|---|---|---|---|---|
| 今天市场发生了什么 / 今天A股为什么大跌 / 外盘怎么样 | `get_market_context` | bounded market API snapshot | none | P3 PASS (Canary 7); deferred |
| 分析 002415 / 这只股票现在怎么样 / 离条件多远 | `get_symbol_context(symbol)` | quote + cached history + universe membership | none | P3 PASS (Canary 6); resident semantic core |
| 今天有什么机会 / 有哪些 READY/NEAR / 现在盯什么 | `get_signal_board()` | canonical trading `state.json` + freshness | none | P3 PASS (Canary 3); deferred |
| 我现在持有什么 / 哪些仓位需要注意 | `get_positions()` | `state.json` live position projection / `positions.json` | none | P3 PASS (Canary 2/8); deferred |
| 策略验证到哪一步 / forward evidence / 是否已经证明 | `get_validation_status()` | ledger-derived validation accounting + PIT limitation | none | P3 PASS (Canary 1); deferred |
| 重新扫描今天 / 刷新今天信号 / 跑一下候选池 | `run_live_scan()` | frozen scan engine (`zuaef_quant.scan_sidecar`) | scan-side state update only | P3 PASS (Canary 4); deferred; operator parity pending |
| 把 002415 加入观察 / 移除自选 / 查看观察列表 | `manage_watchlist(action, symbols)` | scoped watchlist files under `workspace/artifacts/quant/watchlist/` | local verified write | P3 PASS (Canary 5a/5b), state restored; deferred |
| 查一下 002415 最近的新闻 / 公告 | `get_market_intelligence(symbol)` | structured finance feed | none | existing, deferred; not part of P3 canary |
| 评估这个参数组合 / 回测这个策略 | `evaluate_strategy(spec)` | host-owned evaluator | child artifact write | existing |
| 我今天 32.5 买了 100 股 002415 | `record_trade_outcome(...)` | canonical trading ledger | local fact write | existing; explicit human fact only |
| 把这个判断记录下来 | `record_decision_brief(...)` | briefs directory | local artifact write | existing |
| Broad compatibility / full mixed context | `get_trading_context()` | canonical trading artifacts | none | legacy compat, deferred-only |
| Scan evidence before the narrow split | `get_live_signals()` | frozen scan engine | scan-side state update | legacy compat, deferred-only; same engine as `run_live_scan` |
| Analysis watchlist add/remove compatibility | `update_analysis_watchlist(action, symbols)` | watchlist files | local verified write | legacy compat, deferred-only alias of `manage_watchlist` |
| Watchlist read compatibility | `get_analysis_watchlist()` | watchlist files | none | legacy compat, deferred-only alias for list semantics |

## Narrow-intent coverage summary

| Golden intent | Expected first discovered tool | Required domain tools | Forbidden default fallback |
|---|---|---|---|
| 分析今天A股大跌原因 | `get_market_context` | ≤ 2 domain tools; no repo/shell | candidate pool or positions as market-wide evidence |
| 策略现在验证到什么程度? | `get_validation_status` | validation block only | `get_trading_context` broad dump |
| 我现在持有什么? | `get_positions` | positions + exit alerts only | `get_trading_context` broad dump |
| 重新扫描一下今天 | `run_live_scan` | scan result only | shell / repo search / direct script |
| 把海康威视加入观察 | `manage_watchlist` | one verified mutation | broad trading context + manual file mutation |

## Discovery contract

Each narrow tool description contains the user language that `ToolSearch` needs. Deterministic
discovery is pinned by `tests/test_quant_tool_disclosure.py`, which asserts the expected tool is the
top-ranked result for its intent query:

```text
今天有什么机会 ready near       -> get_signal_board
策略现在验证到什么程度           -> get_validation_status
我现在持有什么                   -> get_positions
重新扫描今天                     -> run_live_scan
把海康威视加入观察               -> manage_watchlist
```

No hand-written keyword router is introduced.

## P3 evidence (completed)

P3 was executed with a real production model through the Gateway bridge seam; see
[`P3_QUANT_CANARY_REPORT.md`](./P3_QUANT_CANARY_REPORT.md) and
[`P3_QUANT_CANARY_RESULTS.json`](./P3_QUANT_CANARY_RESULTS.json).

Result: `P3_FULL_PASS`.

- All expected semantic tools were reached.
- Zero legacy broad-tool fallback.
- Zero shell/repo/`run_code` generic escape.
- Watchlist add/remove verified and restored.
- Outcome answers were acceptable on domain review.
- Canary 8 used exactly `search_tools -> get_market_context -> get_positions`
  (3 requests, 2 domain tools, 0 generic escapes).
- Canary 1 added one `load_capability` call before `search_tools`; the expected
  `get_validation_status` path was still used and no legacy/generic fallback
  followed. Recorded as a non-blocking Harness capability-reveal observation.

P4 engine consolidation has now been executed: the expected semantic tools remain unchanged,
the P4 real-model matrix re-verified them (expected tool 9/9, zero generic escapes), and the
one non-blocking Canary 1 extra legacy read is recorded in `P4_ENGINE_CONSOLIDATION_REPORT.md`.
P5 and P6 have since been executed (P6 closed by the pre-P7 boundary cleanup,
see `P6_CLOSURE_REPORT.md`); P7 is READY but not started.
