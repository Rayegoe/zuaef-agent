# Quant 生产链路 · 周一实盘验证运行手册（runbook）

> 首个真实交易时段验证：**2026-09-07（周一）**，A 股时段 09:30–11:30 / 13:00–15:00。
> 生产唯一节点 = **opi5**（orangepi5pro，192.168.31.134，user orangepi）。本机 barry-A901S 只做开发。
> 判定分级：**PASS** / **WARN**（记录、不阻塞）/ **FAIL**（必须处置后再继续）。

---

## 0. 角色与铁律

- **唯一 poller**：同一 bot token 只允许 opi5 gateway 一个 getUpdates 轮询者。本机旧 gateway 已
  `stop + disable`。除非做故障演练，**不要在本机 `systemctl --user start zuaef-gateway.service`**。
- 本机 quant-bridge 是**发送方**（读 alerts.jsonl → sendMessage），不轮询，不破坏唯一性。
- opi5 用户级 journal 为 volatile（persistent 未开）：**日志证据有限的场景用进程/连接级证据**，
  需要 journal 时先 `export XDG_RUNTIME_DIR=/run/user/$(id -u)`。
- 凭据只在 repo 根 `.env`（gitignored）。重置/变更后服务重新读取。

---

## 1. 前置检查（建议周一 09:00 前跑完；周日可先预演一遍全表）

| # | 检查项 | 命令（opi5，除非注明） | 期望 / 通过判据 |
|---|---|---|---|
| 1.1 | 代码三方一致 | 本机：`git log --oneline -1`；opi5：`git log --oneline -1`；`git ls-remote origin main`（走 GitHub） | 三者同一 commit（当前 `7483a75` 或更新） |
| 1.2 | opi5 工作区干净 | `cd ~/zuaef-agent && git status --porcelain` | 空（`.env.bak-*` 已被 gitignore） |
| 1.3 | 常驻服务活性 | `for s in zuaef-gateway zuaef-console zuaef-quant-dashboard; do systemctl --user is-active $s.service; systemctl --user show $s.service -p NRestarts --value; done` | 全部 `active`；gateway NRestarts=0 |
| 1.4 | 代理/隧道 | `systemctl --user is-active sing-box.service`；`curl -sS -x http://127.0.0.1:4000 -m 15 -o /dev/null -w '%{http_code}' https://api.telegram.org/` | sing-box active；tg 返回 3xx |
| 1.5 | OpenRouter 可达 | 同上命令换 `https://openrouter.ai/` | 200 |
| 1.6 | 隧道死恢复法 | `systemctl --user restart sing-box.service && sleep 6 && curl -x http://127.0.0.1:4000 ... https://api.telegram.org/` | 重启后 3xx（tg）/200（openrouter）；GitHub 与网关都依赖它 |
| 1.7 | 量化数据就位 | `du -sh data/workspace/.zuaef-state; ls data/raw | tail; ls data/quant-cache | head` | data 783M 级；raw 有最近交易日 bar |
| 1.8 | 时钟/定时器 | `date "+%A %F %T %Z"`；`systemctl --user list-timers --no-pager | grep quant-monitor` | 时区 CST；下一触发 = **Mon 09:30:00** 与 **13:00:00** |
| 1.9 | 无 409 前提 | 本机：`journalctl --user -u zuaef-gateway --since today --no-pager | grep -c 409` | 0（本机 gateway 未再启动） |
| 1.10 | 投递冒烟（推荐，会真实发一条） | 见下方代码块（1.10-smoke） | 手机 Telegram 收到该消息 |
| 1.11 | dashboard 可达 | `curl -s -m5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/`（console 8765 同法） | 200 |

**1.10-smoke（投递冒烟，真实发送一条到手机。凭据来自 .env，需显式 source）：**

```bash
cd ~/zuaef-agent && set -a && . ./.env && set +a && .venv/bin/python - <<'PY'
from zuaef_telegram.client import TelegramClient
import os
c = TelegramClient(bot_token=os.environ['TELEGRAM_BOT_TOKEN'], chat_id=os.environ['TELEGRAM_CHAT_ID'])
print(c.send_message('[preflight] opi5 quant 投递管线 OK'))
PY
```

**1.x 任一 FAIL → 先处置（见 §6）再开盘。**

---

## 2. 开盘启动检查（09:30 触发 → 09:35 内完成）

| # | 检查 | 命令 | 通过判据 |
|---|---|---|---|
| 2.1 | 会话进程拉起 | `export XDG_RUNTIME_DIR=/run/user/$(id -u); systemctl --user status zuaef-quant-monitor.service -n 6 --no-pager` | `quant_trading_monitor.py session` 进程在跑；无 Traceback |
| 2.2 | 采样循环 | `ps -o pid,etime,cmd -C python | grep monitor`；再等 ≥2 分钟看日志 | 同进程持续采样（非一次性） |
| 2.3 | 心跳/行情 | 上述 journal 内可见周期输出（quotes/opportunity 状态） | 至少 3 个周期连续无异常 |
| 2.4 | alerts 流 | `ls -la workspace/artifacts/quant/trading/`；`wc -l workspace/artifacts/quant/trading/alerts.jsonl`（不存在也正常，记录基准） | 文件存在或首次创建；有内容则记录行数基准 |

**PASS 判据**：2.1+2.2+2.3 全过。**无候选/无 alert ≠ 失败**——空宇宙时 monitor 只做采样与心跳。

---

## 3. 盘中检查点（建议 10:00 / 10:30 / 11:00；下午 13:00 再跑一次 2.x+3.x）

| # | 检查 | 命令 | 通过判据 |
|---|---|---|---|
| 3.1 | 数据新鲜 | `ls -la data/quant-cache 最近修改时间`；必要时 `data/raw/daily` 近 1 日文件 | 存在 2026-09-07 数据或当日更新 |
| 3.2 | 告警→投递 | 若出现 E1/E2/E3/E4/E5 事件：`wc -l workspace/artifacts/quant/trading/alerts.jsonl` 前后对比；手机看 Telegram | alert 落盘后 **≤45s**（bridge tick）送达 |
| 3.3 | 网关稳定 | `ss -tnp 2>/dev/null | grep zuaef-agent`（隔 ~30s 两次）；`systemctl --user show zuaef-gateway -p NRestarts --value` | 同一连接 tuple 无重建；NRestarts=0；无 409 |
| 3.4 | bridge 游标 | `ls -la .zuaef-state/quant-bridge/` | cursor/投递日志存在；无堆积待投 |
| 3.5 | Agent run（E1/E2 时） | `ls .zuaef-state/receipts | tail` | 有新 receipt；run 无 ERROR |
| 3.6 | dashboard 实时 | `curl -s -m5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/` | 200 且页面行情刷新 |
| 3.7 | 无 alert 情形 | 记录「无触发」即可，另跑：`cd ~/zuaef-agent && .venv/bin/python tools/quant_telegram_bridge.py --dry-run` | rc=0（投递管线本身健康） |

---

## 4. 收盘检查（11:30 早盘收 / 15:00 全天收）

| # | 检查 | 通过判据 |
|---|---|---|
| 4.1 | 会话退出 | 收盘后 monitor 应自行退出（`--exit-on-close`，is-active → inactive），journal 有退出依据 |
| 4.2 | T10 日结 | 每日一次的 daily summary 已发出（规则触发时） |
| 4.3 | 状态落盘 | 观察日志/`workspace/artifacts/quant` 有当日增量 |
| 4.4 | 下一触发 | `systemctl --user list-timers | grep quant-monitor` → 下一个交易日 09:30/13:00 已排 |

---

## 5. 失败模式 → 处置速查

| 症状 | 定位 | 处置 |
|---|---|---|
| gateway 不在 active | `export XDG_RUNTIME_DIR=/run/user/$(id -u); journalctl --user -u zuaef-gateway -n 30`；查 drop-in `~/.config/systemd/user/zuaef-gateway.service.d/proxy.conf` | ① 隧道死 → `systemctl --user restart sing-box.service` 复测 1.4；② `systemctl --user restart zuaef-gateway.service` |
| 409 Conflict 再现 | 谁在 getUpdates：本机 `ps -ef | grep -iE 'getUpdates|gateway'` | 停掉第二个 poller；确认唯一性；本机 gateway 勿再 start |
| monitor 空跑/无数据 | `ls data/raw | tail`；universe 状态 | 数据补拉/重跑候选构建；确认 Universe 活跃 |
| bridge 未投递（有 alert） | `ls .zuaef-state/quant-bridge/`；手动 `systemctl --user start zuaef-quant-bridge.service` 复现 | 查 cursor/失败原因；凭据缺失→单元加 `EnvironmentFile=%h/zuaef-agent/.env` |
| 全部 via-proxy 000 | sing-box 隧道节点死（CONNECT 200 但 TLS decode error 特征） | `systemctl --user restart sing-box.service` → 复测 tg/github |
| 部署需回滚 | `git log --oneline -3` | `git reset --hard <好commit>` 后 `bash ops/deploy-opi5.sh`；或 revert 后正常部署 |
| 本机旧网关误启用 | 本机 journal 出现新 409 | `systemctl --user stop + disable zuaef-gateway.service` |

---

## 6. 端到端通过判据（总结）

**PASS（完整链路）**：
1. 09:30/13:00 会话正常拉起并持续采样至收盘退出；
2. 任一真实 alert 在 45s tick 内送达 Telegram（E1/E2 时伴随 Agent run receipt）；
3. 网关全程无 409、NRestarts=0、长轮询连接无重建；
4. 收盘后状态落盘、下一交易日触发已排。

**PASS（空宇宙/无触发日）**：monitor 采样与心跳正常 + 无 error + `--dry-run` rc=0 + 投递冒烟（1.10）通过。

**FAIL**：1.4/2.1/3.3 任一不满足且处置后仍不恢复 → 记录观察、不收盘归档，下一交易日再验。

---

## 7. 运维速查

```bash
# 部署（本机 commit+push 后，opi5 上）
bash ~/zuaef-agent/ops/deploy-opi5.sh          # pull --ff-only + 重启 gateway/console/dashboard

# 隧道/代理
systemctl --user restart sing-box.service       # 隧道节点死时
curl -sS -x http://127.0.0.1:4000 -m 15 -o /dev/null -w '%{http_code}\n' https://api.telegram.org/

# 日志（opi5 journal 为 volatile，需先设 XDG_RUNTIME_DIR）
export XDG_RUNTIME_DIR=/run/user/$(id -u)
journalctl --user -u zuaef-quant-monitor -n 20 --no-pager

# bridge 手动 tick / dry-run
systemctl --user start zuaef-quant-bridge.service
.venv/bin/python tools/quant_telegram_bridge.py --dry-run

# 连接级证据（不依赖 journal）
ss -tnp 2>/dev/null | grep zuaef-agent
systemctl --user show zuaef-gateway -p NRestarts --value
```

<!-- 维护：ops/quant-live-verification.md，随部署闭环入库；执行后在本文件头部记录结果。 -->