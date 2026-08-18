# Writing v0.2 — Implementation Report（实施记录 + WRITE gates 验证）

Date: 2026-08-18
Repo: Rayegoe/zuaef-agent
Baseline: `workspace/artifacts/writing-v0.2/baseline.md`
SPEC: ZUAEF Writing Capability — SPEC & Implementation Plan v0.2

## Summary

Writing 已从 Host 编排恢复为 **Agent-owned capability**：单 Core Agent 通过
`ace-writing` profile 组合，使用 Harness Planning / Skills / ToolOutputLimits /
StepPersistence / CodeMode 等 upstream primitives，ACE tools 负责材料/依据/
事实/provenance。Host 只做机械准备（bytes→sha256→rights→ACE ingest→M id→薄任务契约）。

## 改动文件（按 Phase）

### Phase 1 — Harness 依赖对齐
- `pyproject.toml` / `plugins/zuaef-ace-writing/pyproject.toml`：
  `pydantic-ai-harness[skills,code-mode]>=0.1`
- `uv.lock`：+ pydantic-monty 0.0.21 (+client/+runtime)，无版本漂移
- 插件 editable 重装同步版本 0.1.0 → 0.2.0
- 回归：pytest 480 passed / ruff 绿

### Phase 2 — 移除 Host-Controlled Writing
- `examples/production_writing.py` **重写为薄 driver**：
  - `WritingTask`（article_id/assignment/audience/constraints，`extra="forbid"`）
  - `mechanical_prepare`（纯机械：hash/rights/ingest/M-id 绑定）
  - `render_agent_prompt`（首个模型请求只含任务契约 + 机械事实，绝无
    writing_plan/angle/outline/techniques/memory/examples/材料文本）
  - `run_production_task`（`build_profile_agent("ace-writing") -> execute_run`，
    快照冻结进 receipt）
  - 删除：prepare_writing_context / render_writing_context /
    build_production_agent / run_production_article / ProductionWritingToolset
    / one-pass-only 指令 / save-only 表面
- 旧机制迁移至 `benchmarks/editorial-learning/scripts/host_projection_legacy.py`
  （仅 benchmark 实验使用，标注 LEGACY 非生产）
- 引用方更新：`examples/sanlian_showcase.py`、`examples/case_showcase.py`、
  `benchmarks/editorial-learning/scripts/compare_paths.py`
- `tests/test_production_writing.py` 重写为 29 个 zero-model contract 测试

### Phase 3 — 生产入口统一走 profile
- WCASE-1 真实模型端到端：mechanical prep → profile 组合（Planning 被 Agent 使用，
  Skills 按需加载，ACE list/read/retrieve/claim-check 全工作）→ save_artifact →
  **ACE fact_check_passed=true, claims_resolved=true** → completed。

### Phase 4 — Harness Planning & Skills
- `.agents/skills/` 新增 4 个写作 skill（稳定方法层，实例层归 ACE corpus）：
  `longform-feature-writing` / `scene-preserving-writing` / `editorial-revision`
  / `beauty-wechat-writing`（SKILL.md + YAML frontmatter）
- 验证：Skills 以 deferred capability 暴露（catalog 只含 id+description，
  body 按需 load_capability）；真实运行中出现 `load_capability`（WCASE-1/2/3）。

### Phase 5 — CodeMode
- writing toolset 的观察工具（list_materials/read_material/retrieve_exemplars/
  retrieve_knowledge/check_claim）打 `metadata={"code_mode": True}`；
  `save_artifact` 不打（SPEC §10 边界）
- plugin 增加 `code_mode` 配置 → 注入 Harness `CodeMode(tools={"code_mode": True})`
- `profiles/ace-writing.toml` 默认 `code_mode = false`；
  `profiles/ace-writing-codemode.toml`（实验）ON
- A/B（同任务/同材料/同上限，WCASE-1）：
  - OFF：30 requests，completed，855 字
  - ON：20 requests，run_code×6（+list 1/read 1/exemplars 2/knowledge 1），
    save_artifact 成功、fact check 通过，753 字（run 因 run_code 未决效果在预算边界
    收口为 blocked，成品已落盘）
  - 结论按 WRITE-7：**默认保持 OFF**（质量未证明显著提升，且收口不稳）。

### Phase 6-8 — WCASE 运行（Field Gate）
- WCASE-1 单源：completed，30 requests，855 字，事实全对，ACE 校验通过
- WCASE-2 多材料：completed，21 requests，1204 字。
  读全 9 份材料：成稿只用核心(采访/规格/实测)+次要(定价/品牌史)；
  3 份无关材料（菜单/旅行日志/煤油灯）零出现；冲突草稿（旧规格）未作确定事实，
  数字全部采用正式版 v3。**Selection Intelligence 通过（WRITE-3）。**
- WCASE-3 信息边界：completed，36 requests，1036 字。
  任务索要"三个月回购率/长期顾客感受"而材料没有 → 文章明确声明
  "任何三个月回购率 XX% 都是我们不能编造的数字"，在材料范围内完成。
  **无编造（WRITE-8）。**
- WCASE-4 修订：草稿 completed（22 req，661 字）→ 自然语言反馈
  （"太像 AI，判断句太多，人物没出来，开头太像背景说明"）→ 修订稿
  （19 req，598 字，save_artifact 已保存）。
  修订实质回应反馈：开头改为直接对话（"老周你今儿怎么来得晚"）、人物用材料
  原话行动、删除草稿结尾的判断句总结并换成具体收尾（收音机换折子/三张空桌/
  五只倒扣茶杯）、事实全保留。**WRITE-10 通过（实质）。**

  > **运行接口缺陷（非写作能力失败，勿归因于 Revision Intelligence）**：
  > 修订轮 receipt 为 `partial`，仅因 RunSummary 的 artifacts 引用漏了
  > `artifacts/` 前缀（host 校验拒绝该引用；修订稿已实际保存并经 host 验证，
  > 见 report：`eval/WCASE-4/revision.md`）。根因已修复——提示词写入字面示例
  > （含 `artifacts/` 前缀），并新增断言测试锁定；后续运行应 completed。
  > 同类 summary 引用问题也出现在 A/B 的 ON 侧（partial，产物已保存）。
- case-01-content-team（迁移案例）：completed，14 requests，2293 字。
  数字标注为客户报数、不写平台检测机制、从具体场景进入、人物原话在场。
  **迁移证明：无 case_showcase 依赖。**

### Phase 9 — Editorial Control A/B
- 运行（WCASE-1，同任务/材料/预算 40）：
  - ON（`ace-writing`，editorial_control=true）：draft partial，16 requests，1250 字
    （partial 为 summary 引用格式问题，产物已保存）
  - OFF（`ace-writing-no-editorial`）：draft completed，19 requests，1275 字
- **盲评结论（2026-08，人工匿名评审）：样品Y（OFF）质量更好（样品Y > 样品X）。**
  ON 未显示稳定优势。
- **决策落地（SPEC §20）**：Editorial Control **保持 optional/experimental**。
  生产默认 `ace-writing` 的 `editorial_control = false`；ON 侧可通过
  `profiles/ace-writing-editorial.toml` 按需开启。**不追加任何 machine sensor**
  去强行优化"指标赢"。盲评表与 KEY 见 `blind-eval/`。

## 停止条件评估（SPEC §33）

| 事实 | 状态 | 证据 |
| --- | --- | --- |
| 1. 单素材任务自主完成（看材料→选择→写→核验→保存） | ✅ | WCASE-1 completed（30 req，ACE fact_check_passed） |
| 2. 多材料 Host 不选、Agent 自选基本合理 | ✅ | WCASE-2（无关材料零出现、冲突数据正确处理） |
| 3. 材料不支持的信息不编 | ✅ | WCASE-3（明确拒绝编造回购率） |
| 4. 自然语言编辑反馈能真正修稿 | ✅ | WCASE-4（判断句删减、人物对话化、开头场景化） |
| ACE evidence intact | ✅ | 多次 save 均 fact_check_passed / claims_resolved |
| Harness runtime intact | ✅ | 全量测试 477 passed / ruff 绿 |
| 人工编辑判断可用性 | ⏳ **人工步骤** | 产物齐备（eval/WCASE-*），盲评表见 §26 |

Writing v0.2 实施到此停止；下一步只由真实 Writing failure 或人工盲评结论决定。

### Phase 10 — 移除 Showcase authority
- 删除 `examples/case_showcase.py` + `tests/test_case_showcase.py`
- 数据迁移：`benchmarks/writing-cases/case-01-content-team/`
  （raw/ 5 份 + expected-signals/ 人工验收注记 + 新 case.json 薄契约，
  不含 writing_plan/signal_gate 编排）
- 任何 Writing proof 不再依赖 case_showcase；迁移后的 case 已能通过
  `tools/run_writing_eval.py case-01-content-team` 运行。

### Phase 11 — Writing Field Gate runner
- `tools/run_writing_eval.py`：load case → 机械 ingest → 调生产 profile →
  收集 outcome → 写 evaluation bundle；绝不决定选材/结构/技法/修订。

## 过程中修复的真实缺陷（Field 驱动，SPEC §30 规则）

1. **Knowledge 读节点抛裸异常**：Agent 把 ACE 的 claim-taxonomy 提示误当成
   workspace knowledge id → FileNotFoundError 阻断整轮。
   修复：`read_knowledge` 把 (ValueError/OSError) 转成可恢复错误串
   （src/zuaef_agent/knowledge_capability.py）。
2. **check_claim 畸形参数耗尽重试**：非法 claim 形状抛验证异常→重试上限→blocked。
   修复：参数放宽为 Any、预算检查提前、非法形状返回错误 JSON
   （plugin + examples 两处 writing_toolset.py 同步）。
3. **FileSystem 漫游/越权写 artifacts**：FS 开启时模型要么到处探索 workspace
   浪费预算（WCASE-2：21 次文件操作），要么直接写 artifacts/ 绕过 ACE 校验。
   修复：core 保护 `artifacts/*`（仅 toolset 可写，WRITE-9 provenance 不变量）；
   写作 profile 组合时关闭泛用 FileSystem（composition_settings，实测依据）。
4. **泛用 Knowledge 噪音**：workspace 文件知识库（1 篇文档）对写作任务无用，
   WCASE-4 修订轮在其中消耗约 12 个请求（search/list/read_knowledge）后预算
   耗尽、未达 save。写作的知识源是 ACE（retrieve_knowledge）。
   修复：写作 profile 组合时关闭泛用 Knowledge（同 FileSystem 的实测依据）。
5. **RunSummary evidence 引用伪造**：模型填 tool-effect 引用不存在的 id → 降级
   partial。修复：提示词明确只用 artifact: 引用，禁止 tool-effect。
6. **JSON 序列化**：receipt 的 Decimal 成本值 → plain_jsonable 转换。
7. **profiles/ace-writing.toml** 去掉 ace_root 硬编码（默认路径不变，可被
   ACE_ROOT env 覆盖）。

## 验收 gates 状态（WRITE-1..12）

| Gate | 状态 | 证据 |
| --- | --- | --- |
| WRITE-1 生产组合 | ✅ | run_production_task 只用 build_profile_agent("ace-writing") + execute_run；测试覆盖 |
| WRITE-2 无 Host Plan | ✅ | WritingTask extra=forbid + 提示词测试断言无 angle/outline/techniques/examples |
| WRITE-3 Agent 选材 | ✅ | WCASE-2 实测 |
| WRITE-4 工具顺序不脚本化 | ✅ | 无顺序断言；提示词声明"Decide what to read" |
| WRITE-5 Harness Planning | ✅ | Planning capability 在列；receipts 有 write_plan/read_plan |
| WRITE-6 Harness Skills | ✅ | 4 skill 目录 + deferred catalog 测试 + 运行中 load_capability |
| WRITE-7 CodeMode A/B | ✅（记录） | OFF 30 req completed vs ON 20 req 保存成功；默认保持 OFF |
| WRITE-8 事实完整 | ✅ | WCASE-3 无编造；WCASE-2 数字全用正式版 |
| WRITE-9 ACE 校验 | ✅ | save_artifact 走 ACE；WCASE-1 fact_check_passed=true；artifacts/** 受保护 |
| WRITE-10 修订 | ✅ | WCASE-4：判断句删减、人物对话化、开头场景化，事实保留 |
| WRITE-11 Editorial A/B | ✅（盲评出结论） | 样品Y(OFF) > 样品X(ON) → 保持 optional，默认 OFF |
| WRITE-12 无新通用基建 | ✅ | 仅新增 Harness CodeMode + writing skills + 工具加固；无新 engine/store |

## 环境说明

- 模型：DeepSeek（OpenAI-compatible via LLM_* env）
- ACE：`$PWD/.zuaef-state/ace` 为可写副本（原 checkout 在 sandbox 下不可写；
  两台机器行为一致）
- /tmp 跨命令不持久 → 临时文件一律放 `.zuaef-state/tmp/`
- 复现命令见 baseline.md

## 待办（需要人工/后续轮次）

- **Phase 9 盲评已完成（2026-08）**：样品Y（Editorial OFF）质量更好 →
  Editorial Control 按 SPEC §20 保持 optional：生产默认 OFF
  （`profiles/ace-writing-editorial.toml` 为 ON 可选侧），不再追加 sensor。
- 若未来有新的实际证据表明 Editorial Control 稳定胜出，再评估
  Editorial Intelligence follow-up SPEC；在此之前不投资。
- CodeMode 稳定性：若收口问题（run_code 未决效果）修复后重测，再决定默认。
- 提交策略：已按语义拆 5 个提交（refactor / feat / fix / test / docs），
  盲评结论作为独立提交追加。