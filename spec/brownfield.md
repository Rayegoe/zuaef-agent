# Brownfield 基线与契约映射

## 迁移问题更正

原始 `zuaef-agent-core-refactor-v1.1` 成果包包含两个 Skill、`.env.example` 与 `.gitignore`，且 SHA-256 与 `BUILD_MANIFEST.json` 一致。本地目标缺失是隐藏文件未被迁移且迁移后未执行 manifest 校验，不是原成果包不完整。

当前四个文件已原样补齐，完整 manifest、权限、11 项既有测试与 Ruff 均通过。后续修复是增加 package/checkout integrity 验收，使隐藏运行必需文件不能静默丢失。

## 当前结构与目标结构

当前主路径：

```text
run_task → build_agent → agent.run_sync → receipt
```

目标主路径：

```text
business composition ── Agent + deps ──┐
                                       ├─ execute_run
run_task convenience wrapper ──────────┘      ├─ usage limits
                                              ├─ pause / continuation
                                              ├─ exception boundary
                                              ├─ host outcome verification
                                              ├─ StepPersistence evidence
                                              └─ Receipt
```

该拆分不引入 registry 或 factory。每个业务自行 composition，但必须经过同一 receipt-producing runtime。

## 六个核心契约

| 契约 | 现有缺口 | 最小修复边界 |
| --- | --- | --- |
| CAP-1 共享执行缝 | `run_task()` 内建 Agent，业务 toolset/deps 无法进入主路径 | 提取接收 Agent 与 deps 的 `execute_run()`；wrapper 复用它 |
| CAP-2 Host truth | status/artifacts/evidence 全部信任模型；异常可能无 Receipt | 模型提交引用，host 验证后形成 TerminalRun；terminal/pause 都落 Receipt |
| CAP-3 Pause/resume | `output_type=RunSummary`；无 deferred/history continuation | RuntimeOutcome 区分 TerminalRun/PausedRun，按 PydanticAI 原生参数续跑 |
| CAP-4 Knowledge invariant | FileSystem 可写 knowledge；sources 全部可空；路径边界不完整 | protected `knowledge/**`、按类型强制 sources、containment 与原子文档写 |
| CAP-5 Reproducibility | 无 lock；provider eager import；测试仅静态触碰核心 | `uv.lock`、frozen 命令、lazy provider import、真实 runtime contract tests |
| CAP-6 Capability proof | 只有 scaffold 与 11 项局部测试，无真实业务结果 | 一个本地 source + Research Toolset 的真实模型垂直切片 |

## RuntimeOutcome 合同

```text
RuntimeOutcome
├── TerminalRun
│   ├── RunSummary: completed | partial | blocked
│   └── terminal Receipt
└── PausedRun
    ├── DeferredToolRequests
    ├── message_history
    ├── conversation_id
    └── pause Receipt
```

Continuation 用原 message history 与 DeferredToolResults 开启新 run；新旧 run id 不同，conversation id 相同。Pause 不伪装成业务终态。

Pause Receipt 与 terminal Receipt 是不同形态：`state=paused`，携带 `pending_approvals`、已 settled evidence 句柄与 `usage_complete`；不得用 `status=partial` 冒充，否则 CLI/Telegram/Web 会把"等审批"渲染成"任务失败"。

v1.1 不承诺 exactly-once。Tool effect 为 settled 时不得因 continuation 重复执行；副作用 `started` 但没有 completed/failed 时标记 `unresolved_effect` 并 blocked，等待人工处理。纯读工具只有在调用方显式声明 safe replay 时才能重放。

## Host outcome verification

模型提交的是候选引用，不是事实。Host 至少验证：

- Artifact：规范化相对路径、workspace containment、存在、regular file、本次运行归属、size、SHA-256。
- Artifact 归属不依赖 mtime：runtime 在执行前对 `workspace/artifacts/**` 已存在文件记录 path 与 SHA-256（有界快照）；验证时要求文件为新建（快照中不存在）或 hash 与快照不同，不需要 event sourcing。
- Knowledge：规范化 knowledge id、文件存在、frontmatter 的 run id 与来源规则、本次运行归属。
- Tool effect：StepPersistence 中的 run id、tool call id、tool name 与 settled/unresolved 状态。

Receipt 保存 verified 引用及校验字段，而不是自然语言 `evidence: ["I checked X"]`。任何 load-bearing 引用不可验证时，不得 finalized 为 completed。

## Knowledge 最小正确性

- Harness FileSystem 将 `knowledge/**` 配为 protected：读允许、写拒绝；Knowledge Capability 是唯一写入口。
- `concept`、`claim`、`method`、`reference` 必须至少一个 SourceRef；`project-note`、`decision`、`user-authored-note` 可无来源，但类型必须显式匹配。
- `knowledge_id == "index"`、非法/越界 id、根外 symlink、`limit <= 0`、`limit > MAX_SEARCH_RESULTS` 均明确拒绝。
- 文档使用同目录 temp file + `os.replace`；`knowledge/*.md` 是 authoritative truth，`index.md` 可在失败后重建，不使用数据库事务。

## 依赖、usage 与 CLI

- 提交 `uv.lock`；验收只运行 `uv sync --frozen`、`uv run --frozen pytest`、`uv run --frozen zuaef-agent …`。
- `pyproject.toml` 可保留兼容范围，lockfile 固定实际验证版本。
- 本地 slim 环境的 OpenAI import 失败不证明完整 `pydantic-ai` 安装有缺陷；它证明当前 probe 没有使用项目自己的锁定环境。修复同时覆盖环境可复现与不必要 eager import。
- 普通 provider model ID 不 import OpenAI-specific 模块；仅配置 `openai_base_url` 时 lazy import OpenAIChatModel/OpenAIProvider。
- UsageLimits 增加 `total_tokens_limit`，不建新资源账本；无法得到完整 usage 时记录 `usage_complete: false`，不得用 `{}` 表示零使用。
- Receipt 义务边界从 run acceptance 开始：run_id 已分配且 runtime 接受执行之前，配置文件解析、CLI 参数、环境装配错误是 process error，不要求 Run Receipt；接受之后任何 runtime 失败必须返回或落盘 Receipt。不得为覆盖 pre-acceptance 错误新建错误管理框架。
- CLI completed 退出 0，partial/blocked 退出非零，paused 使用与失败语义可区分的专用退出码；非法零限制明确报错。下游调用方必须能把"等审批"与"失败"区分开。

## 正确性补丁，不扩建

Manifest integrity、保留 knowledge id、search limit、symlink containment、文档原子替换、可重建 index、usage 完整性和 CLI exit code 与 P0 契约同批完成，但不得演变成 package manager、数据库、通用 validator 或资源治理系统。

## 继续 defer

- wall/tool timeout：尚无真实挂死证据。
- 并发文件锁：尚无真实并发需求或失败。
- 知识版本/冲突模型：尚无覆盖冲突的业务压力。
- 通用 acquisition record：本地 source 切片不需要采集平台。

## 继续 reject

- RunReceipt.status 与 summary.status：当前由同一内部构造点赋值，无可达不一致路径。
- `requires_approval()` 非枚举输入 fail-open：当前无可达非枚举调用点。

## 本地权威资料

- `pydantic-ai/docs/deferred-tools.md`
- `pydantic-ai/docs/testing.md`
- `pydantic-ai-harness/docs/step-persistence.md`
- `pydantic-ai-harness/docs/skills.md`
- `pydantic-ai-harness/README.md`

`pydantic-deepagents` 只提供 Skill/Capability 组合参考；其 multi-agent、forking、memory、checkpoint、custom hooks 与自有 runtime 不进入本核心。
