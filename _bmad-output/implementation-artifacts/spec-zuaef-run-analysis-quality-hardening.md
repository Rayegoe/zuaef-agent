---
title: 'ZUAEF Run Analysis 事实保真与嵌套语义加固'
type: 'bugfix'
created: '2026-08-23'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'b820895707db93585a027320dfc036f009f6c37e'
context:
  - '{project-root}/docs/runtime-refoundation/SPEC.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 当前 `analysis.md` 的五段正文全部由 LLM 生成；实测 Host 会原样接受模型写错的 run ID、重命名后的工具名和臆测的 token limit，也会接受缺少 Section 5 的截断报告。Analysis-of-Analysis 还没有确定性区分当前 Analysis run、subject run 与 nested subject。

**Approach:** 保留 `load_run_facts() → projection → Analysis Agent → analysis.md`，把 Section 2 和运行关系元数据交给 Host 从现有 projection 渲染；LLM 只提交 Section 1/3/4/5，Host 验证完整性后组装最终 Markdown。不给 Harness、Capability、持久化或证据层增加新权威。

## Boundaries & Constraints

**Always:** 事实值逐字来自现有 `RunFacts/project_run` projection；缺失值渲染为 `unknown`。Host 保留 run ID、model、status、request/token 数、tool name 与 artifact facts，不从 usage 反推配置。模型段落只负责业务结果判断、解释、显式分层的因果假设和一个用于区分竞争假设的实验。Subject 为 `analysis-*` 时，只从其持久化 Analysis task prompt 的固定句式解析 nested subject；解析失败写 `unknown`。

**Ask First:** 若实现必须改变 API contract、持久化 schema、Harness/Core、projection 事实定义，或需要自动 retry，停止并征求确认。

**Never:** 新增 Analysis schema family、数据库、Evidence/Gate framework、Capability、Agent、critic/judge、workflow state machine、审批、自动实验、自动业务配置修改、hash/manifest 或 provider telemetry 采集机制；不重构无关 runtime。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| EXACT_FACTS | projection 含 run `abc123`、output 1436、tool `inspect_run_segment` | Section 2 原值输出，绝不出现近似 limit 或工具改名 | N/A |
| UNKNOWN_FACT | projection 无 configured output limit | 报告保持 `unknown`，LLM prompt 禁止由 usage 推断配置 | N/A |
| NESTED_ANALYSIS | A 分析 `analysis-B`，B prompt 指向 C | 元数据明确 A/B/C 与 `Subject kind: analysis` | 句式无法确定解析时 `Nested subject: unknown` |
| INCOMPLETE_LLM | Section 1/3/4/5 任一缺失或为空 | 不写成功 artifact，当前 Analysis API/state 明确 `failed` | 复用 `AnalysisError`/`AnalysisResult`，不加 schema |
| MODEL_SECTION_2 | LLM 仍返回自己的 Section 2 | Host 丢弃该段，只插入 deterministic Section 2 | N/A |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/web/analysis.py:47-88` -- `ANALYSIS_INSTRUCTIONS` 当前要求模型生成五段；改为证据纪律和仅生成 1/3/4/5。
- `src/zuaef_agent/web/analysis.py:337-389` -- `_analysis_prompt` 与 `_format_analysis_artifact` 是 prompt/最终组装边界；在此解析模型段落、检查非空、输出 A/B/C 元数据并插入 Host facts。
- `src/zuaef_agent/web/analysis.py:430-502` -- `_run_analysis` 已持有 subject `RunFacts` 与现有 failed result 通道；把同一 facts 传给 assembler，完整性失败沿现机制报告。
- `src/zuaef_agent/web/analysis_store.py:37-57` -- projection 文件 handoff；增加薄的 Observed Facts renderer，复用 `project_run(facts)`，不建立 DTO/store。
- `src/zuaef_agent/web/projector.py:488-582` -- 只读复用点：`run_view`、usage、timeline、artifact 与 composition 的现有确定性 envelope。
- `src/zuaef_agent/web/analysis_projector.py:181-240` -- 只读参考：当前 bounded projection 与 observable prompt；本轮不改变事实层。
- `tests/test_web_console.py:801-879` -- 现有 Analysis API/toolset/export 回归测试；在同文件增加事实保真、unknown、嵌套关系、Section 2 替换与不完整失败测试。

## Tasks & Acceptance

**Execution:**

- [x] `src/zuaef_agent/web/analysis_store.py` -- 从现有 projection 生成稳定的 Observed Facts Markdown；无值统一 `unknown`，工具和 artifact 标识不解释。
- [x] `src/zuaef_agent/web/analysis.py` -- 加固 prompt；确定性提取 1/3/4/5、拒绝缺失段、解析 nested subject、组装 Host 元数据与 Section 2；沿现有 failed state 暴露不完整结果。
- [x] `tests/test_web_console.py` -- 覆盖矩阵场景并保证 inspection/projection/API/Console 既有行为继续通过。

**Acceptance Criteria:**

- Given authoritative projection facts, when `analysis.md` is assembled, then Section 2 contains exact identifiers/counts and contains no model-authored replacement text.
- Given absent configuration evidence, when prompt and artifact are produced, then no configured limit is asserted and unknown remains explicit.
- Given a hypothesis in Section 4, when Section 5 is accepted, then prompt requires a discriminating experiment and forbids upgrading the hypothesis to fact.
- Given A analyzes B and B deterministically points to C, when metadata renders, then A/B/C retain their correct roles; an unparseable C is `unknown`.
- Given any required LLM section is empty or absent, when the worker settles, then Analysis state is failed and cannot silently appear as business success.
- Given existing inspection, projection, analysis API and workspace export tests, when the focused suite runs, then all remain green.

## Spec Change Log

## Design Notes

完整性检查是局部 Markdown contract，不是新 schema：只识别四个精确二级标题并要求正文非空。最终顺序固定为 1 → Host 2 → 3 → 4 → 5；模型偶发输出的 Section 2 不进入 artifact。Fresh reproduction 已证明旧 assembler 会原样写入 `abc132`、`~1500 token limit`、`read_run_projection`，并在缺少 Section 5 时仍返回文档。

## Verification

**Commands:**

- `timeout 180 .venv/bin/pytest -q tests/test_web_console.py` -- expected: 新旧 Analysis/Inspection/Projection/API 测试全部通过。
- `.venv/bin/ruff check src/zuaef_agent/web/analysis.py src/zuaef_agent/web/analysis_store.py tests/test_web_console.py` -- expected: 无 lint findings。

## Suggested Review Order

**职责分界与运行入口**

- 单次加载 projection，统一供 Agent inspection 与 Host 最终渲染。
  [`analysis.py:566`](../../src/zuaef_agent/web/analysis.py#L566)

- Prompt 将事实、判断、假设和区分性实验的职责明确拆开。
  [`analysis.py:48`](../../src/zuaef_agent/web/analysis.py#L48)

**确定性事实与文档组装**

- Host 从现有 bounded projection 原样渲染 Section 2 与 omitted 数。
  [`analysis_store.py:77`](../../src/zuaef_agent/web/analysis_store.py#L77)

- Assembler 固定输出 1→Host 2→3→4→5，并拒绝不完整 deliverable。
  [`analysis.py:494`](../../src/zuaef_agent/web/analysis.py#L494)

**Markdown 与嵌套关系边界**

- 小型 parser 识别真实 H2、缩进与代码围栏，不接受伪完整输出。
  [`analysis.py:392`](../../src/zuaef_agent/web/analysis.py#L392)

- Nested subject 仅来自原始持久化 Analysis task prompt。
  [`analysis.py:449`](../../src/zuaef_agent/web/analysis.py#L449)

**验收与回归**

- 精确事实、unknown 和模型 Section 2 替换由同一测试固定。
  [`test_web_console.py:854`](../../tests/test_web_console.py#L854)

- 成功 settlement 与 artifact readback 覆盖真实 Host 写入路径。
  [`test_web_console.py:1256`](../../tests/test_web_console.py#L1256)
