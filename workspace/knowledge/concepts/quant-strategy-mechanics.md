---
type: concept
title: '策略机制：StrategySpec、gen1 基线、冻结的 DEMO 策略与 mutation 纪律'
tags:
- quant
- strategy
- toml
- zuaef-quant
sources:
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/05_STRATEGY_AND_EVALUATION.md
  title: Strategy and Evaluation Protocol
  evidence: "§1 Strategy is the search unit; §2 Minimal StrategySpec; §3 expression strategy; §4 one material mutation"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/strategy.toml
  title: gen1 baseline strategy
  evidence: "entry_expression; exit_expression; mutatable fields"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/active.toml
  title: DEMO_ACTIVE_STRATEGY (frozen S3)
  evidence: "provenance block; all strategy params"
- id: sources/zuaef-quant
  resource: zuaef-quant-final-spec-v2.0-optimized/00_GLOBAL_STRATEGY.md
  title: Spec v2.0 global strategy
  evidence: "M1 monitoring near-band; frozen entry clauses; exit rules"
- id: sources/zuaef-quant
  resource: tools/quant_trading_monitor.py
  title: M1 trading monitor
  evidence: "WATCH/NEAR/READY/INVALIDATED lifecycle; EXECUTED via ack-buy"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: Implementation summary
  evidence: "§2 P1/P4; §3.3 冻结权威与工件地图"
generated:
  by: zuaef-agent
  date: 2026-09-04
---

# 策略机制

## 策略 = 搜索单元（spec 05 §1）

```text
Strategy = Universe + Entry + Exit + Holding + Risk boundary + Position sizing
```

因子可能有用，但现金流来自一个**完整可执行的策略**——不是单个因子。

## StrategySpec：最小 TOML ABI（spec 05 §2-3）

- 只含数值/表达式字段：schema、name、universe、entry_expression、exit_expression、
  max_holding_days、stop_loss_pct、take_profit_pct、position_fraction、max_positions。
- **禁止任意 Python**；评估器按白名单校验（插件 `validate_spec`，越界报错）。
- 表达式复用 Qlib 已验证算子（`Ref`/`Mean`），不发明通用量化 DSL。

## M1 机会生命周期（spec v2.0-optimized M1 §6；tools/quant_trading_monitor.py）

同一冻结策略在交易时段以状态机落地，入场/退出条款不被改写：

```text
WATCH（进入监控近带）→ NEAR（最差归一化剩余差距在近带内）→ READY（=冻结扫描触发+语义门）
→ INVALIDATED；EXECUTED 仅由用户 ack-buy 置位
```

- NEAR 是真实计算：到冻结入场条款（pullback、volume ratio、1d strength）的差距，不是印象值。
- 退出不变：止损/止盈/收盘破 MA5/最大持有天数（冻结 S3 规则）——监控器按同一 active.toml 执行。
- 监控器不产生新策略语义，只把既有冻结条款搬到时间维度（M1 近带参数来自 spec，不来自模型）。

## gen1 基线策略 `volume_pullback_reversal`（strategy.toml）

- Entry（T 日信号）：`pullback_5d <= -0.06 AND volume_ratio_20d >= 1.80 AND close_strength_1d >= 0`
  - `pullback_5d = $close / Ref($close, 5) - 1`（5 日回撤）
  - `volume_ratio_20d = $volume / Mean($volume, 20)`（20 日量比）
  - `close_strength_1d = $close - Ref($close, 1)`（收盘强度）
- Exit：`holding_days >= 5 OR close_below_ma5`
- 风险：stop_loss 3%、take_profit 6%、单仓 10%、最多 5 仓；max_holding_days = 5
- **可 mutation 字段**：`entry_pullback_max`、`entry_volume_ratio_min`（默认值即基线出处）

## DEMO_ACTIVE_STRATEGY = `s3_longer_hold`（active.toml，冻结）

| 参数 | 值 |
| --- | --- |
| entry_pullback_max | −0.05（S1 从 −0.06 放宽） |
| entry_volume_ratio_min | 1.80（S2 曾试 2.2，被证据否决） |
| max_holding_days | 8（S3 从 5 延长） |
| stop_loss / take_profit | 0.03 / 0.06 |
| position_fraction / max_positions | 0.10 / 5 |
| universe | csi500_subset（37 只） |

冻结理由（active.toml provenance）：不是因为证明盈利（Profitability NOT YET），
而是它是证据最好的研究子策略、且是验证实时决策产品链路（P5）的最合适工具。
**历史调参到此为止**——下一份证据必须来自未来（paper/shadow），而不是更多 in-sample mutation。

## Mutation 纪律（spec 05 §4 + README §2 P4）

- 每个 Agent 子策略**只改一个有实质意义的主意**：阈值、持有期、出场条件、制度过滤器、单条信号子句。
- 禁止同时改 universe+entry+exit+sizing+costs。
- 宿主硬守卫：一轮只允许一次 `evaluate_strategy`；轮次形状固化（读父结果 → 一个 mutation →
  evaluate 一次 → 写结果 → END），无 workflow engine。

## 历史进化记录（active.toml provenance；README §2 P4）

| 轮次 | 变更 | 年化（独立重放） | 笔数 | 结论 |
| --- | --- | --- | --- | --- |
| 基线 | — | +0.20% | 24 | 平进平出 |
| S1 | 回撤 −0.06→−0.05 | +0.34% | 29 | 改善 |
| S2 | 量比 1.8→2.2 | +0.01% | 9 | 被证据否决（Result 自写 "hypothesis not supported"） |
| S3 | 持有 5→8 天 | +0.37% | 29 | 最优，纯出场侧收益；冻结为 DEMO |

参考：任一策略结果都带 universe PIT 局限说明；数值仅在 37 只历史轨迹上有意义。
