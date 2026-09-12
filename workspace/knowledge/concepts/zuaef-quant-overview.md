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
  resource: zuaef-quant-spec-v3.1-20260905/00_SOURCE_OF_TRUTH.md
  title: v3.1 spec pack — Source of Truth（当前权威；v2.0-optimized 为其下位输入）
  evidence: "M1 monitor / canonical acks / forward D+1..D+8+MFE/MAE / Workbench + loopback writes / six-tool capability / Telegram document delivery / one-shot bridge + timer 全部 IMPLEMENTED；proactive 链 IMPLEMENTED_NOT_PROVEN"
- id: sources/zuaef-quant
  resource: zuaef-quant-final-spec-v2.0-optimized/00_START_HERE.md
  title: Final spec v2.0 (optimized, executable baseline 2026-09-03；历史契约层)
  evidence: "Status FINAL/EXECUTABLE; North Star; spec v2.0 replaces v1.1/v1.2; product success"
- id: sources/zuaef-quant
  resource: zuaef-quant-final-spec-v2.0-optimized/02_AGENT_AND_HARNESS.md
  title: Agent participation + live decision harness
  evidence: "deterministic layer vs Agent layer; Decision Mode; Research Mode; Agent is not the polling loop"
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: ZUAEF A股决策 Agent 实现总结与实操指南
  evidence: "§1 项目定位; §3 系统架构; §4 实现情况清单"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/STATUS.md
  title: Program status (frozen 2026-09-02)
  evidence: "P5.5 ENGINEERING FREEZE; proof table"
- id: sources/zuaef-quant
  resource: plugins/zuaef-quant/zuaef_quant/monitor.py
  title: M1 Live Trading Loop v0.1
  evidence: "session loop; opportunity lifecycle; ack-buy/ack-sell; state dir"
- id: sources/zuaef-quant
  resource: tools/quant_p05_reconcile.py
  title: P0.5 dual-engine reconciliation
  evidence: "same frozen inputs; attribution classes A-F; residual UNEXPLAINED fails P0.5"
generated:
  by: zuaef-agent
  date: 2026-09-05
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
       └─ QuantDecision Capability（领域指令 + QuantToolset，6 个确定性工具）
            ├─ evaluate_strategy                  ┐
            ├─ run_live_scan                      ┼─ subprocess 隔离（.venv-quant Python 3.12）
            ├─ record_decision_brief              │
            ├─ record_trade_outcome               │（canonical ack：仅记录事实，不下单）
            ├─ get_signal_board/get_positions/   ├─ 窄化只读 canonical trading 投影
            │  get_validation_status             │（候选池/账户/验证成熟度各自隔离）
            ├─ get_trading_context               │（P7.3 真实 E2 证据保留的 deferred fallback）
            └─ render_quant_business_artifact     ┘─ 确定性渲染业务 HTML（artifacts/quant/delivery/）
                 └─ 确定性工具：quant_core / quant_eval_qlib / quant_live_scan / quant_trading_monitor / quant_render_business_dashboard
                      └─ 数据面：akshare 1.18.94（腾讯历史/新浪快照/CSIndex 成分/qt.gtimg.cn 实时）
```

2026-09-03/04 增补（spec v2.0-optimized 实现）：

```text
确定性侧新增两个工具（Agent 不轮询、不结算）：
├─ quant_trading_monitor（M1 交易时段循环，30–60s）
│    活跃 watch 宇宙 → 报价 → 时机 → 策略条件 → 机会状态机（WATCH/NEAR/READY/INVALIDATED）
│    → 实质变化告警流；EXECUTED 仅由用户 ack-buy 置位；持仓按冻结 S3 退出规则监控
│    状态落 workspace/artifacts/quant/trading/（file-native，无新平台）
└─ quant_p05_reconcile（P0.5 双引擎对账）
     同一冻结策略+同一冻结 intents → Qlib 研究面（qfq，market_truth OFF）
     vs 独立 A 股重放（raw，market_truth ON）→ 逐笔对账 + 聚合对比
     差异必归因（A 市场规则差  B 不支持对等  C Qlib 局限  D/E bug  F 无法解释）；F 残留= P0.5 失败
```

2026-09-05 增补（spec v3.1 基线）：Trading Workbench 事件驱动层

```text
Trading Workbench（详见 concepts/quant-telegram-workbench.md）
├─ Phase 1 Dashboard：business.html（NOW 层 + 口径徽章 + Action Queue + Timeline）
│    + loopback-only 写适配器（quant_serve POST → canonical ack CLI）
├─ Phase 2 主动助理：quant_telegram_bridge（oneshot + systemd timer 45s）
│    durable alerts → E1/E2 Agent 解释（interpretation-only，bridge 是唯一投递权威）
│    E3/E4/E5 确定性文案；SYSTEM_RECOVERED 确定性证据；T10 日报复用 Dashboard verdict
├─ freshness 契约（host 派生 5 态：FRESH/NOT_SCANNED/STALE/MARKET_NOT_OPEN/INSUFFICIENT_EVIDENCE）
│    get_signal_board / get_positions 直接给 freshness 事实，模型禁止自推新旧
└─ zuaef-telegram：send_document + send_artifact_to_supervisor（host 固定收件人/范围，
     operator self-delivery 无 approval；客户外发审批边界不动）

权威 spec：`zuaef-quant-spec-v3.1-20260905/`（00_SOURCE_OF_TRUTH.md 为当前权威；
源不一致时：本机运行树/services/canonical artifacts > GitHub main ≥ 2026-09-05 基线 > v3.1 pack > 旧文档；
"Never reset a working runtime to satisfy stale documentation"）。
v2.0-optimized 降为下位契约层；v1.0-final 保留为历史。

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
| --- | --- |
| Research Engine Proof | **PASS**（P0 真实数据 + P1 Qlib 评估 + P2 一致性） |
| Self-learning Loop Proof | **PASS**（P4：S1→S2 被否决→S3，一轮一个 mutation） |
| Profitability Proof | **NOT YET**（最好子策略 ≈ +0.37% 年化/29 笔，噪声内，有意停止 in-sample 追寻） |
| Live Decision Product | **FIRST PROOF PASS**（2026-09-02 盘中实测 NO_TRADE，86s 端到端延迟） |

**当前阶段**：P5.5 ENGINEERING FREEZE 持续 —— 观察模式本体已由 M1 交易时段循环接管
（连续盯盘 + 持仓管理 + forward 观察，见 quant-live-ops）；P0.5 双引擎对账已实现并进入可信对等路径；
Trading Workbench Phase 1+2 已实现（Dashboard + 事件桥 + 工件投递 + freshness 契约）。
代码仍冻结：新功能必须来自真实市场派发的任务。

**证明边界（v3.1 §00）**：proactive 链 `Runtime → alert → Bridge → Agent(E1/E2) → Bridge →
Telegram` = **IMPLEMENTED_NOT_PROVEN**——单测全绿或手动投递成功都不晋升；必须由一次真实
A 股时段的"用户零发起端到端回执"（T12）晋升为 PROVEN。工作定语：事件驱动的人机决策助理，
不是自动交易系统。盈利能力 UNPROVEN 不变。
