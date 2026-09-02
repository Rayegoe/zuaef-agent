---
type: concept
title: 'ZUAEF-ASHARE-001 项目总览：定位、架构与证明状态'
tags:
- quant
- architecture
- zuaef-quant
- agent-design
sources:
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/00_README.md
  title: Spec pack entry (ZUAEF-ASHARE-001 v1.0-final)
  evidence: "One-sentence definition; Business outcomes; Build order; Highest-priority rule"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: ZUAEF A股决策 Agent 实现总结与实操指南
  evidence: "§1 项目定位; §3 系统架构; §4 实现情况清单"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/STATUS.md
  title: Program status (frozen 2026-09-02)
  evidence: "P5.5 ENGINEERING FREEZE; proof table"
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/02_ARCHITECTURE.md
  title: Technical architecture
  evidence: "§1 authority boundaries; §8 no second runtime"
generated:
  by: zuaef-agent
  date: 2026-09-02
---

# 项目总览

## 一句话定义（spec 00）

为**小资金 A 股散户**构建最小可用的 A 股决策能力：接通真实行情 + 历史大样本 +
确定性策略评估 + LLM 策略搜索/反思 + 模拟/实盘反馈，减少直觉交易，让资金决策更有依据。
**盈利是实证目标，从来不是软件保证。**

## 最高优先级规则（spec 00）

> Do not build a quant platform. 不造量化平台——接通真实数据与成熟引擎（akshare/qlib），
> 诚实地证明一个完整策略可被评估，然后让 Agent 从证据里迭代。只有具体失败证明必要时才加架构。

## 架构分层与数据流（README §3.1）

```text
ZUAEF Agent Core（业务域中立，零量化改动）
  └─ zuaef-quant Plugin（plugins/zuaef-quant，入口点 quant，allow_capabilities = true）
       └─ QuantDecision Capability（10 条领域指令 + QuantToolset）
            ├─ evaluate_strategy       ┐
            ├─ get_live_signals        ┼─ subprocess 隔离（.venv-quant Python 3.12）
            ├─ record_decision_brief   ┘
            └─ record_trade_outcome（纯本地 JSONL）
                 └─ 确定性工具：quant_core / quant_eval_qlib / quant_live_scan
                      └─ 数据面：akshare 1.18.94（腾讯历史/新浪快照/CSIndex 成分/qt.gtimg.cn 实时）
```

重依赖（akshare、pyqlib）**永不进 Agent 主环境**——评估/扫描在侧环境 `.venv-quant`
（Python 3.12）以 subprocess 执行；插件包自身不背这些库（P3 设计，README §2）。

## 权威边界（spec 02 §1）——谁拥有什么

- **确定性命量化代码拥有**：行情归一化、指标计算、策略评估、交易成本、可成交性检查、事件重放、指标计算。
- **LLM 拥有**：假设形成、选择一个有意义的 mutation、解读证据、写 Strategy Result、解释 Decision Brief。
- **LLM 不拥有确定性市场事实**。"No candidate → no LLM request"（spec 02 §3：无触发就不需要请求 LLM）。

## 业务产出只有两个（spec 00）

1. **Decision Brief** — 现在是否有值得的机会、为什么、什么条件下、什么会使其失效。
2. **Strategy Result** — 测了什么、改了什么、证据返回了什么、失败在哪、下一轮学什么。

Receipts、DB 行、workflow 状态、gate 对象都不是业务产出。

## 建设顺序与当前状态

Build order（spec 00）：U0 上游兼容 → P0 真实数据证明 → P1 单策略+Qlib 评估 →
P2 独立执行重放 → P3 能力接入 → P4 三轮模型进化 → P5 实时链路 → P6 paper → P7 实盘记录。

实现状态（STATUS.md，冻结 2026-09-02）：

| Proof | State |
|---|---|
| Research Engine Proof | **PASS**（P0 真实数据 + P1 Qlib 评估 + P2 一致性） |
| Self-learning Loop Proof | **PASS**（P4：S1→S2 被否决→S3，一轮一个 mutation） |
| Profitability Proof | **NOT YET**（最好子策略 ≈ +0.37% 年化/29 笔，噪声内，有意停止 in-sample 追寻） |
| Live Decision Product | **FIRST PROOF PASS**（2026-09-02 盘中实测 NO_TRADE，86s 端到端延迟） |

**当前阶段**：P5.5 ENGINEERING FREEZE —— 代码冻结，转入"run → observe → record → judge"观察模式。