---
title: '飞书原生自托管 coding profile'
type: feature
created: '2026-09-08'
status: in-progress
baseline_commit: 0c58a230db21b9dff93d2def2ddde6a9287616d9
review_loop_iteration: 0
context:
  - AGENTS.md
  - zuaef-self-hosting-coding-profile-spec-v0.1/12_MASTER_PROMPT.md
---

<frozen-after-approval reason="用户已授权整个 Spec Pack 实现">

## Intent

让飞书操作者选择 coding，通过现有单 Agent 自己读写真实仓库、测试、处理 Spec 附件，无需 Codex/Pi。完整需求以 `zuaef-self-hosting-coding-profile-spec-v0.1/` 全包为准，开始时读取各文件。用户授权继续实施及必要验证，不重复索取规划批准。

## Boundaries & Constraints

保持 Runtime/Core/receipt/StepPersistence/路由既有 authority；插件只组合上游构件。无 worker runtime、registry、queue、新 hash 机制。不自动 push/restart。不读出密钥。保护已有图索引修改及其他未跟踪 Spec 包。Shell 是可信操作者工具而非敌对代码沙箱。

## I/O & Edge-Case Matrix

| 场景 | 预期 |
|---|---|
| 正常 coding 配置 | 仓库 FileSystem/Shell 经 repo prefix 与 workspace 共存 |
| 未知配置键/坏仓库路径 | 模型前 CompositionError，无自动建目录 |
| 密钥路径及越界 | repo FS 拒绝读取/写入，普通源码可修改 |
| CodeMode 开/关 | 无冲突，shell 可调用，保留正常完成路径 |
| 飞书授权 file-only/text+file | SDK 下载后相对 AttachmentRef，正常 run |
| 未授权/bot/未 mention | 零下载 |
| 超限/下载失败/危险路径 | 明确运输错误，无假附件、不覆盖/不越界 |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/composition.py`: build_profile_agent → resolve_profile → frozen snapshot → build_agent，复用不改。
- `src/zuaef_agent/plugin_api.py`: build_plugin(env, config) 返回 PluginBundle(capabilities, skill_dirs)，无 instructions 字段。
- `src/zuaef_agent/core.py`: 已有 workspace FS、可选 Shell、Skills、Planning；generalist host∩profile。
- 已安装 Harness 0.29.0/PydanticAI 2.40.0。FileSystem(root_dir, denied_patterns, protected_patterns)；protected 仅写保护，密钥须 denied_patterns。Shell(cwd, allowed_commands, denied_env_patterns)，public LLM_API_KEY_ENV_PATTERNS 非默认。RepoContext(workspace_dir=Path,home_dir=None,filenames=('AGENTS.md','README.md'))。全部支持 .prefix_tools('repo')。CodeMode() 已安装，先复现完整组合再决定默认开启。
- `plugins/zuaef-knowledge-worker/pyproject.toml`：现有 workspace entry-point 包装例。
- `src/zuaef_agent/gateway/feishu.py`: admission 保持同步也可，_on_message 应 async await SDK 下载，禁止同 loop _submit().result()。SDK 可 await handler。
- SDK 1.4 ResourceDescriptor.type/file_key/file_name，无 size/mime。await channel.download_resource(file_key,resource_type='file',message_id=msg.message_id) -> bytes|None；下载后 len 限制（SDK 不支持流式上限，文档诚实说明），exclusive 写入 workspace inbox，防遍历/symlink/覆盖。
- `src/zuaef_agent/gateway/runner.py`: default_adapter 传现有 max_upload_bytes。
- `gateway/models.py` AttachmentRef、bridge.project_prompt 和 routing 已支持，勿改。
- `tests/test_gateway_feishu.py`：同步 fake 要适配 async handler，加真实 SDK await compatibility。

## Tasks & Acceptance

实现者负责下列产品代码/测试/文档/锁文件及 surgical manifest；主 Agent 负责外部部署检查和最终验收报告。共享工作区，不撤销他人编辑。实现按 causal slice 顺序推进，先原生 coding 组合有效再做飞书。

- [x] `plugins/zuaef-coding/**`：薄插件，严格六键配置/真实仓库锚点/git worktree 校验，repo FS/Shell、RepoContext、可选 CodeMode、精简 coding Skill、真实能力/commit 配置说明。
- [x] `profiles/coding.toml`、`pyproject.toml`、`uv.lock`：真实安装/解析。本机和 OPi5 路径需明确，不静默落到 workspace；可用明确可移植路径配置并文档化。
- [x] `gateway/feishu.py`、`runner.py`：归一化授权 file 资源，已有 inbox/attachment seam，用户可见失败。
- [x] `tests/test_coding_profile.py`、`tests/test_gateway_feishu.py`：覆盖矩阵、实际工具调用编辑/测试、凭据过滤、existing profiles、approval 不回归。
- [x] `docs/coding.md`：部署配置、可信访问、Shell 权限真实限制、activation 状态。
- [x] `BUILD_MANIFEST.json`：仅新/修改交付文件条目更新，禁止全量重生成。
- [x] targeted pytest、full pytest、ruff .、manifest、plugin list/profile check；区分 baseline 失败。

验证记录（2026-09-08）：full pytest 1320 passed；ruff 任务文件干净（30 个 baseline 错误均在本任务未触碰的 quant 文件）。Gate A/I 通过；Gate B 真实模型通过（canary 克隆，5 请求，直接工具，CodeMode 维持 OFF）；Gate C partial——三次真实运行，编辑与运行内 pytest 23 passed 均达成，唯"运行内如实汇报"条款被操作者 CLI 预算截断，残余条款并入 Gate F；Gate J 通过（含两个 reproduced 摩擦的最小修复：裸命令名指引 72b3a3a、只读 which 白名单 fc39d6a）。OPi5 已部署（fc39d6a，composition_id 与本机一致，feishu.env coding 访问=同 quant 两群组 chat，zuaef-feishu-gateway 已重启加载）。Gate D/E/F 待真实飞书操作者消息；G/H 跳过（allow_codex/allow_pi 默认 false）。

验收：Given 新配置 When build/run Then 自身工具修改/测试仓库；Given 授权飞书附件 When SDK handler Then attachment 相对路径进入现有 run；Given 其他 profile When check Then 行为保持。真实模型 B/C/J 和飞书 D/E/F 由主 Agent 接续验证，未通过不得标完成。

## Verification

基线：profile check coding exit 64（不存在），HEAD 如上。真实工具 schema fixture 不应联网；若沙箱 async/thread 卡住，用 async FunctionModel 或诊断后报告。验证命令 `uv run zuaef-agent plugin list`、`uv run zuaef-agent profile check coding --config-root .`、`.venv/bin/pytest -q`、`.venv/bin/ruff check .`。报告已运行的命令及结果，不编造 live 成功。

## Spec Change Log
