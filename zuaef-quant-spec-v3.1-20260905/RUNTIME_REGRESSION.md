# 当前运行契约回归

2026-09-05；测试口径 research/fixture，不是 replay 盈利或 live-forward 证据。

## 修改前回归

命令：

```sh
.venv/bin/python -m pytest tests/test_quant_trading_monitor.py tests/test_quant_business.py tests/test_quant_plugin.py tests/test_quant_telegram_bridge.py tests/test_quant_replay.py -q
```

结果：**201 passed in 7.44s**，无 skip/fail。

覆盖：M1 WATCH/NEAR/READY/INVALIDATED/EXECUTED、时间/语义门、position exit、D+1/3/5/8、SKIP 不改 lifecycle；Workbench NOW 和真实本地 HTTP 200/400/403；六工具 composition、canonical outcome adapter、业务渲染；Bridge E1/E2 解释、失败 fallback、成功后 checkpoint、失败 retry、reset 去重、发送权限、daily continuity；现有 research replay/reconciliation。

## 真实 CLI 隔离 smoke

目录 `/tmp/quant-v31-runtime-rsgbi950`（保留用于检查，不是生产证据）。每条命令前缀：

```sh
.venv/bin/python tools/quant_trading_monitor.py --state-dir /tmp/quant-v31-runtime-rsgbi950
```

顺序后缀：

```sh
once
ack-buy --symbol 600000 --price 10 --shares 100 --venue paper --time 2026-09-04T10:00:00+08:00
skip --symbol 600001 --price 12 --note 'isolated verification only' --time 2026-09-04T10:05:00+08:00
ack-sell --symbol 600000 --price 11 --shares 100 --venue paper --time 2026-09-05T10:00:00+08:00
status
```

五条 exit=0；once=MARKET_CLOSED、symbols=0。隔离 ledger 中一个 CLOSED position、一个 SKIP observation、三个 forward observations；这些都是人为 fixture，不是实盘、收益证据或真实 human samples。

执行前后直接逐文件 bytes 比较以下 canonical 文件，全部相等（没有新增 hash）：

- trading/state.json、positions.json、forward.json、opportunities.json、soak.jsonl；
- benchmarks/quant/gen1/active.toml；
- data/quant-cache/candidates/active_symbols.json。

生产 forward.observations 仍为0，positions open/closed仍为空。

## 安全与证明边界

Workbench HTTP tests 实际只绑定临时127.0.0.1端口；非loopback模式的 POST 拒绝经测试，未对 LAN 暴露写接口。现场没有 Workbench/monitor 进程，故测试成功不能写成服务已部署运行。

Bridge timer 运行和单元测试均不足以证明交易时段零用户发起主动投递。维持 IMPLEMENTED_NOT_PROVEN；没有发送测试 Telegram 消息，没有修改 Bridge 配置和递送状态。
