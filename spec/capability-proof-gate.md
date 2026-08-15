# v1.1 Capability Proof Gate

这是本阶段唯一 Acceptance Gate。以下要求共同组成一个 Gate，不拆成 15 个独立修复目标，也不新增 evaluator/gate framework。

## 受控垂直切片

输入使用真实本地 source：

`./Outcome-First PydanticAI Agent Engineering Guide v2.0.md`

同一个真实 PydanticAI Agent 装配：

- 至少一个业务 Research Toolset，用于读取/提交真实 source 研究结果；
- 现有 FileSystem、Knowledge、Skills、ToolOutputLimits 与 StepPersistence；
- 一个 `requires_approval=True` 的受控副作用工具，唯一 external-write 测试效果是项目根下 `.state-proof/external-effect-<conversation_id>.marker`（位于 `workspace/**` 与 `knowledge/**` 之外）；不得写 `knowledge/**`、源码或 report，避免 approval 测试污染 artifact/knowledge 验证。

Agent 必须经共享 `execute_run(agent, deps, …)`：读取 source，生成 `workspace/artifacts/report.md`，通过 Knowledge Capability 写入 evidence-backed knowledge，并返回 RuntimeOutcome 与 Receipt。

## Gate 证据

### 可复现与真实运行

- `uv sync --frozen` 成功。
- `uv run --frozen pytest` 与静态检查成功。
- 使用已配置的真实模型运行垂直切片；TestModel/FunctionModel 只能验证确定性分支，不能替代此证据。
- 运行确实导入并执行 core、runtime、provider resolver、CLI、业务 Research Toolset、Knowledge、StepPersistence 与 Receipt verification；静态字符串断言不计入 Gate。

### Host 验证结果

- `report.md` 由 host 验证 containment、存在、regular file、本次运行归属、size 与 SHA-256。
- Knowledge 节点由 host 验证 id、frontmatter run id、sources 与文件存在。
- Receipt 只保存 verified artifact/knowledge/tool-effect 引用；模型伪报路径的确定性测试必须降级 completed。

### Approval pause 与 continuation

- 首次副作用调用返回 PausedRun，含 DeferredToolRequests、message history、conversation id 与 pause Receipt；工具尚未执行。
- deny continuation 使用 DeferredToolResults，保留 conversation id、生成新 run id，标记文件不存在并留下 Receipt。
- approve continuation 使用 DeferredToolResults，保留 conversation id、生成新 run id，执行受控工具并留下 settled tool-effect 与最终 Receipt。
- 本 Gate 不声称 exactly-once；它只证明 continuation 不重复已 settled effect。构造 `started` 无 settled result 时，runtime 必须 blocked、记录 `unresolved_effect` 且不自动重放。

### Failure receipt

- 至少对 provider、tool、output validation、persistence 中一个可控失败运行公共 runtime。
- Receipt 义务边界为 run acceptance：run_id 分配前的配置/CLI/依赖错误是 process error，不计入本 Gate，也不为它们新建错误管理框架。
- 失败必须返回或落盘明确的 partial/blocked Receipt，包含 run/conversation identity、错误摘要、`usage_complete`、已 settle usage 与已有证据句柄；不得无记录异常退出。

### Manifest 与 CLI

- 为当前交付树更新 `BUILD_MANIFEST.json` 并执行 integrity test；任何路径、内容哈希或隐藏运行必需文件缺失时失败。integrity 校验范围是 manifest 声明的文件集合，不遍历整棵树；运行期产生的 `.state-proof/**` marker 不得触发 integrity 失败。
- CLI completed 退出 0，partial/blocked 退出非零，paused 使用与失败语义可区分的专用退出码；非法零限制明确失败。

## Pass / stop rule

上述证据全部存在且真实模型垂直切片可人工沿 Artifact、Knowledge 与 Receipt 复核时，Gate 通过并立即停止 Stage A。

Gate 通过前，禁止新增 multi-agent、registry、graph runtime、background jobs、generic ingestion framework、vector DB、长期 memory、并发执行框架、自研 durable state machine，或接入 YouTube/Hardware Scout/WordPress 等下一业务。
