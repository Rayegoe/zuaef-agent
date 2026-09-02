---
type: concept
title: '量化交易基础概念（本项目如何体现每个原则）'
tags:
- quant
- learning
- fundamentals
- methodology
sources:
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/04_DATA_AND_MARKET.md
  title: Data and A-Share Market Truth
  evidence: "§5 survivorship; §7 execution truth; §10 data honesty"
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/05_STRATEGY_AND_EVALUATION.md
  title: Strategy and Evaluation Protocol
  evidence: "§7 independent replay; §9 anti-overfit; §11 reward"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: Implementation summary
  evidence: "§2 P2; §5.4/§5.5 观察期指标; §6 重启准入"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/STATUS.md
  title: Program status
  evidence: "Known limitations carried forward"
generated:
  by: zuaef-agent
  date: 2026-09-02
---

# 量化交易基础概念（以本项目为实例）

> 本节点是**学习索引**：每个概念给你"是什么"的一行定义 + "本项目在哪里体现/如何实践"。
> 通用定义部分超出项目语料，属背景知识；项目内的实践全部可追溯到 sources。

## 1. 数据诚实（data honesty）
- **是什么**：无法可靠重建的事实必须显式返回"限制/无效"，绝不为了保持流水线绿色而编造
  （spec 04 §10）。
- **本项目实践**：EastMoney 不可达就换数据面并记录；PIT 成员缺失就写进每份 Strategy Result；
  缓存 sidecar 记录来源/时间/范围，错误不会静默替换成 stale 数据。

## 2. 回测窗口角色与数据泄漏（leakage）
- **是什么**：回测里出现"未来信息"就是泄漏——最常见的三类：用未来数据选股、用全样本调参
  再在同一个样本上报喜、成交价用信号日收盘而不是下一日可执行价。
- **本项目实践**：T 日信号 → **T+1 开盘成交**（修复过"决策日当天成交"的真 bug）；
  research/promotion/holdout/forward 四窗隔离（spec 05 §9）。

## 3. 幸存者偏差与 PIT（point-in-time）
- **是什么**：用今天的成分股名单回看历史，被退市/调出股票的历史被抹掉，收益被系统性高估；
  PIT = 每个历史日期只知道当时知道的成分。
- **本项目实践**：今日 CSI500 成员回看所有日期，**显式标注在每一份结果里**，且 PIT 重建
  被设为任何盈利声明的前置门（spec 04 §5）。

## 4. 执行真相（execution truth）——假 alpha 的来源
- **是什么**：回测里"能成交"不等于"真能成交"。T+1、涨跌停板封死、停牌、整手、佣金、
  印花税、滑点、信号时序都会制造纸面收益。
- **本项目实践**：独立重放引擎（raw 价格 + market_truth=ON）+ 14 个防伪测试 +
  双引擎一致性 ≤3pp——"重放越独立，结果越可信"（spec 04 §7；05 §7）。

## 5. 前视证据（forward evidence）与 paper trading
- **是什么**：历史回测只能证"曾经"，forward 是在冻结时刻之后、真实未来市场里的
  纸面/小仓位观察，永不回溯改写。
- **本项目实践**：2026-09-02 代码冻结即 forward 起点；前几笔 trigger 人工结算，
  记录 signal/brief 价格漂移、D+1/D+3/D+5/D+8 收盘、MFE/MAE、实际可成交性（README §5.4）。

## 6. 过拟合与 p-hacking
- **是什么**：样本内反复调参总会找到一个好看的参数——样本量越小越容易自欺；
  被反复查询的数据集已变成训练数据。
- **本项目实践**：一轮只改一个 mutation；S2 被否决就换方向；29 笔交易上**停止**一切
  历史调参（"继续搜索就是 p-hacking"）（README §2 P4.5、§6）。

## 7. 信号质量指标（观察期只看这五个）
- Trigger frequency（有没有足够机会）、Signal→Brief latency（Agent 赶不赶得上）、
  Signal→Brief price drift（延迟是否造成真实损失）、Subsequent return path（信号有无意义）、
  Agent veto 价值（LLM 相对裸扫描器有无增益）。
- **本项目实践**：实测 2026-09-02 盘中 37 只 0 触发 → Agent 独立给出 NO_TRADE；
  signal→brief 延迟 86s（scan 本身仅 ~3s）。30–50 个 trigger 后做 A/B：
  scanner+LLM vs scanner alone（README §5.5）。

## 8. 收益 vs 风险/成本（reward 观）
- **是什么**：毛利更高但成本拖累/回撤更差的候选并不自动更好；优化目标是完整策略的
  成本后结果，不是单一胜率（spec 05 §6/§11，v1 无 RL）。
- **本项目实践**：主证据 = 笔数、净收益、每笔期望、盈利因子、最大回撤、平均持有、成本拖累；
  S3 冻结时明确记录成本拖累 0.44% 量级的影响。

## 9. 权威边界：确定性 vs LLM
- **是什么**：市场事实（价格、可成交性、成本）是确定性的，模型只负责假设与解读——
  模型"觉得会涨"不能成为成交价/成交记录的证据。
- **本项目实践**：spec 02 §1（LLM 不拥有确定性市场事实）；工具返回有界证据，
  ENTER_CANDIDATE 永远不是订单；无候选时 NO_TRADE 合法。