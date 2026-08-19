# AUDIT — 三条支线进展 × SPEC v2.1（T001–T014 状态汇总）

Audit run: 2026-08-19, against `main` HEAD `4fe3342` (plus the `gateway-history`
branch `e2bbe57`). Methodology: live inspection (git reflog/log, per-commit
diffs, source reads), running the probe tool, and running test suites — every
verdict below is grounded in measured evidence, not assertion.

Lines audited:

| 支线 | 任务 | 载体 |
|---|---|---|
| 主线 A | Upstream Capability Baseline = **T002** | 直接落在 `main`（无独立 worktree） |
| 支线 B | Delete Duplication = **T003 + T005** | 直接落在 `main`（用户选择仅验证，不建 worktree） |
| 支线 C | Gateway Continuity = **T010 + T011** | `worktree/gateway-history`（Phase 1）+ `main`（Phase 2 实现） |

---

## 主线 A — T002 Upstream Capability Baseline：PASS（零 RELEASE GAP）

交付物已在仓库内：`docs/upstream-baseline.md`（commit `5ed0e54`）+ 可复现探针
`tools/probe_upstream_baseline.py`。

本次实测（`uv run python tools/probe_upstream_baseline.py`）：

```
pydantic-ai = 2.30.0   pydantic-ai-harness = 0.20.0   python = 3.13
[READY] Agent/Capability/Toolset · FileSystem · Shell · RepoContext
[READY] Planning · Skills · ToolOutputLimits · StepPersistence/StepStore
[READY] Memory · ConversationSearch · SubAgents
[READY] Context controls (compaction) · ClearToolResults
[READY] WebSearch · WebFetch · ToolSearch · DeferredLoadingToolset
[READY] official DeepSeek provider/profile
[READY] optional: CodeMode · Advisor · DynamicWorkflow · CapabilityCreation
RESULT: all REQUIRED baseline primitives READY on the pinned release.
```

用户清单 15 项逐项核对：全部 READY；`DeepSeekProvider` 存在且签名符合预期
（`api_key / openai_client / http_client`），官方 profile 拥有能力 flag。
文档与探针输出一致（19 处 READY，无 RELEASE GAP）。

**验收结论**：T002 = PASS。其确认结果即是 T010 Phase 2 的解锁条件——三条线复用同一公开
StepStore API（`FileStepStore.list_runs / latest_snapshot / fork_run / continue_run`）。

---

## 支线 B — T003 + T005 Delete Duplication：PASS（VERIFIED，与 BRANCH_B 记录一致）

平行 agent 的验证记录 `BRANCH_B_DELETE_DUPLICATION.md` 已存在；本次独立复核结论吻合：

| 任务 | 结果 | 证据 |
|---|---|---|
| T003 删自定义 tool-conflict preflight | **DELETE 确认** | commit `08c10a9` 删 `_check_tool_conflicts / _tool_names / _claim`（composition.py −73 行）；`resolve_profile` 不再做冲突检查；注释明确冲突由 upstream composition 拥有。**未**新建 registry/bridge/adapter。回归测试 `tests/test_plugin_composition.py::test_duplicate_tool_fails_no_silent_override`（414–449，实测通过）：解析不再抛错，materialize 工具 schema 时由 PydanticAI 自身 `UserError`（匹配 "conflicts"）拒绝。 |
| T005 简化 provider/profile | **DELETE 确认** | commit `9b98c9a`：DeepSeek → 官方 `DeepSeekProvider`（`deepseek_model_profile` 拥有 thinking/tool-choice/json-object flags）；generic endpoint → `OpenAIProvider` 官方默认 profile。`AgentSettings` 删除手抄 flag `openai_strict_tool_definitions / multiple_system_messages / supports_max_completion_tokens`。留存的仅为部署层 transport/config（base_url、api key、http(s) proxy、timeouts、retries、thinking 开关、`…/chat/completions` 后缀归一——后者是当前 main 上未提交的增量，符合 T005 规则）。测试：`test_cli_and_providers.py` 三用例 + `assert not hasattr(settings, "openai_strict_tool_definitions")`。 |
| Go 约束 | 无新 AdapterManager/Registry/Bridge | `test_core_contract_static.py` 静态断言 + grep 通过 |
| Go 约束 | Gateway / Memory / SubAgent / generalist 不动 | 提交范围仅 composition/verification/providers/config/tests/manifest；T006+ 的 generalist 面在 `core.py/config.py` 独立提交，未混入 |

本次实测：T003/T005 相关 41 用例全绿。遗留（cosmetic）：3 处过时 docstring 仍声称 ZUAEF 自己检测
tool conflicts（`composition.py:5`、`composition.py:213`、`cli.py:82`），因触碰 manifest 未修，可后续一行提交。

---

## 支线 C — T010/T011 Gateway Continuity：T010 已实现于 main；T011 保持

### Phase 1（TRACE ONLY）— `worktree/gateway-history`（commit `e2bbe57`）

- `docs/gateway-continuity-trace.md`：画清 `inbound → session → run → persistence → next inbound`
  （带 file:line），定位缺陷（`service._start_run` → `bridge.start_profile_run` →
  `runtime.execute_run(message_history=None)`）；确认 Harness 0.20.0 公开 continuation/StepStore API。
- RED 测试 `test_normal_followup_reuses_conversation_but_keeps_empty_history`：`conversation_id` 复用 ✓、
  新 `run_id` ✓、Turn 1 内容未进 Turn 2 ✗（RED = 缺陷证明）。
- 绿色诊断 `test_terminal_run_leaves_resumable_snapshot`：terminal Turn 1 留 `complete` snapshot，
  `continue_run` 可重建——持久化半边已工作，缺口仅在网关 restore。

### Phase 2 — 实现落在 `main`（commit `4fe3342`，平行 agent）

实现与 Phase 1 trace 的 §5 方案逐点吻合：

- `bridge.prior_run_history()`：读 prior receipt → 校验 `conversation_id` 与 session 一致（`/new`
  重置不泄史）→ 公开 `FileStepStore.fork_run(run_id=prior)` → 返回 `message_history`。
- `_start_run` 在 `start_profile_run` 传 `message_history=history`：fresh `run_id` + 同一 `conversation_id`。
- 测试 `tests/test_gateway_continuity.py`（main）：`test_turn2_sees_turn1_constraint`（用黄金该例真实约束
  "价格先不要写"，断言 Turn 2 模型可见）+ `test_reset_conversation_does_not_leak_prior_history`。

**本次实测：我的 Phase-1 RED 测试在主实现下转绿 2/2** —— 缺陷已修复。

### T011（approval continuation）保持

`tests/test_gateway_service.py`（approve/deny 回调、/approve /deny）、`test_continuation.py`
（`continued_from_run_id`、同 `conversation_id`、frozen-composition 权威、版本漂移在模型请求前失败）、
`test_gateway_e2e_wordpress.py`（批准门控的外部写入过网关）——实测 **61 项网关+续跑相关用例全绿**。

---

## SPEC 全量 T001–T014 状态表

| 任务 | 状态 | 证据 |
|---|---|---|
| T001 基线 + Golden Outcome | PASS | 任务目录文档、`docs/upstream-baseline.md`、`uv.lock` (2.30.0/0.20.0/3.13)；Golden 路径 = `tools/fde_two_turn_proof.py`；原 continuity 缺陷已记录并修复 |
| T002 锁定 release pair + 探针 | PASS | 见主线 A；全部 READY、零 RELEASE GAP |
| T003 删 tool-conflict preflight | DELETE | `08c10a9` + 回归测试 |
| T004 替换私有 StepPersistence 解析 | DELETE | `08c10a9` + `verification.py` 改走 `FileStepStore.list_events`（公开 API） |
| T005 简化 provider 解析 | DELETE | `9b98c9a`（官方 DeepSeekProvider/OpenAIProvider；删手抄 flags） |
| T006 组合 generalist 能力面 | READY | `969b591`（`core.py::generalist_capabilities`；被 T002 矩阵覆盖） |
| T007 授权 + 渐进披露（五态） | PASS | `b92b51f` + `test_generalist_activation.py` |
| T008 上下文管理基线 | READY | `0a721b9` + `test_context_management_baseline.py` |
| T009 Memory / ConversationSearch | READY | `0a721b9` + `test_memory_recall_baseline.py` |
| T010 修复网关正常多轮历史 | PASS | `4fe3342` + 两条测试；我的 Phase-1 RED 转绿 |
| T011 保留审批续跑 | PASS | continuity/gateway/e2e 61 用例全绿 |
| T012 业务不变量 | KEEP | 全量套件中 Case/Knowledge/Receipt/写作/预算/WordPress 用例全绿（未动用业务层重构） |
| T013 真实两轮 FDE 证明 | **IN-FLIGHT** | `tools/fde_two_turn_proof.py` 已写好（公开 fork_run 恢复历史；捕获 conversation/两 run/工具面/约束/artifact/verification/receipt/Turn-2 历史），未提交、未实跑（需真实凭据） |
| T014 终回归并 STOP | HOLDING | 全量 `497 passed / 1 failed`（唯一失败 = T013 工具未登记进 manifest，非代码回归；ruff 对已提交文件干净）。T013 未跑 → STOP gate 未到 |

### CAP gates

| Gate | 状态 |
|---|---|
| CAP-1 能力面就绪 | PASS（T002 矩阵） |
| CAP-2 选择性激活 | PASS（T007） |
| CAP-3 少重复基础设施 | PASS（T003/T004/T005） |
| CAP-4 真实连续性 | PASS（T010：Turn 2 收到 Turn 1 历史，实测验证） |
| CAP-5 真实 FDE 业务证明 | **PENDING**（= T013 实跑） |
| CAP-6 回归 | PASS（含一个已知的 T013 manifest 漂移例外） |

---

## 需要处理/提醒的事项

> 更新（2026-08-19，用户指示"结合分析和结论一起修"后）：**1、2（登记部分）、3、4 已在本轮修完**，
> 落地为 `main` 上的一个提交。剩余仅：T013 真实凭据实跑（CAP-5），以及可选的 gateway-history 分支清理。

1. **分支调和（支线 C）—— 已处理（trace 文档已并入 main）**：`docs/gateway-continuity-trace.md`
   已从 `gateway-history`（e2bbe57）复制进 `main` 并登记。`gateway-history` 分支与 main 各有一份同名
   `tests/test_gateway_continuity.py`（内容不同，main 版更强，含 /new 不泄史守卫）。合并前需去重；
   若不再需要，可关闭/删除该分支。
2. **T013 收尾 —— 登记已完成，实跑待凭据**：`tools/fde_two_turn_proof.py` 现已提交并登记进 manifest
   （全量套件恢复全绿）；真实两轮运行仍需真实模型凭据，完成后 T013=PASS、T014=STOP、CAP-5=PASS。
3. **cosmetic —— 已修**：3 处过时 docstring（`composition.py` 模块 + `resolve_profile`、`cli.py`
   `profile check` help）已改为"冲突由 upstream composition 拥有"；`providers.py` 的 FURB188
   （`endswith`+切片 → `removesuffix`）一并修复。
4. **hygiene —— 已修**：`tools/regen_manifest.py` 现显式排除 `__pycache__/*.pyc`；manifest 中 4 条
   pyc 脆弱条目已移除，`docs/upstream-baseline.md` 所述"manifest 不再绑死构建产物"自此成立。