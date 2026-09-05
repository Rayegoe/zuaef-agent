# v3.1 修改前运行基线

采集时间：2026-09-05 17:45–17:48 Asia/Shanghai；本文件是本次首次人工文件编辑。

- 分支 main；完整 HEAD `6714ca722b2dd2c1f7c92e457af5e817ff9762e4`。`git ls-remote origin refs/heads/main` 返回同一提交；HEAD...origin/main 为 0/0，无未推送提交。提交主题与规范评审基线一致。
- 原始 git status：`.codebase-memory/artifact.json` 已修改；`zuaef-quant-spec-v3.1-20260905/` 未跟踪。保留，不 reset/clean/stash/checkout/merge。
- 用户级 `zuaef-gateway.service` active；`zuaef-quant-bridge.timer` active，每 45 秒调用 oneshot bridge；17:46:24 日志显示成功退出。supervisor-sync timer active。系统级无 quant unit；进程列表未发现 Quant monitor/Workbench serve。8799 是 docuwiki，不是 Quant Workbench。
- M1 权威实现 `tools/quant_trading_monitor.py`；生产目录 `workspace/artifacts/quant/trading/`，包含 state/opportunities/positions/forward JSON、alerts.jsonl、soak.jsonl。最后 heartbeat 为 2026-09-04 19:10:35+08，状态 MARKET_CLOSED，symbols_scanned=0；不是当前实时健康证明。
- 当前 positions open/closed 均空；forward.observations=[]。不能把规范中的「true trade records 5」解释为此 canonical ledger 中 5 次成交。
- 候选快照 `workspace/artifacts/quant/business/candidate_snapshot.json`，as_of 2026-09-03 18:27:56+08，candidate_count=50，base_count=800。handoff 为 `data/quant-cache/candidates/active_symbols.json`。
- 固定策略 `benchmarks/quant/gen1/active.toml`，s3_longer_hold，pullback=-0.05，volume_ratio=1.80，hold=8；属于 DEMO_ACTIVE_STRATEGY，不是盈利证明。
- 六工具在 `plugins/zuaef-quant/zuaef_quant/toolset.py`：evaluate_strategy、get_live_signals、record_decision_brief、record_trade_outcome、get_trading_context、render_quant_business_artifact。主 Agent/Core 无需变动。
- Workbench `tools/quant_serve.py` 与 `tools/quant_render_business_dashboard.py`；GET `/api/quant/now`，POST `/api/quant/ack-buy`、`ack-sell`、`skip`，写入边界为 loopback。当前未发现监听实例，待隔离测试验证实现。
- Bridge `tools/quant_telegram_bridge.py`；`.zuaef-state/quant-bridge/state.json` 为 cursor/去重状态，bridge.jsonl 为通知日志（采集时不存在）；timer 配置 `ops/systemd/zuaef-quant-bridge.*`。不发送测试 Telegram 消息。
- 最近业务页面 `workspace/artifacts/quant/business/business.html` 修改于 09-05 12:32；last_scan.json 修改于 09-03 18:28。PIT 报告 `workspace/artifacts/quant/semantic/p0.3_pit_audit_REPORT.md` 与 `pit_audit_20260903T045824Z.json`。
- 历史数据 `data/quant-cache/`；候选源 membership 检索时间 CSI300=09-02、CSI500=08-28，金融源检索时间09-02。这些当前档案不能静默倒推十日历史可用性。research evaluator 仍非严格 PIT production replay。
- proactive_event_delivery=IMPLEMENTED_NOT_PROVEN：本次为周六，无真实交易时段零用户发起 E1/E2 收件证明；timer 成功和单测不能替代该证明。

差异：规范「host/runtime healthy」是先前业务事实，本机此刻只证实 Gateway/Bridge timer 活跃；monitor/Workbench 没有运行，live-forward=0。实现须保留真实缺口，不能编造实时运行或历史 PIT 证据。

采集命令：git status/log/branch/rev-list/ls-remote；systemctl --user list-units/list-timers；systemctl list-units；ps -eo pid,args；ss -ltnp；journalctl --user -u zuaef-quant-bridge.service；读取上述 canonical JSON、候选、策略及脚本。

## 2026-09-05 执行后基线更新

- HEAD 仍为 `6714ca722b2dd2c1f7c92e457af5e817ff9762e4`，origin/main 一致。
- 本工作树包含 v3.0→v3.1 规格替换、`tools/quant_v31.py`、`tests/test_quant_v31.py`、M1 replay seam、isolated v31 artifacts。未 reset/checkout/merge。
- 授权环境核心回归：222 passed in 3.01s；非授权沙箱仅 4 个 Workbench HTTP 用例因 127.0.0.1 bind PermissionError 失败，属环境限制，不是实现回归。
- 生产 canonical files 的 SHA256 在 replay/shadow/research/experiment 前后全部一致；forward observations=0，positions open/closed=0。
- Bridge state 未发送新通知：offset=0，delivered_ids=[]。真实交易时段 proactive acceptance 仍未证明。
- 存在 `zuaef-harness-alignment-spec-pack-v0.1/` 未跟踪目录；本次未修改。
