# Final Execution Plan

严格按业务证明，不按模块并行铺开。

## P0 — TRUST THE DATA

Question：数据语义和历史可得性可信吗？

- volume semantic proof
- semantic status
- financial/PIT availability
- anti-leak sliced replay
- financial-sector regression

**Exit:** 真实 semantic evidence + anti-leak PASS。失败就停止策略优化。

## P1 — TRUST THE BACKTEST

Question：收益是不是执行假象？

- PIT status
- Qlib vs quant_core parity
- net cost headline
- OOS lock
- trial/search lineage

**Exit:** frozen strategy 在独立 replay 后结论方向一致，PIT/cost/search 状态明确。

## P2 — FIND WHAT WORKS

Question：candidate score 和 S3 哪部分真有贡献？

- factor IC/RankIC/quantile
- A0–A7
- exit attribution

**Exit:** Causal Research Review 明确“有贡献 / 无贡献 / 未知”。

## P3 — TEST ROBUSTNESS

Question：结果是不是某几年/regime/大量搜索的偶然？

- walk-forward
- regime breakdown
- search-adjusted warning
- DSR/PBO if meaningful
- untouched OOS gate

**Exit:** 结论必须同时看到 periods/regimes/trial count/net expectancy/OOS。

## P4 — MAKE AGENT A REAL RESEARCHER

Question：Agent 能否从证据自主提出下一步？

- Research Log / Lessons / Open Questions
- recall
- Agent chooses uncertainty
- bounded hypothesis
- isolated experiment worktree if needed
- deterministic evaluation
- contradiction/next question

**Exit:** 一次非预枚举 Agent-led research run。

## P5 — REPLAY EVERY DECISION

Question：三个月后能否完整重建今天？

- report_id
- immutable scan/candidate/report
- snapshot refs / repository revision
- every-run append
- agent_run_id/trace_id
- stale detection

**Exit:** 随机旧 report_id 可复原 data/strategy/Agent/decision/HTML/commit。

## P6 — FORWARD LEARNING

- D+1/3/5/8
- MFE/MAE
- realized exit/net P&L
- review packet
- lesson update
- CONTINUE/ADJUST/RETIRE

**Exit:** 至少一次真实 forward outcome 改变 Lesson 或 research priority。

## Freeze

P0–P5 后停止架构开发，进入 `run -> observe -> settle -> review -> learn`。
