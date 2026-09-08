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
  **2026-09-07 操作者决定移除**：每次运行都向群里发 ACCEPTED 卡片属噪音，
  terminal 卡片保留 run id 与 `/inspect` 提示，`/inspect` 与 Console 亦不依赖
  它。实现与测试已删除（规范 §11 在本部署点作废，依 §33 记录分歧）。
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

T010 生产级 provider 断供演练、T012 真实飞书 ACCEPTED → live →
LIMIT_REACHED → /inspect 与 Quant 独立刷新。真实飞书入站操作需要操作者配合；
测试 adapter 不等于真实飞书证明。（T009 部署后 smoke 已完成，见下节。）


## T009 部署后验证（commit 5f8940c，14:05–14:10 CST）

```text
4 units active（console / quant-dashboard / gateway / feishu-gateway）
2 timers enabled（monitor / bridge）
GET :8765/api/health → {"ok":true,"version":"0.1.1"}，bundle index-lwb_HMiR.js
GET :8787/api/quant/now → market_phase OPEN_PM（host 派生）、runtime HEALTHY
monitor restart 后 state.json 写出 cycle_at / market_tick_at（age 42s）/
freshness CURRENT，51 symbols，data_trust PASS
```

monitor 是 timer 驱动的一次性 session，本可等下一 tick 取新代码；为当日完成
T007/T008 生产验证手动 restart 一次，重启后立即恢复心跳与扫描（重启安全）。

事故 receipt 77c45d0e 经新投影（真实数据，非 fixture）：

```text
status limit_reached · activity LIMIT_REACHED · profile quant-decision
requests 12 · tool_calls 25 · input 746,586 · output 20,928 · usage_complete true
usage_limits {} → Configured limits UNKNOWN（旧 receipt，诚实未知）
limit_boundary UNKNOWN（不从 token 数猜测）
runtime_reason The next request would exceed the request_limit of 12 …
```

## T010 故障隔离

测试级（全绿）：

- provider 异常 → ACCEPTED 仍先行、receipt failed
  （test_accepted_is_sent_even_when_the_model_never_responds）。
- UsageLimitExceeded → limit_reached receipt 冻结 limits
  （test_limit_reached_receipt_freezes_configured_usage_limits，真实 runtime seam）。
- Quant monitor 全链路 200 测试零模型参与；Console projection/inspection 测试
  零 provider 参与 —— 两条平面在构造上互不依赖。

生产级：事故 receipt 在部署后立即可通过 Console 投影与 inspection 复盘
（上方输出）；monitor/dashboard 与 gateway 独立 restart 各自恢复。

未证明（需操作者）：对生产 gateway 主动断 provider 的现场演练（会降级在用的
飞书通道，未在无人在场时执行）；T012 真实飞书五步流。

## M2 业务补丁：Chat Surface Cleanup + Runtime Analysis Watchlist（2026-09-07 操作者指令）

两条产品边界修正，均由操作者基于真实飞书体验提出。

### 1. 业务聊天不再泄漏运行标识

completed 回复 = 纯 presentation（模型回答），不再附 `✅ Completed` / `Run:`
前缀。Run ID 只出现在：FAILED / LIMIT_REACHED 卡、无 presentation 的回退卡、
`/status`、`/inspect`、Approval 卡。`normal chat = business surface，
Console = operational surface`。

### 2. 三层股票宇宙（candidate pool / analysis watchlist / positions）

002654 事件暴露的语义错误：把「不在自动候选池」等同成「不能研究」。

- **candidate pool**：算法所有，只有它产生 READY/NEAR；用户不能从聊天塞票。
- **analysis watchlist**（新增一等能力）：用户关注事实，
  `workspace/artifacts/quant/watchlist/<scope>.json`，host tool 独占写、
  不进 Git。scope = 绑定 Case 优先，否则聊天 channel
  （`CoreDeps.bindings["analysis_scope"]`，opaque，Quant Core 不知道客户概念），
  多群/多客户天然隔离。`legacy_watchlist.toml` 保持 repo 种子/兼容基线，
  运行时永不写入。
- **positions**：monitor 照旧，一等公民。

Agent 新增 3 个 host tools（plugins/zuaef-quant/zuaef_quant/toolset.py）：

- `get_symbol_context(symbol)`：任意 6 位 A 股的按需独立诊断（报价+host 派生
  新鲜度、三层归属、冻结 S3 clause 距离、MA5 证据、scan 新鲜度、limitations）
  —— 由 monitor 新子命令 `symbol-context` 提供，诊断距离永不产生交易状态。
- `get_analysis_watchlist()`：读本 scope 的名单（无 scope 绑定 → fail-closed）。
- `update_analysis_watchlist(action=add/remove, symbols=[...])`：本地可逆、
  无需交易 approval（不下单、不改策略），invalid 代码拒绝。

Monitor 扩展：`quote universe = candidates ∪ positions ∪ analysis watchlist
(all scopes union)`，机会层只迭代候选 —— 自选票有行情但**永远不会 READY/NEAR**
（有专门测试：给自选票 READY 级行情也只进报价面）。state.json 记录
`analysis_watchlist`。`get_trading_context` 不暴露跨 scope 并集（隔离）。

指令面：QUANT_INSTRUCTIONS 增加三层宇宙语义与「不在候选池 ≠ 不能研究」的
回答口径（含关注/取消关注的确认话术）。

测试：`tests/test_quant_watchlist.py` 16 例（store 校验/scope 逃逸防护/
cap/隔离、monitor 报价面加入但 lifecycle 隔离、symbol-context 语义、toolset
scope 绑定与 fail-closed、bridge bindings 线程化）；既有 gateway/routing/e2e
断言随 surface 改动更新。全量回归 1150 passed + manifest 校验通过。

## Research Sandbox（CodeMode）接入（2026-09-07 操作者方向确认）

按「Codex 建能力、Agent 用能力解决未知问题」的边界，接入 harness CodeMode
作为 quant 的第二类计算能力（固定 evidence tools 之外的研究型沙盒）：

- `create_plugin(config={"code_mode": true})` 时追加 `CodeMode` capability：
  evidence tools（get_trading_context / get_symbol_context / get_live_signals
  / get_analysis_watchlist / evaluate_strategy）被包装为 run_code 内的 Python
  可调用；只读 mount 暴露 `data/quant-cache`（权威日线缓存）到沙盒
  `/quant-cache`；默认 30s/256MiB backstop；生产策略、ledger、trading
  artifacts 不在沙盒可达范围。默认（无 flag）不启用，缺失缓存 fail-loud。
- profile `quant-decision.toml` 启用 code_mode；指令面写明沙盒语义：临时
  推导（事件研究/相似历史 forward 分布/横截面比较/自定义窗口统计），结果
  作为 DERIVED host fact 进入回复（须报样本量与窗口）；反复被问的分析应
  提议固化为永久工具，不允许一次性代码变成影子管线。
- 暂未启用 WebSearch/WebFetch（Market Intelligence 层）：按能力准入规则
  需要真实失败证据（某次客户问题因缺外部信息而答不出）再开，避免为
  「可能有用的感知」付费。Durable research memory 复用现有 Decision
  Brief / knowledge / Case 事实，不新建记忆服务。

测试：`TestCodeModeSandbox` 4 例（默认无沙盒、无 flag 不启用、启用后
只读 mount + 五工具白名单、缺缓存 fail-loud）。全量回归 1160 passed。

## T011 HEAD 回归与双端同步（2026-09-08）

部署提交 5f8940c 之后又有 8 个提交（chat bridging、research service v0.2、
learning 等），在当前 HEAD `9ef8b29` 重取 T011 证据：

```bash
timeout 590 .venv/bin/pytest -q tests/
# 1220 passed, 22 warnings in 220.24s
```

`web-ui/` 与 `src/zuaef_agent/web/static/` 自 5f8940c 起零变更
（`git diff --name-only 5f8940c..HEAD` 两路径为空），前端 check exit 0 /
build 产物 `index-lwb_HMiR.js` 证据沿用部署时点，不重复证明未变更事实。

同步与运行面（2026-09-08 17:06 CST，只读）：

- `git ls-remote`：origin 与 opi5 的 main 均为 `9ef8b29` = 本地 HEAD，
  无待部署缺口。
- OPi5：4 units active（console / quant-dashboard / gateway / feishu-gateway）、
  2 timers enabled（monitor / bridge）、`:8765/api/health` → ok。
- `:8787/api/quant/now`（收盘后）：`market_phase=MARKET_CLOSED`（host 派生）、
  `last_scan_at=15:00:17` 收盘收束扫描、`market_tick_at=null → freshness
  UNKNOWN` —— 收盘扫描不取行情，缺失事实保持 UNKNOWN 不伪造，符合 T007 语义；
  runtime HEALTHY、`stale=false`。
- OPi5 工作树漂移（未处理，留操作者决定）：
  `profiles/quant-decision.toml` 有未提交修改；
  `workspace/workspace/artifacts/supervisor-build-loop-blueprint.md` 为未跟踪
  嵌套路径。

至此 M2 本地可独立完成的部分全部收束；剩余两项均需操作者在场。
