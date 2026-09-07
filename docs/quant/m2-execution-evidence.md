# M2 执行与验收证据

日期：2026-09-07。状态：实施中，尚非 M2 PROVEN。

## T000 基线与事故

本地 `git branch --show-current && git rev-parse HEAD`：main，
`01db73b813d28cbbc3c900fbceeb9b40c60048e3`。
OPi5 `/home/orangepi/zuaef-agent` 同一 HEAD，`git status --short` 与
`git diff --stat` 均为空。运行树优先，无远端代码差异需要回收。
本地原有代码图缓存改动和未跟踪飞书规格目录保留。

只读检查 OPi5 `.zuaef-state/receipts/77c45d0eae864e6d9cb16220e2d92eb9.json`：

| 字段 | 实际值 |
|---|---|
| execution_state | limit_reached |
| error 的明确原因 | The next request would exceed the request_limit of 12 |
| boundary kind | request_limit（直接来自 error，非 token 推测） |
| requests / tool_calls | 12 / 25 |
| input_tokens / output_tokens | 746586 / 20928 |
| cache_read_tokens | 587776 |
| usage_complete | true |
| historical usage_limits | 原 receipt 无此字段；其他 limits 未知 |
| tool_effect_facts | 27（25 completed，2 started） |
| unresolved_effects | 2：list_directory、find_files |
| artifact_facts | 0 |
| started_at | 2026-09-07T04:48:09.742138Z |
| finished_at | 2026-09-07T04:51:55.434089Z |
| elapsed | 225.691951 秒 |
| composition profile | quant-decision，quant + telegram |

规格 12:18 是示例，实际事故为上海时间 12:48–12:51。usage 完整和 effects
未解决是独立维度；不能因为前者为 true 把后者抹掉。未读模型 hidden reasoning，
未修改事故 receipt。

## 现有能力与基线测试

REUSED：ReceiptStore/StepPersistence、串行 Gateway、确定性 Inspection、
SSE `run_changed` invalidation、Timeline 主面板、Quant canonical ledger/锁、
NOW endpoint 与 30 秒轮询、现有 systemd units、loopback 写接口保护。

EXTEND/MISSING：午休 phase、ACCEPTED、历史 limits、limit 诊断展示、/inspect、
live summary、显式 ThinkingPart 过滤、receipt-only 计数、Quant 时间/日线证据。

基线命令与结果：

```bash
timeout 180 .venv/bin/pytest -q tests/test_receipt_store.py tests/test_web_console.py tests/test_cli_resume.py
# 63 passed, 20 warnings
timeout 180 .venv/bin/pytest -q tests/test_gateway_service.py tests/test_gateway_renderer.py tests/test_gateway_feishu.py tests/test_gateway_telegram.py
# 104 passed, 2 warnings
.venv/bin/pytest -q tests/test_quant_trading_monitor.py tests/test_quant_business.py tests/test_quant_v31.py tests/test_quant_freshness.py tests/test_quant_plugin.py
# 200 passed
cd web-ui && npm run check
# exit 0
```

Quant 初次沙箱执行有 4 个 loopback socket PermissionError，提升权限重跑全绿。
这是执行环境限制，不作为产品失败或略过测试。

## T009 部署前 OPi5 实测

```bash
ssh opi5 'systemctl --user is-active zuaef-console zuaef-quant-dashboard zuaef-gateway zuaef-feishu-gateway'
# active × 4
ssh opi5 'systemctl --user is-enabled zuaef-quant-monitor.timer zuaef-quant-bridge.timer'
# enabled × 2
ssh opi5 'curl -fsS http://127.0.0.1:8765/api/health'
# {"ok":true,"version":"0.1.1"}
ssh opi5 'curl -fsS http://127.0.0.1:8787/api/quant/now'
# 2026-09-07 13:33:19+08:00: runtime HEALTHY, data_trust PASS,
# heartbeat_at=last_scan_at=13:33:02+08:00, symbols_scanned=51
```

读 systemd unit 确认 Console :8765 与 Dashboard :8787 均绑定 127.0.0.1；
monitor 使用 `session --interval 45 --minutes 150 --exit-on-close`，timer 在工作日
09:30/13:00 启动。bridge timer 45 秒。无需新 daemon。

已有 601799 EXIT_ALERT 的历史理由仅含 `close_below_ma5 (76.32 < 77.10)`，
未给 close_date，不能给旧事件事后伪造日期；最新 bar 证据与原 trigger 必须区分。

## T001–T008 实现（2026-09-07 下午完成，全量回归绿）

REUSED 保持不变：ReceiptStore/StepPersistence、串行 Gateway、SSE invalidation、
现有 systemd units、loopback 写保护。零新存储，core.py/composition.py/plugin_api.py
未改动。

- T001 `market_phase()`：monitor 与 stdlib dashboard 双实现，`in_session` 变为其
  投影；`run_cycle` 非交易时段直接写 phase（PRE_OPEN/OPEN_AM/LUNCH_BREAK/OPEN_PM/
  MARKET_CLOSED），`cmd_session --exit-on-close` 在 LUNCH_BREAK 收束，13:00 timer
  重启；`cmd_cycle` 对午休返回 0。边界由 `TestMarketPhase` 13 例 + dashboard
  mirror 7 例钉死（含 UTC 04:18→12:18 SH 的时区换算与 12:18 事故回放）。
- T002 `render_run_accepted()`：deterministic、无模型、`start_profile_run()` 前
  发送；`ZUAEF_CONSOLE_PUBLIC_BASE_URL` 合法时附 `?run=` 链接，带凭据/查询串/
  非法 scheme/空白一律不猜。测试钉死 texts[0]=ACCEPTED 且模型抛错时仍先发。
- T003 `RunReceipt`/`PauseReceipt` 增 additive optional `usage_limits`，
  `execute_run` 在验收时冻结三项 limit；旧 receipt 无该字段仍可读（显式测试）。
- T004 LIMIT_REACHED 一等投影：terminal 卡片（usage、configured limits、
  boundary=UNKNOWN 不猜、runtime reason、artifacts/unresolved、/inspect 提示，
  presentation 不参与）；`project_run` 暴露 activity/usage_complete/usage_limits/
  error；usage 计数 receipt 优先，事件派生仅作回退，无事实则 UNKNOWN 不补零。
- T005 `/inspect`：host-only 命令，读 `session.last_terminal_run_id` 的
  deterministic inspection（markdown ≤7500 字符），零模型调用（计数断言）。
- T006 Console：trajectory 顶部诊断面板（activity/limits/boundary/reason）、
  `?run=` 深链、终态 failed/limit_reached 自动切到 Inspection 面板；analysis
  文案降级为可选二级能力。SSE invalidation 未动，无新协议。
- T007 时间语义：state.json 增加 `cycle_at`/`heartbeat_at`/`last_scan_at`/
  `market_tick_at`/`market_phase`；NOW 快照 state 事实优先、soak 仅回退；
  tick 缺失 → freshness UNKNOWN；EXIT 卡分别展示原始触发证据与最新日线观察
  （close_value/close_date/ma5_value/bar_source），不回填历史触发日期；
  `close_below_ma5` 历史确认 bar 改名 `latest_confirmed_close_below_ma5` 并带
  close_date。策略参数未动。
- T008 Dashboard：市场时段改为 host 派生 phase 展示，新增周期时间/行情 tick/
  行情新鲜度行；Agent 状态不参与 phase 计算。

回归证据：

```bash
timeout 590 .venv/bin/pytest -q tests/
# 1137 passed, 22 warnings（含本轮新增 37 例）
cd web-ui && npm run check   # exit 0
cd web-ui && npm run build   # dist → src/zuaef_agent/web/static/dist
.venv/bin/python tools/regen_manifest.py && .venv/bin/pytest -q tests/test_manifest_integrity.py
# 3 passed
```

新增/收紧的测试：monitor `TestMarketPhase`（15）、business `TestMarketPhaseMirror`
+ `TestNowSnapshotTimeSemantics`（12）、renderer accepted/limit 卡（3）、gateway
service ACCEPTED 先行 + `/inspect` 两例（3）、bridge usage_limits 冻结集成（1）、
receipt 旧格式兼容（1）、web console limit_reached/旧 receipt 投影（2）。

## 待补验收

T009 部署后 smoke、T010 故障隔离、T012 真实飞书 ACCEPTED → live →
LIMIT_REACHED → /inspect 与 Quant 独立刷新。真实飞书入站操作需要操作者配合；
测试 adapter 不等于真实飞书证明。

