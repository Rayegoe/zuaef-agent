---
type: concept
title: '观察模式日常运行：命令、工件、冻结规则与重启准入'
tags:
- quant
- operations
- freeze
- zuaef-quant
sources:
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: Implementation summary + 实操指南
  evidence: "§5 实操指南; §6 重启开发的准入规则; §7 命令速查与故障排查; §3.3 工件地图"
- id: sources/zuaef-quant
  resource: benchmarks/quant/gen1/STATUS.md
  title: Program status (frozen 2026-09-02)
  evidence: "Decisions frozen at P4.5; Known limitations"
- id: sources/zuaef-quant
  resource: profiles/quant-decision.toml
  title: Quant-decision profile
  evidence: "plugin quant; allow_capabilities = true"
- id: sources/zuaef-quant
  resource: tools/quant_trading_monitor.py
  title: M1 live trading monitor CLI
  evidence: "once/session/ack-buy/ack-sell/status; --state-dir; MARKET_CLOSED/SYSTEM_UNAVAILABLE/NO_TRADE"
- id: sources/zuaef-quant
  resource: tools/quant_p05_reconcile.py
  title: P0.5 reconcile CLI
  evidence: "--config benchmarks/quant/gen1/quant.toml; attribution classes"
generated:
  by: zuaef-agent
  date: 2026-09-04
---

# 观察模式日常运行

## 一次性准备（README §5.1；换机时对照）

```bash
uv sync                          # 主环境（Python 3.13；生产安装不带 quant 组）
uv sync --group quant            # 需要在主环境跑 quant 数据工具/测试时
uv venv --python 3.12 .venv-quant
uv pip install -p .venv-quant/bin/python "akshare==1.18.94" "pyqlib==0.9.7"
mkdir -p ~/.config/zuaef/profiles && cp profiles/quant-decision.toml ~/.config/zuaef/profiles/
# .env 里配好 LLM_API_BASE / LLM_API_KEY / LLM_MODEL
```

## 唯一日常动作：每日一次 Agent 决策（README §5.2，交易时段内）

```bash
ZUAEF_QUANT_PYTHON=$PWD/.venv-quant/bin/python \
ZUAEF_QUANT_REPO_ROOT=$PWD \
.venv/bin/zuaef-agent run \
  --profile quant-decision --request-limit 10 --tool-calls-limit 12 \
  "Live decision check for the A-share active strategy. FIRST tool call: get_live_signals()..."
```

形状：先 `get_live_signals()` → 严格按触发证据判定 **NO_TRADE / ENTER_CANDIDATE**（空触发=NO_TRADE，
不许硬凑候选）→ 调一次 `record_decision_brief`（decision_id `brief-live-<unixseconds>`、
signal timestamp、strategy name、why/invalidation/expected_holding、raw trigger facts 或 'none'）→ 停止。
**不调其他工具、不写文件。**

## M1 交易时段循环（v0.1，spec v2.0-optimized M1；2026-09-04 增补）

交易时段内的连续盯盘由确定性循环接管（Agent 不轮询；实质变化才进告警流）：

```bash
# 交易时段内连续盯盘（30–60s 间隔）
.venv/bin/python tools/quant_trading_monitor.py session --interval 45
# 单次扫描（等价于一次循环节拍，退出码报告机会状态）
.venv/bin/python tools/quant_trading_monitor.py once
# 用户成交确认（EXECUTED，唯一置位路径；价格/股数由用户给出）
.venv/bin/python tools/quant_trading_monitor.py ack-buy --symbol 600000 --price 10.5 --shares 500
# 持仓平仓确认
.venv/bin/python tools/quant_trading_monitor.py ack-sell --symbol 600000 --price 10.9 --shares 500
# 当前状态一览
.venv/bin/python tools/quant_trading_monitor.py status
```

- 机会生命周期 **WATCH → NEAR → READY → INVALIDATED**；`EXECUTED` 只能由 `ack-buy` 置位
  （人为外部动作，绝不自动成交）。NEAR=到冻结入场条款的最差归一化剩余差距在近带内；
  READY=冻结扫描触发 + 语义门武装。
- 持仓为一等公民：仅由 ack-buy 创建、按冻结 S3 退出规则监控（止损/止盈/收盘破 MA5/最大持有天数）、
  仅由 ack-sell 关闭。
- forward 观察（D+1/3/5/8、MFE/MAE）只对真实 NEAR/READY/EXECUTED/CLOSED 记录从缓存日线累积——
  绝不 mock、绝不回填成成交。
- 状态落 `workspace/artifacts/quant/trading/`；`--state-dir` 隔离 fixture/重放与真实结果。
- 业务区分：`MARKET_CLOSED`（非交易时段，无合成活动）/ `SYSTEM_UNAVAILABLE`（断连/数据不可信，
  绝不报成 NO_TRADE）/ `NO_TRADE`（数据健康但冻结策略无触发）。

## P0.5 双引擎对账（2026-09-04 增补；spec pack 03 P0.5）

独立重放与研究面的一致性不是靠 NAV 相等，而是逐笔归因；验证后无需每日跑：

```bash
.venv-quant/bin/python tools/quant_p05_reconcile.py [--config benchmarks/quant/gen1/quant.toml]
```

同策略+同 intents（重生成 intents 元素级比对证明可复现）→ Qlib 向量面（qfq、market_truth OFF）
+ 独立重放（raw、market_truth ON）→ 逐笔对账+聚合对比。差异归因 A–F（市场规则差/不支持对等/
Qlib 局限/引擎 bug/无法解释）；任何无法解释的残留 = P0.5 失败。详见 quant-execution-truth。

## 快速看盘（不起 Agent）

```bash
uv run --group quant python tools/quant_live_scan.py
```

## 记录动作：每日一行观察日志

`benchmarks/quant/gen1/OBSERVATION_LOG.md` 追加：`| 日期 | 时间 | 扫描只数 | 触发数 | Agent action | scan 耗时 | brief 延迟 | 备注 |`
brief JSON 自带完整字段，日志行仅供肉眼巡检；**无 DB**。

## 出现真实 trigger 时（观察期的目的）

**不要开发任何东西。** 前几笔**人工结算**，字段从简：signal time/price、brief time/price
（→ price drift）、next open 成交价、D+1/D+3/D+5/D+8 收盘、MFE/MAE、实际可成交性
（一字板/停牌/流动性异常）。这几行就是第一笔 forward evidence；不要写结算程序——
等市场告诉你真正重要的字段是什么。

## 冻结期规则（README §6）

**禁改清单**：S4 及后续调参、P6/P7 框架、dashboard、watcher、PIT platform、10-run A/B、
SpendLimits、broker。唯一例外：PIT universe 仅在"准备做任何盈利声明"时作为前置门解冻。

**重启开发的准入**（强规则：没有来自真实市场的新问题，不开新 feature）：
- A. **≥10 个真实 trigger** → 人工结算复盘 → 决定 A/B 实验/是否自动化；
- B. **观察期足够长仍 0 trigger** → "策略密度不足"成立 → 重启的是策略/宇宙研究（不是框架）。

观察期只看五个指标（README §5.5）：Trigger frequency、Signal→Brief latency、
Signal→Brief price drift、Subsequent return path、Agent veto/增量判断。
积累 30–50 个 trigger 后的唯一重要 A/B：A=每个 trigger 直接 paper enter；
B=Agent 有权 WATCH/NO_TRADE；比较期望值、回撤、坏交易剔除率、错失的好交易。
**"scanner+LLM 是否优于 scanner alone"尚未证明——这是产品核心问题。**

## 故障速查（README §7.2 节选）

| 症状 | 处置 |
|---|---|
| EastMoney / SSL EOF | 正常（本网络被拒）；数据面已走腾讯/新浪/CSIndex |
| 历史抓取偶发失败 | 腾讯限流；引擎内已有界重试，重跑即可 |
| side environment missing | 确认 `.venv-quant/bin/python` 存在或设 `ZUAEF_QUANT_PYTHON` |
| cannot locate repository tooling | 从仓库根运行或设 `ZUAEF_QUANT_REPO_ROOT` |
| profile not found | 重装 profile（§5.1 第 3 步） |
| evaluate_strategy already ran this round | 一轮守卫生效（设计行为），写完 Result 即结束 |
| manifest 完整性失败 | `python tools/regen_manifest.py` |
| 扫描全 0 触发 | 正常（S3 条件选择性高）；连续多周 0 触发才构成研究信号 |