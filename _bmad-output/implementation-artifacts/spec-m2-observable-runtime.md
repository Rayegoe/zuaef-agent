---
title: 'M2 可观察运行时与实时控制界面'
type: feature
created: '2026-09-07'
status: in-progress
baseline_commit: 01db73b813d28cbbc3c900fbceeb9b40c60048e3
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="用户已明确授权执行 M2 全部任务">

## Intent

让运行状态、耗时、工具、usage、停止原因及有效工件直接来自持久事实，Quant deterministic runtime 独立于模型持续运行。用户已授权实施及 OPi5 验收，无需重新审批实现规格。

## Boundaries & Constraints

复用 StepPersistence、ReceiptStore（terminal truth）、GatewayStore（routing）、monitor canonical ledger、now_snapshot。串行 Gateway 不变；不改策略参数、冻结 S3、Core/composition/plugin ABI、approval、loopback。不得增加 store、调度器、额外模型回合、隐藏思维展示。缺失事实 null/UNKNOWN。只按既有 BUILD_MANIFEST 合同更新受影响条目。当前代码图缓存与未跟踪飞书规格目录属于用户，保留。

## I/O & Edge-Case Matrix

| 输入 | 预期 |
|---|---|
| 工作日 09:29:59/09:30/11:29:59/11:30/12:18/12:59:59/13:00/14:59:59/15:00 | PRE_OPEN/OPEN_AM/OPEN_AM/LUNCH_BREAK/LUNCH_BREAK/LUNCH_BREAK/OPEN_PM/OPEN_PM/MARKET_CLOSED |
| 周末 | MARKET_CLOSED |
| slow fake run | host ACCEPTED 先于 start_profile_run 及首次模型请求，随后 terminal |
| 未配置 public URL | 只显示真实 run ID，不猜主机地址 |
| 旧 receipt | 可读，无历史迁移，usage_limits 默认空 |
| LIMIT_REACHED | 完整/partial usage、历史 limits、bounded runtime reason、artifacts、unresolved effects；不根据 token 猜 boundary |
| /inspect | 最近 terminal run 的 deterministic inspection，零模型调用；无 run 清楚说明 |
| 无 market tick/daily bar 日期 | null/UNKNOWN，不替换为 fetched_at/cycle_at/今日 |
| ThinkingPart | 不出现在 API/页面 operational projection |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/runtime.py:410 execute_run` 已创建 UsageLimits、捕获 UsageLimitExceeded；`finalize_terminal:231`、`_build_paused:354` 原位追加当次 limits。
- `src/zuaef_agent/models.py:42/74` RunReceipt/PauseReceipt 缺 limits。
- `src/zuaef_agent/gateway/service.py` _start_run 已 admission、分配 ID、保存 active、读取历史、同步 start_profile_run；_handle_command 增 /inspect。保留 profile routing、session、approval。
- `src/zuaef_agent/gateway/renderer.py` 纯函数；render_terminal 目前 presentation 优先导致 limit 原因隐藏。
- `src/zuaef_agent/web/inspection.py:170` 已 bounded content-free inspection；复用 readers load_run_facts，不通过 HTTP 自调用。
- `src/zuaef_agent/web/projector.py:206/249` response.parts 未显式过滤 thinking；usage_summary:466 与 run_view:488 step 缺失可能将 receipt requests 显示为零，应修复。
- `web-ui/src/views/console-view.ts:156` 已 run_changed EventSource +150ms HTTP refetch；`trajectory-view.ts` Timeline 已一级面板；前端在 web-ui/src 修改并编译 static，不重写。
- `tools/quant_trading_monitor.py:306` in_session 两端含等号，run_cycle:333 将所有非session写 MARKET_CLOSED；cmd_cycle/cmd_session 同步边界。renderer stdlib mirror 同步。
- `tools/quant_render_business_dashboard.py` now_snapshot 与现有 NOW 顶栏、30s polling 复用。
- `docs/quant/README.md` 运维说明；`zuaef-quant-spec-v3.1-20260905/00_SOURCE_OF_TRUTH.md` 量化权威，修改前阅读。

## Tasks & Acceptance

实现责任：本执行 worker 负责本地 M2 代码、测试、前端编译、docs/quant/README.md 与 BUILD_MANIFEST；主代理负责 OPi5 实际检查、部署与实机验收报告。你不是唯一工作者，不撤销他人改动。实施期间不要调用其他 build 工作流重启规划，直接按此规格执行；可用 graph 定位，结果不足 fallback。

- [x] T000 本地/OPi5 HEAD 同基线、远端干净。事故 receipt request_limit=12，12 requests、25 tool_calls、usage_complete=true、input=746586、output=20928、2 unresolved、0 artifacts，04:48:09.742138Z—04:51:55.434089Z。未修改 receipt。
- [x] T001 market_phase pure host + renderer mirror，session 午休可退出、13点 timer 可重启。边界测试。
- [x] T002 admission 后、start_profile_run 前 deterministic render_run_accepted，full ID/profile/RUNNING；可选 ZUAEF_CONSOLE_PUBLIC_BASE_URL 仅合法无凭证配置 URL，使用实际前端 route；测试无模型依赖及顺序。
- [x] T003 additive optional usage_limits 冻结 run 当次 request/tool/token limits，terminal/pause 全路径写入；resume 现有语义不变。
- [x] T004 projection/inspection/terminal renderer 显示 LIMIT_REACHED、elapsed、configured limits、observed counts、usage_complete、bounded error、artifacts、unresolved；boundary 无可靠事实则 UNKNOWN。处理仅 receipt 无 step 的计数。
- [x] T005 /inspect、HELP_TEXT、bounded renderer，从 session.last_terminal_run_id 调现有 inspection，零 LLM。
- [x] T006 扩展现有 run header live summary：profile/model/start/finish/counts/tokens/usage/activity；activity 仅 persisted facts 推导 RUNNING_MODEL/RUNNING_TOOL/PAUSED/SETTLING/COMPLETED/FAILED/LIMIT_REACHED/UNKNOWN。保留 SSE invalidation；Timeline、tools、artifacts、reason、unknowns 可见。失败默认 Inspection，Analysis 明示 optional/consumes budget/can fail。过滤 hidden thinking 并测试。
- [x] T007 明确 cycle_at/market_tick_at(nullable)/last_scan_at/heartbeat_at；close_below_ma5 证据附 close_value/close_date/ma5_value/bar_source，只有前日 bar 就标 latest_confirmed_close_below_ma5，不改 EXIT policy。
- [x] T008 Quant 顶栏展示 phase/runtime health/heartbeat/last real scan/data trust/freshness/READY/NEAR/positions/exit alerts；模型无参与。Console 可选 configured business link，不 iframe。
- [ ] T010 本地故障注入：真实执行边界中不可用 provider 与 usage exceeded；receipt/inspection可读；在同样 provider 不可用配置下 monitor/NOW/dashboard不调用模型。隔离临时状态，禁止写生产 ledger，禁止断开整个主机网络。（测试级已绿，见证据文档；生产级 provider 断供演练待操作者在场。）
- [x] T011 全量回归与前端 checks/build，old receipt/pause/resume/approval/artifact/routing/Feishu/Telegram/ledger lock/write owner/security；只更新变更 pinned entries。
- [ ] T009/T012 主代理：OPi5 现有 units/loopback API、部署、实机 provider failure、飞书 ACCEPTED→live→LIMIT_REACHED→/inspect 与 Quant持续可用；不能把 fake 测试当真实飞书证明。（部署 5f8940c + 部署后 smoke + T007/T008 生产投影已验；2026-09-08 复核 origin/opi5=HEAD=9ef8b29、HEAD 回归 1220 passed；实机 provider failure 演练与真实飞书五步流待操作者。证据：docs/quant/m2-execution-evidence.md。）

## Verification

基线：Quant 200 passed；receipt/web/resume 63 passed；gateway/service/renderer/Feishu/Telegram 104 passed；前端 npm run check exit 0。
实现后执行 `.venv/bin/pytest -q` 与 web-ui `npm run check`/`npm run build`，若沙箱阻止 socket 或 async，申请提升。每项记录命令/结果；未证明项保留。

## Spec Change Log

## Design Notes

这是一次明确获授权的跨层产品目标，按用户 T000→T001→T002→T003/T004→T005/T006→T007/T008 顺序实施。bmad 通用重新审批、拆分和 no remote ops 建议由用户的 EXECUTABLE M2 授权覆盖；不扩大业务行为。runtime-refoundation backlog T006 未收敛与此 operational M2 范围不同，不推进该研究任务。
