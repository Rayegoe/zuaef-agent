---
type: concept
title: 'Trading Workbench：事件驱动人机交易助理（架构、契约与运维教训）'
tags:
- quant
- workbench
- telegram
- event-bridge
- operations
sources:
- id: sources/zuaef-quant
  resource: zuaef-quant-spec-v3.1-20260905/00_SOURCE_OF_TRUTH.md
  title: v3.1 spec pack — Source of Truth（当前权威）
  evidence: "Trading Workbench / loopback write adapters / six-tool capability / Telegram document delivery / one-shot bridge + systemd timer 均 IMPLEMENTED；proactive 链 = IMPLEMENTED_NOT_PROVEN"
- id: sources/zuaef-quant
  resource: plugins/zuaef-quant/zuaef_quant/bridge.py
  title: Quant Telegram event bridge (oneshot)
  evidence: "byte-offset cursor + delivered_ids；ordered line-by-line checkpoint-after-delivery；E1/E2 Agent run + delivery-authority guard；E3/E4/E5 确定性文案；SYSTEM_RECOVERED 确定性证据规则；T10 日报复用 load_real_trend"
- id: sources/zuaef-quant
  resource: plugins/zuaef-quant/zuaef_quant/freshness.py
  title: Quant Freshness & Natural Response Spec v0.1 §3–§5
  evidence: "FRESH/NOT_SCANNED/STALE/MARKET_NOT_OPEN/INSUFFICIENT_EVIDENCE 全部 host 派生；absence of observation != observed zero"
- id: sources/zuaef-quant
  resource: plugins/zuaef-telegram/zuaef_telegram/toolset.py
  title: send_artifact_to_supervisor — host-scoped operator self-delivery
  evidence: "固定收件人（无 recipient 参数）；resolve()+is_relative_to(delivery_root)+扩展名白名单+≤20MB；无 approval；客户审批边界不动"
- id: sources/zuaef-quant
  resource: plugins/zuaef-quant/zuaef_quant/monitor.py
  title: M1 monitor — canonical ledger file lock + CLI ack alerts carry ts
  evidence: ".ledger.lock fcntl 序列化并发写；POSITION_OPENED/CLOSED/HUMAN_SKIP 告警含 ts（事件契约）"
generated:
  by: zuaef-agent
  date: 2026-09-05
---

# Trading Workbench（Phase 1 Dashboard + Phase 2 主动助理）

## 一句话

把 Trading Workbench 从"用户主动问"（Pull）升级为"Runtime 主动报"（Push）：
**Runtime 发现事实 → Agent 解释事实 → Telegram 把事实送给人**；LLM 永远不产生
READY/EXIT 等确定性状态，也永远不是投递权威。

## 系统地图（谁连谁）

```text
Market/Data ──> zuaef_quant.monitor (M1, 45s)             # 确定性扫描 + 机会状态机
                  │  写 canonical truth（.ledger.lock 串行化）
                  ▼
   workspace/artifacts/quant/trading/                     # state/positions/opportunities/
                  │                                       # alerts.jsonl/soak.jsonl/forward.json
                  ├────────────> zuaef_quant.dashboard.render（静态 business.html + /api/quant/now）
                  ├────────────> get_signal_board / get_positions / get_validation_status
                  │              （按意图隔离的模型只读投影，前两者含 freshness 5 态）
                  ▼
   alerts.jsonl（durable 事件流）
                  │
                  ▼
   zuaef_quant.bridge（oneshot，systemd timer 45s）
                  │  byte 游标 + delivered_ids（源 reset 安全）
                  ├─ E1 NEW_READY / E2 POSITION_EXIT_ALERT ─> start_profile_run("quant-decision")
                  │        （interpretation-only：prompt 硬约束 + receipt 守卫）
                  ├─ E3 LIVE_CONNECTION_LOST / E4 DATA_UNTRUSTED / E5 OPENED/CLOSED ─> 确定性文案
                  ├─ SYSTEM_RECOVERED（in-session + unavailable=false + 心跳≤90s 才发一次）
                  └─ T10 收盘日报（continuity 复用 Dashboard 同一 load_real_trend 实现）
                  ▼
   zuaef-telegram TelegramClient（send_message / send_document）
                  ▼
   Supervisor（Telegram）
```

并发写路径有三条（bridge 只读；monitor cycle 与 ack CLI 都写）→ monitor 用
`.ledger.lock`（fcntl）把 canonical 账本写入串行化。

## 关键契约

1. **唯一投递权威 = bridge**。E1/E2 的 Agent run 是 interpretation-only：
   prompt 硬约束 + host 守卫（receipt `tool_effect_facts` 出现 telegram-send
   完成 → 不转发不补发，记 `DELIVERY_AUTHORITY_VIOLATION`）。
2. **游标 ≠ 投递身份**。byte-offset 只表示"读到哪"；`delivered_ids`
   （`type:symbol:ts`，上界 500）承担防重发。源文件 truncate/rotate（`st_ino`
   变化或 size<offset）→ 归零重扫，不重发。
3. **ordered, line-by-line, checkpoint-after-delivery**。发送成功才把游标推进到
   该行行尾（原子 tmp+rename）；Telegram 失败 → 游标不动，下 tick 原地重试；
   Agent 失败 → 降级确定性文案即视为已投递（§22.1）。
4. **freshness 由 host 派生**（freshness.py）：`get_signal_board` / `get_positions` 返回
   `freshness_status/freshness_reason`，模型禁止自己从日期推断新旧；
   STALE 判定只看数据日，不要求 scan 可见（"未见 scan 记录"≠"从未扫描"）。
5. **事件只在状态跃迁时发射**；LIVE_CONNECTION_LOST/DATA_UNTRUSTED monitor 侧
   1/day 去重；NEAR/WAIT/MARKET_CLOSED/NO_TRADE 永不主动推送。
6. **路径安全是能力边界不是 prompt 约束**：`send_artifact_to_supervisor` 无
   recipient 参数、host 固定 delivery/ 根 + 白名单 + 大小上限，模型无收件人
   决策权；客户外发审批（wordpress 路径）与此完全隔离。

## 运维教训（真实事故，勿重复）

| 事故 | 特征 | 根因 | 处置 |
| --- | --- | --- | --- |
| gateway poll 集体失败 3.5h | 每 ~65s 一条空消息 `surface poll failed`；新进程同路径请求秒通 | 本地代理隧道半死 + gateway 进程内 httpx 连接池复用坏连接；进程不死故 systemd 不重启 | `systemctl --user restart zuaef-gateway`；oneshot+timer 的 bridge 设计即由此教训而来 |
| credentials missing 刷屏 | 切到 quant-decision 后每条消息报 `TELEGRAM_CHAT_ID` 缺失 | gateway 启动时经 `AgentSettings.from_env()` 把 `.env` 读进 os.environ 一次；之后改 `.env` 对运行中进程无效 | 同上 restart；**硬规则：改 `.env` 后必须重启 gateway** |

衍生规则：长驻进程 + 本地代理的组合，故障会让"半死状态"长期存在（空异常消息、
固定 65s 节奏）；新写常驻消费优先 oneshot+timer（systemd 保证 tick 不重叠）。

## 证明边界（v3.1 §00）

proactive 链 `Runtime → alert → Bridge → Agent(E1/E2) → Bridge → Telegram` =
**IMPLEMENTED_NOT_PROVEN**：单测全绿 + 手动投递成功都不升级为 PROVEN——
必须由一次真实 A 股时段的"用户零发起端到端回执"（T12）晋升。
工作定语：事件驱动的人机决策助理，不是自动交易系统。
