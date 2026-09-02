---
type: concept
title: '评估方法学：时间窗角色、反过拟合协议、指标与流水线'
tags:
- quant
- evaluation
- backtest
- anti-overfit
sources:
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/05_STRATEGY_AND_EVALUATION.md
  title: Strategy and Evaluation Protocol
  evidence: "§5 evaluate_strategy; §6 metrics; §9 anti-overfit protocol; §10 robustness minimum; §11 no RL"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/quant.toml
  title: Frozen benchmark generation 1
  evidence: "[research]/[promotion]/[holdout]/[forward] window dates"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: Implementation summary
  evidence: "§2 P1/P4; §3.2 评估流水线; §4 未构建/已知限制"
generated:
  by: zuaef-agent
  date: 2026-09-02
---

# 评估方法学

## 四条时间窗，四种信息角色（spec 05 §9；quant.toml 冻结）

| 窗口 | 区间 | 谁可见 | 用途 |
|---|---|---|---|
| **research（迭代研究）** | 2018-01-01 ~ 2022-12-31 | Agent 每轮可见 | 内部可做 walk-forward/时间切分 |
| **promotion（晋级）** | 2023-01-01 ~ 2024-12-31 | **host-only** | 有希望的决赛策略，详细指标不写进 Agent 可读的迭代历史 |
| **holdout（冠军隐子集）** | 2025-01-01 ~ 2026-08-28 | **隐藏，从不喂回搜索** | 极少/最终使用 |
| **forward（前视/paper）** | 冻结时（2026-09-02）起 | 未来 | 从不回溯改写 |

> 核心原则：Agent 反复查询的任何测试集会变成训练数据——**不要把反复查询的集合叫"封存测试集"**。
> 窗口边界在基准代开始前冻结（`benchmarks/quant/gen1/quant.toml`）。

## evaluate_strategy 流水线（spec 05 §5；README §3.2，全宿主确定性）

```text
validate spec（白名单数值字段，Python 永不越界）
→ 读冻结 gen1 配置 + universe manifest
→ stage CSV → dump_bin（vendored qlib 上游脚本）→ qlib bin 库
→ D.features 表达式（Ref/Mean）→ 信号面板
→ 确定性意图构建（T 日决策、T+1 开盘成交、按代码排序取候选）
→ 双引擎跑同一份冻结 intents（vector 研究 + 独立重放）
→ evidence.json（+trades/blocked/equity CSV）+ result.md
→ 一致性判定（年化差 ≤ 3pp）
```

Agent 不能改评估器、市场规则、成本或基准；一次评估守卫宿主强制（一轮一次）。

## 指标（spec 05 §6）

- **主证据**：交易笔数、净 PnL/净收益、每笔期望收益、盈利因子、最大回撤、
  平均持有期、成本拖累。
- **辅助**：胜率、平均盈亏比、换手、Sharpe/Sortino、IC/RankIC（适用时）。
- **永远不要只优化胜率**；毛利更高但成本/回撤更差的候选并不自动更好（§11）。

## 反过拟合与停止准则（README §2 P4/P4.5、§4）

- 一轮一个实质 mutation；S2 被证据否决后 S3 换杠杆——进化方向由证据决定，不是预写 workflow。
- **S3 冻结即停止历史调参**：29 笔交易上继续搜索就是 in-sample p-hacking。
- 当前定位是"验证产品链路的演示工具"，不是交易建议；绝对优势远在噪声内
  （最好 ±0.37% 年化 / 29 笔，带幸存者偏差的 universe）。

## 鲁棒性最低门槛才可主动使用（spec 05 §10）

足够交易样本 / 成本后结果 / 邻域参数敏感性 / 时间与制度稳定性 / 无明显单期依赖 /
重放一致性 / 无泄漏。**不建 gate 框架**——评估器返回证据，Agent 解释它。

## 未构建（冻结期不解决）

PIT universe、promotion/holdout 已冻结从未触碰（host-only）、P6/P7 框架、10-run A/B、
SpendLimits、broker；watcher 与 paper 结算引擎有意未建（先人工结算，让市场告诉我们
真正需要记录什么字段）。