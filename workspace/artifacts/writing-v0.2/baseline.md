# Writing v0.2 — Baseline（Phase 0 记录）

Date: 2026-08-18
Repo: Rayegoe/zuaef-agent
Status: 可复现基线（下述命令在本工作区可复现）

## 1. SCM

- HEAD: `4078eaf` — "add sequential editorial experiment scripts"
- 工作树：4 个被误删的 tracked SPEC 文档已还原（`git checkout --` 恢复，
  使 BUILD_MANIFEST 完整性测试通过；这些文档是 HEAD 的一部分，非本阶段删除）。
- 未跟踪项（pre-existing）：`.codebase-memory/`, `_bmad-output/`,
  `workspace/cases/`, `workspace/workspace/`。

## 2. 测试基线

命令：

```bash
export ACE_ROOT=$PWD/.zuaef-state/ace   # ACE 的可写副本（见 §5 环境说明）
.venv/bin/python -m pytest -q
```

结果：

- **468 passed, 0 failed, 0 skipped**
- 说明：测试需要 ACE checkout 且需要写 ACE workspace。
  真实路径 `~/projects/article-context-engine/article-context-engine` 在本
  sandbox 的 workspace-write 策略下不可写；`$PWD/.zuaef-state/ace` 是该
  checkout 的逐字节副本，同一内容、可写，因此基线完整可跑。
- 环境修正前：326 passed / 1 failed（首次，ACE 写被拒）；随后 8 failed +
  18 skipped 均为环境 artifact（ACE 副本落在 /tmp 被清理 + SPEC 文档被删），
  非代码缺陷。

## 3. Lint 基线（delivery scope，与 CI 一致）

```bash
.venv/bin/ruff check src/ plugins/ examples/ benchmarks/ tests/ tools/
```

结果：**All checks passed!**（ruff 0.16.3）

注：全仓 `ruff check .` 有 62 个 pre-existing 错误，全部位于 delivery scope
之外的资产（`.agents/**`, `_bmad/**`, `zuaef-editorial-control-v0.1/**`），
CI 明确将其排除（见 .github/workflows/ci.yml）。

## 4. 依赖基线

venv：`.venv`（uv 托管的 CPython 3.13）

| 包 | 版本 | 备注 |
| --- | --- | --- |
| pydantic-ai | 2.30.0 | 满足 `>=2.27,<3` |
| pydantic-ai-slim | 2.30.0 | |
| pydantic-ai-harness | 0.20.0 | 当前仅 `[skills]` extra |
| pydantic-monty | **未安装** | CodeMode 需要（`[code-mode]` extra） |
| ruff | 0.16.3 | |
| uv | 0.11.28 | 需 `UV_CACHE_DIR` 指向可写路径 |

pyproject：`pydantic-ai>=2.27,<3`、`pydantic-ai-harness[skills]>=0.1`
uv.lock：harness 0.20.0 / pydantic-ai 2.30.0（已锁定）

Harness 0.20.0 提供 `pydantic_ai_harness.code_mode` 模块；CodeMode 依赖
`pydantic-monty>=0.0.19`（extra 名 `code-mode` / 别名 `codemode`）。
Skills 文档注明 minor release 可能改 API —— 按 SPEC §28：锁死实测版本，不追
main 最新。

## 5. 环境说明（本 sandbox 特有）

- /tmp 在 bash 调用之间不持久（材料文件、ACE 副本都会消失）→ 临时文件一律放
  `$PWD/.zuaef-state/tmp/`。
- 模型链路：.env 提供 `LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL`，
  `AgentSettings.from_env()` 走 OpenAI-compatible chat 模式（DeepSeek），
  网络可用。
- 真实模型探针：`execute_run(build_agent(...))` 一次 hello 运行
  → `status: completed, outcome: OK`（probe-2 receipt 已落盘）。
- ACE 冒烟：`ctx.py new/ingest/materials/material` 在 `.zuaef-state/ace`
  副本上工作正常；`list_materials` 返回 material id/sha256/bytes/stored_path
  等索引字段（与 SPEC §16 的 Material Index Contract 兼容）。

## 6. 当前 ace-writing profile（Phase 2 之前的形态）

`profiles/ace-writing.toml`：

- `editorial_control = true`（EditorialControlCapability 激活）
- `ace_root = ~/projects/article-context-engine/article-context-engine`
- plugin fabric：`zuaef_ace_writing:create_plugin`，返回 1 toolset
  （BudgetedWritingToolset：list_materials / read_material / retrieve_exemplars
  / retrieve_knowledge / check_claim / save_artifact）+ 1 capability

已安装（editable）插件 dist 版本：zuaef_ace_writing-0.1.0（源码 pyproject 已
声明 0.2.0 —— 版本元数据滞后，需要重装同步，快照校验按 installed 版本走）。

## 7. 当前 production writing 输出（Phase 2 将被重构的形态）

`examples/production_writing.py`（647 行）：

- Host 组装 `WritingContext` bundle：task + **writing_plan** + 拼接 material +
  **sources ledger** + **techniques** + **editorial_memory** + **examples** +
  constraints，一次性投影进 request #1（`render_writing_context`）。
- 模型表面只有 `save_artifact`（+ 可选 `retrieve_more_context` escape hatch）。
- `build_production_agent` 关闭 generic surfaces
  （filesystem/knowledge/planning/skills/tool_output_limits），保留
  StepPersistence + EditorialControlCapability。
- 采用 `core.build_agent` + `extra_toolsets`，**不走** profile。

现状结论（SPEC Problem Statement 属实）：

- pull-based `BudgetedWritingToolset` 已存在并被 plugin 暴露；
- 但 production 路径被 Host projection 覆盖：host 决定 angle/outline/
  techniques/memory/examples，模型只做"一次写完 + save"。

## 8. Phase 0 冻结范围（本阶段不动）

runtime.py / gateway/** / case/** / client-service/** / wordpress/** /
budget/** / FDE 相关代码。`core.py` 仅允许在 CodeMode 需要 generic
composition seam 暴露时做极小改动（优先插件侧 compose）。