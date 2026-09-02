---
title: '内部 Supervisor 循环基础设施 v0.1'
type: 'feature'
created: '2026-08-24'
status: 'done'
review_loop_iteration: 0
baseline_commit: '1b0e46bbf5e67de00a194c3e5b68638b230434f7'
context:
  - 'zuaef-internal-loop-infra-spec-v0.1/SPEC.md'
  - 'zuaef-internal-loop-infra-spec-v0.1/ACCEPTANCE.md'
---

> 本文件仅是构建流程的实施索引。唯一规范权威是
> `zuaef-internal-loop-infra-spec-v0.1/SPEC.md`；本文件不得扩展其范围。

<frozen-after-approval reason="用户已明确指定 canonical SPEC.md 并授权实施">

## Intent

**Problem:** 当前本地 worker、GitHub、ChatGPT Project Supervisor 与人工授权之间仍依赖手工复制粘贴；同时主工作树存在无关未提交改动，传输与 worker 执行必须隔离。

**Approach:** 按 canonical 规范实现一个 stdlib Python 机械传输工具、两条专用 Git 分支/工作树、systemd 用户定时轮询、固定 worker 提示词及运维文档，不改变生产 Agent 或 Console 语义。

## Boundaries & Constraints

**Always:** 精确执行合并后的 `.supervisor/NEXT.md`；保持主工作树分支、状态和文件不变；worker 使用 `BASE_COMMIT` 的全新隔离工作树；仅发布显式且公开安全的报告、tracked patch 与 attachments；实现并验证 Gate A–E，Gate F 只准备真实环境。

**Ask First:** 需要真实推送、创建远端分支、安装/启用 systemd timer、修改 ChatGPT Project 指令或执行手机 canary 时，必须由用户或 Supervisor 明确授权。

**Never:** 引入第二 Supervisor、工作流引擎、注册表、状态数据库、哈希/manifest、重试栈、自动选择 TASKS 项、自动合并 worker 代码或修改生产 runtime/business plugin/StepPersistence/Console 语义；不得 reset、stash、clean 或切换主工作树。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 报告发布 | worker outbox 与可选 tracked diff | 专用 report 工作树提交并推送 REPORT、可选 patch/attachments | Git 失败非零退出并保留本地证据 |
| 控制无变化 | remote control head 等于 last-started | 不启动 worker | 成功 no-op |
| 单条新控制 | 合法 NEXT 与可用 BASE_COMMIT | 先记录 head，再从精确 base 创建 fresh worktree，启动一次 | worker 退出后仍机械发布报告 |
| 控制缺口 | last-started 到 head 间有多条未消费提交 | 不启动 worker | 明确 `CONTROL_GAP` 非零退出 |
| 缺失报告 | worker 未写 REPORT | 仅生成观察到的进程/传输失败事实 | 不制造语义结论 |

</frozen-after-approval>

## Code Map

- `AGENTS.md` -- 只追加 Supervisor 启动时的窄权限规则；现有 runtime doctrine 只读。
- `tools/supervisor_loop.py` -- 新建唯一机械命令面：bootstrap、publish-report、sync-control、run-next。
- `tests/test_supervisor_loop.py` -- 使用临时 bare Git remote/worktrees 覆盖 Gate B–D 与机械失败路径。
- `docs/internal-loop/README.md` -- 合并 canonical 运维、协议和 Gate F 准备说明，不创造新权威。
- `prompts/internal-loop/CODEX_WORKER_PROMPT.md` -- 固定 bounded worker prompt。
- `ops/systemd/zuaef-supervisor-sync.{service,timer}` -- 每 60 秒一次 outbound poll。
- `src/zuaef_agent/**`, `plugins/**`, `docs/runtime-refoundation/TASKS.md` -- 本任务只读，禁止修改。

## Tasks & Acceptance

**Execution:**
- [x] `AGENTS.md`, docs, prompt 与 systemd units -- 建立权威、运维和轮询边界。
- [x] `tools/supervisor_loop.py` -- 实现四个 bounded commands、工作树隔离、单锁与唯一 polling fact。
- [x] `tests/test_supervisor_loop.py` -- 实现 Gate A–E 的确定性验收覆盖。
- [x] `.zuaef-supervisor/REPORT.md` -- 写本次 Supervisor Report 并停止。

**Acceptance Criteria:**
- Given 主工作树有无关修改，when publish/sync/run-next，then 主工作树 branch/status/files 不变且 worker 基于精确 `BASE_COMMIT`。
- Given 报告、无变更/单条/重复/缺 base/多条控制等状态，when 执行命令，then行为符合 `ACCEPTANCE.md` Gate C–D，且无自动 main 变更。
- Given authority 文件，when 审查 Gate E，then worker 仅执行合并 NEXT、TASKS 仅为 backlog/evidence、完成后 STOP。
- Given Gate A–E 完成，when 交付，then Gate F 保持未模拟，并给出真实 canary 的精确命令与状态。

## Spec Change Log

## Design Notes

Git 原生 branch/commit/worktree/PR 提供现有身份、历史、隔离与人工授权；本地只持久化 `last-started-control`，不创建并行状态系统。控制 head 在启动前记录，以明确选择 at-most-once 自动启动而非自动重试。

## Verification

**Commands:**
- `uv run pytest -q tests/test_supervisor_loop.py` -- Gate B–E 的确定性测试全部通过。
- `uv run ruff check AGENTS.md docs/internal-loop prompts/internal-loop tools/supervisor_loop.py ops/systemd tests/test_supervisor_loop.py` -- 新增范围 lint 通过。
- `uv run ruff check .` -- canonical lint gate 通过。
- `uv run pytest -q` -- canonical test suite 通过，或明确报告与现有未提交工作相关的偏差。

**Manual checks:**
- 核对 git diff 仅包含授权文件面和本次报告，不触碰已有无关改动；Gate F 只准备、不伪造。

## Suggested Review Order

**机械控制与权威边界**

- 从单次轮询入口理解 exact-commit、gap 与 at-most-once 设计。
  [`supervisor_loop.py:612`](../../tools/supervisor_loop.py#L612)

- 独立 run-next 仍须证明 merged control blob 与隔离 worktree。
  [`supervisor_loop.py:514`](../../tools/supervisor_loop.py#L514)

- bootstrap 先验证 fetch/push remote，再创建 detached transport worktrees。
  [`supervisor_loop.py:323`](../../tools/supervisor_loop.py#L323)

**报告通道与失败事实**

- publisher 只复制显式 outbox、tracked patch 与安全 attachment。
  [`supervisor_loop.py:349`](../../tools/supervisor_loop.py#L349)

- Codex 入口固定当前 CLI 参数、cwd、sandbox 与 stdin。
  [`supervisor_loop.py:494`](../../tools/supervisor_loop.py#L494)

**操作与权限**

- Supervisor 启动时 NEXT 是唯一执行权威，TASKS 仅为 backlog。
  [`AGENTS.md:139`](../../AGENTS.md#L139)

- 运维文档给出 bootstrap、timer、恢复与真实 Gate F 路径。
  [`README.md:26`](../../docs/internal-loop/README.md#L26)

- oneshot unit 固定已检查的 Codex 路径并允许长 worker 完成。
  [`zuaef-supervisor-sync.service:6`](../../ops/systemd/zuaef-supervisor-sync.service#L6)

**确定性验收**

- dirty primary、report patch 与 public attachment 边界由真实 Git 验证。
  [`test_supervisor_loop.py:310`](../../tests/test_supervisor_loop.py#L310)

- control gap、崩溃去重与 stale NEXT 路径均被固定。
  [`test_supervisor_loop.py:405`](../../tests/test_supervisor_loop.py#L405)

- fake Codex 子进程验证 argv、cwd、stdin 与自动报告发布。
  [`test_supervisor_loop.py:651`](../../tests/test_supervisor_loop.py#L651)
