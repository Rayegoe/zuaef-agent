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
  resource: plugins/zuaef-quant/zuaef_quant/monitor.py
  title: M1 live trading monitor CLI
  evidence: "once/session/ack-buy/ack-sell/status; --state-dir; MARKET_CLOSED/SYSTEM_UNAVAILABLE/NO_TRADE"
- id: sources/zuaef-quant
  resource: tools/quant_p05_reconcile.py
  title: P0.5 reconcile CLI
  evidence: "--config benchmarks/quant/gen1/quant.toml; attribution classes"
- id: sources/zuaef-quant
  resource: plugins/zuaef-quant/zuaef_quant/bridge.py
  title: Quant Telegram event bridge (oneshot + systemd timer)
  evidence: "E1/E2 Agent run；E3/E4/E5 确定性；游标+delivered_ids；checkpoint-after-delivery"
- id: sources/zuaef-quant
  resource: zuaef-quant-spec-v3.1-20260905/00_SOURCE_OF_TRUTH.md
  title: v3.1 Source of Truth
  evidence: "IMPLEMENTED_NOT_PROVEN 边界；T12 晋升条件"
generated:
  by: zuaef-agent
  date: 2026-09-05
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
# 交易时段内连续盯盘（30–60s 间隔；P6 起生产路径为 zuaef_quant.monitor 模块）
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor session --interval 45
# 单次扫描（等价于一次循环节拍，退出码报告机会状态）
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor once
# 用户成交确认（EXECUTED，唯一置位路径；价格/股数由用户给出）
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor ack-buy --symbol 600000 --price 10.5 --shares 500
# 持仓平仓确认
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor ack-sell --symbol 600000 --price 10.9 --shares 500
# 当前状态一览
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor status
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
- 独立重放（raw、market_truth ON）→ 逐笔对账+聚合对比。差异归因 A–F（市场规则差/不支持对等/
Qlib 局限/引擎 bug/无法解释）；任何无法解释的残留 = P0.5 失败。详见 quant-execution-truth。

## 快速看盘（不起 Agent）

```bash
.venv/bin/zuaef-quant scan
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
| --- | --- |
| EastMoney / SSL EOF | 正常（本网络被拒）；数据面已走腾讯/新浪/CSIndex |
| 历史抓取偶发失败 | 腾讯限流；引擎内已有界重试，重跑即可 |
| side environment missing | 确认 `.venv-quant/bin/python` 存在或设 `ZUAEF_QUANT_PYTHON` |
| required command is unavailable | 依赖的可执行/侧环境缺失;确认 `.venv-quant/bin/python` 与 `.venv/bin/zuaef-quant` |
| profile not found | 重装 profile（§5.1 第 3 步） |
| evaluate_strategy already ran this round | 一轮守卫生效（设计行为），写完 Result 即结束 |
| manifest 完整性失败 | `python tools/regen_manifest.py` |
| 扫描全 0 触发 | 正常（S3 条件选择性高）；连续多周 0 触发才构成研究信号 |

## Trading Workbench 运维（2026-09-05 增补，v3.1 基线）

详见 [quant-telegram-workbench](quant-telegram-workbench.md)。本节只记动作。

### 组件与部署

```bash
# M1 monitor（开盘前后手动起，会话结束自动退；--exit-on-close 到 15:00 收）
PYTHONPATH=$PWD/plugins/zuaef-quant .venv-quant/bin/python -m zuaef_quant.monitor session --interval 45 --exit-on-close

# Telegram 事件桥（oneshot + timer，45s 一 tick；tick 内含 Agent run 时 systemd 自动不重叠）
cp ops/systemd/zuaef-quant-bridge.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now zuaef-quant-bridge.timer
systemctl --user status zuaef-quant-bridge.service   # 最近一次 tick 的结果
tail -5 .zuaef-state/quant-bridge/bridge.jsonl       # 通知日志（事件/run_id/投递结果）
```

### 硬规则（真实事故换来的）

1. **改 `.env` 后必须 `systemctl --user restart zuaef-gateway`**——gateway 启动时经
   `AgentSettings.from_env()` 一次性把 `.env` 读进 os.environ；热改对运行中进程无效。
   症状：切 quant-decision 会话后每条消息报 `telegram plugin credentials missing`。
2. **gateway poll 集体失败（空错误消息、每 ~65s 一条、新进程同路径请求秒通）**
   = 进程内连接池/代理隧道半死 → 同样 restart gateway。长驻消费新写 oneshot+timer。
3. bridge 本体免重启：oneshot 每 tick 全新进程，永远重读 `.env`。

### 多机同步（GitHub ↔ opi5）

```bash
git push origin main   # GitHub（Rayegoe/zuaef-agent）
git push opi5 main     # opi5 主机（SSH 直推 /home/orangepi/zuaef-agent）
# opi5 侧等价做法：git pull origin main
```

文档/知识/配置全部是 repo 内文件——git 同步即文档同步；无需额外分发机制。
同步后如 opi5 跑常驻服务（gateway/bridge/monitor），按上面硬规则检查是否需要重启。

### 状态门

proactive 链 = **IMPLEMENTED_NOT_PROVEN**（v3.1 §00）：真实时段"用户零发起端到端回执"
（T12）跑通前不得宣称 PROVEN。
