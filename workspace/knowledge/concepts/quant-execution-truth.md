---
type: concept
title: 'A 股执行真相：T+1、涨跌停、成本、双引擎重放'
tags:
- quant
- execution
- replay
- chinese-market
sources:
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/quant.toml
  title: Frozen market rules (effective-dated)
  evidence: "[execution] block; stamp_duty periods; price_limits periods; consistency tolerance"
- id: sources/zuaef-quant
  resource: zuaef-quant-final-spec-v2.0-optimized/03_DATA_EXECUTION_TRUTH.md
  title: Data + Execution truth (spec v2.0)
  evidence: "P0.5 dual-engine reconciliation; attribution classes"
- id: sources/zuaef-quant
  resource: tools/quant_p05_reconcile.py
  title: P0.5 reconcile implementation
  evidence: "comparison chain; attribution classes A-F; fail condition"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: Implementation summary
  evidence: "§2 P2; §4 已证明与未构建"
generated:
  by: zuaef-agent
  date: 2026-09-04
---

# A 股执行真相

## 为什么需要"执行真相"（spec 04 §7）

重放必须覆盖能**制造假 alpha** 的失败模式：T+1 卖出约束、停牌、板块涨跌停、
涨停买/跌停卖不成交、整手规则、佣金、最低佣金、卖出印花税、滑点、信号/成交时序。
规则必须**生效日期化**（历史变了就按日期切），不允许在 Python 里散落 `LIMIT=0.10` 这类
无时间概念的常量。

## 冻结的执行规则集（quant.toml，唯一权威）

| 规则 | 值 | 生效日期化 |
|---|---|---|
| 成交时点 | T 日信号 → **T+1 开盘成交**（next_open） | — |
| T+1 | true（普通股当日买不可当日卖） | — |
| 滑点 | 10bps | — |
| 佣金 | 0.025%（最低 ¥5） | — |
| 整手 | 100 股 | — |
| 印花税（卖出） | 0.10% → **0.05%（2023-08-28 起下调）** | ✅ `[[execution.stamp_duty]]` |
| 涨跌停 主板（600/601/603/605/000/001/002/003） | ±10% | ✅ 2018-01-01 起 |
| 涨跌停 创业板（300） | ±10% → **±20%（2020-08-24 起）** | ✅ |
| 涨跌停 科创板（688） | ±20% | ✅ 2019-07-22 起 |
| 停牌 | 递延（不虚构成交） | — |
| 涨停买/跌停卖 | 不成交（block） | — |
| 初始资金 | ¥100,000 | — |

## 双引擎重放（README §2 P2；spec 05 §7-8）

```text
研究阶段（Qlib/vector）：qfq 面板、market_truth=OFF
独立重放：raw 价格、market_truth=ON（T+1/涨跌停/停牌/整手/成本全开）
   ↓ 消费同一份冻结 intents（T 日决策、T+1 开盘成交、按代码排序取候选）
```

- **重放输入**：冻结信号/交易 intents + raw 市场数据 + 冻结执行规则/成本配置。
- **重放绝不输入 Qlib 最终 NAV**；输出：成交/未成交、NAV/收益、回撤、换手/成本、被 block 的原因。
- **一致性判定**：年化差 ≤ 3pp（预声明容忍度，冻结于 quant.toml `[consistency]`）。
  实测：基线 0.02pp、S1 0.18pp、S3 0.18pp。不可解释的大分歧 = 结果不可信。
- 研究价格用复权序列；**重放成交必须用 raw/可重建可执行价格——绝不用复权合成价格成交**（spec 04 §8）。

## 防伪验证（README §2 P2；§3.3）

`tests/test_quant_replay.py`：**14 个防伪 alpha 测试**（T+1、涨跌停、停牌、整手、成本、
board 差异、market_truth 开关、无未来函数）。测试真实抓出过一个 bug：intent 在决策日当天成交
（未来函数）→ 修复为"次日开盘成交"。

## P0.5 双引擎对账（2026-09-04 增补；tools/quant_p05_reconcile.py）

问题：同一冻结策略、同一冻结 intents，Qlib 研究面与独立 A 股重放是否描述同一组经济成交事实？
**不是实现相等/NAV 相等要求**——每个实质性差异都必须被归因：

| 类 | 含义 | 处置 |
|---|---|---|
| A EXPECTED_MARKET_RULE_DIFFERENCE | T+1 开盘成交、涨停买阻/贴稳卖延、停牌无bar、整手舍入（含 raw-vs-qfq 价格面×整手交互与前期规则差异级联进现金状态）、最低佣金、印花税、滑点 | 预期差，计入对账 |
| B UNSUPPORTED_FOR_TRUSTED_PARITY | 跨不支持的除权（qfq/raw 调整机制切换） | 从可信对等子集隔离，绝不静默计入 |
| C QLIB_MODEL_LIMITATION | 向量面按设计不建模涨跌停 | 已知局限 |
| D QUANT_CORE_BUG / E QLIB_EVAL_BUG | 仅凭具体市场规则证据 | bug，需修 |
| F UNEXPLAINED | 残余 | **任何无法解释的残留 = P0.5 失败** |

对账链（冻结输入不动）：同策略 → 同 qlib panel → 持久化 intents.csv（重生成后元素级比对
证明可复现）→ 向量面（qfq、market_truth OFF）+ 独立重放（raw、market_truth ON）→
逐笔对账 → 聚合对比（只做异常检测）。P0.5 验证通过后无需每日跑。

## 与 Agent 的关系

- 评估器/规则/成本/数据切分/基准是**宿主拥有的冻结配置**，Agent 不能改（P3 边界纪律）。
- `ENTER_CANDIDATE` 永远不是订单；无候选时 NO_TRADE 合法且已实测发生（2026-09-02 盘中）。