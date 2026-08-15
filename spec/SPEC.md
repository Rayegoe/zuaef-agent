---
id: SPEC-zuaef-agent-core
companions:
  - brownfield.md
  - capability-proof-gate.md
sources: []
---

> **Canonical contract.** 本 SPEC 与 `companions:` 中的文件共同构成下游构建、测试和验证必须遵守的完整合同。

# 可信共享 ZUAEF Agent Core v1

## Why

Barry 需要围绕一个共享 runtime 扩展 Product Research、Hardware Scout、WordPress、Video Knowledge 等业务，而不是为每个业务重造 Agent。v1.1 的真正目标不是建立通用 Agent framework，而是证明一个业务能力可以通过同一个 ZUAEF runtime，使用真实 PydanticAI Agent、真实 Toolset/Capability 和真实输入，产生经 host 验证的 Artifact、Evidence 与 Receipt；审批可以暂停后继续，失败也留下可追溯 Receipt。

## Capabilities

- **CAP-1 — 共享执行缝**
  - **intent:** 业务方能自行组合 Agent、Toolset、Capability 与类型化依赖，再交给同一个 runtime 执行。
  - **success:** 一个业务 Research Toolset 无需修改核心 Agent 即可通过 `execute_run(agent, deps, …)` 实际调用工具，并获得统一 RuntimeOutcome 与 Receipt；`run_task()` 仅调用该共享入口。

- **CAP-2 — Host 验证的运行事实**
  - **intent:** 模型只能提出结果，host 负责验证状态、Artifact 与 Evidence 后再固化运行事实。
  - **success:** TerminalRun 的 Artifact 引用包含已验证路径、存在性、大小与 SHA-256；Evidence 只接受可解析的 artifact、knowledge、tool-effect 引用，并能证明属于本次运行；不可验证的 completed 声明被降级且写入 Receipt。

- **CAP-3 — 原生暂停与续跑**
  - **intent:** 需要审批的工具能以 PausedRun 结束当前调用，并在外部批准或拒绝后通过 PydanticAI 原生协议继续。
  - **success:** 首次调用返回 DeferredToolRequests、message history、conversation id 和 pause Receipt；续跑使用 DeferredToolResults、相同 conversation id 与新 run id；拒绝不执行副作用，已 settled effect 不被重复执行，未知副作用转为 blocked/unresolved_effect。

- **CAP-4 — 证据型知识写入不变量**
  - **intent:** 通用文件工具只能读取知识区，只有 Knowledge Capability 能按知识类型与来源规则写入。
  - **success:** concept、claim、method、reference 缺少 sources 时被拒绝；允许无来源的 note 类型被显式列举；保留 id、非法 limit、越界路径与 symlink 逃逸被拒绝，文档写入可恢复且索引可重建。

- **CAP-5 — 可复现运行契约**
  - **intent:** 开发者能在锁定环境中真实导入和执行 core、runtime、provider resolver、CLI、业务 Toolset、pause/resume 与 Receipt verification。
  - **success:** `uv sync --frozen`、`uv run --frozen pytest` 和 `uv run --frozen zuaef-agent …` 可重复执行；普通 model ID 路径不加载不需要的 OpenAI-specific 模块；request、tool-call、total-token 限制和不完整 usage 被如实记录。

- **CAP-6 — 受控垂直切片能力证明**
  - **intent:** 操作者能用一个本地真实 source markdown 和业务 Research Toolset 一次证明共享核心，而不引入网络采集变量或新平台层。
  - **success:** `capability-proof-gate.md` 的唯一 Gate 使用真实模型生成经验证 report Artifact、evidence-backed Knowledge、approval pause/approve/deny continuation、成功与可控失败 Receipt，并在通过后停止 Stage A。

## Constraints

- `execute_run()` 接收已组合的 Agent 与 deps，不负责构建 Agent；`build_agent()` 负责 composition，`run_task()` 只是 convenience wrapper。
- RuntimeOutcome 只有 TerminalRun 或 PausedRun；approval pause 不是 `RunSummary.status`，业务终态仍为 completed、partial、blocked。
- Pause Receipt 与 terminal Receipt 是不同形态（`state=paused` + `pending_approvals` + settled evidence + `usage_complete`），不得用 `status=partial` 冒充。
- Artifact 归属验证不得依赖 mtime；runtime 在执行前对 `workspace/artifacts/**` 已存在文件记录 SHA-256 快照，验证时要求新建或 hash 改变。
- Receipt 义务从 run acceptance 开始：run_id 分配前的配置/CLI/依赖错误是 process error，不要求 Run Receipt，也不为它们新建错误管理框架。
- CLI 为 PausedRun 定义与 completed/partial/blocked 可区分的专用退出语义。
- ZUAEF v1.1 不承诺 exactly-once external effects；副作用 `started` 且无 settled result 时不得自动重放，纯读工具只允许显式 safe replay。
- 复用 PydanticAI/Harness 的 DeferredToolRequests、DeferredToolResults、message history、conversation id、UsageLimits、StepPersistence 与 tool-effect ledger；不自研 durable state machine 或第二套事实账本。
- v1.1 Evidence 仅允许 artifact、knowledge、tool effect 三类可解析引用，不建立 Evidence Ontology。
- `knowledge/*.md` 是事实，`index.md` 是可重建 projection；不为文件与索引引入数据库事务。
- 只实现唯一 Capability Proof Gate 的阻断项；Gate 通过前不得增加后续业务、并发或生产硬化抽象。

## Non-goals

- 不构建 AgentRegistry、PluginRegistry、BusinessAgentFactory、每业务一个 Agent class、多 Agent、graph runtime 或 generic ingestion framework。
- 不引入 background jobs、向量数据库、图数据库、长期 memory、并发执行框架、自研 durable interpreter、Web/API 服务或部署治理。
- 不在本阶段实现 YouTube、ASR、Hardware Scout 或 WordPress adapter；Gate 通过后只替换 source/business adapter。
- 不承诺 crash 后外部副作用 exactly-once。

## Success signal

在 `uv.lock` 可复现环境中，同一 `execute_run()` 让真实 PydanticAI Agent 与业务 Research Toolset 处理真实本地 source，生成经 host 验证的 report、knowledge 和 Receipt；审批能停/续，拒绝不产生副作用，未知副作用不自动重放，任一可控运行失败仍留 Receipt。唯一 Gate 变绿后立即停止 Stage A。

## Assumptions

- 执行环境会提供受支持的真实模型凭据或 OpenAI-compatible endpoint；若不可用，Capability Proof Gate 明确失败，不用 TestModel 冒充真实结果。
