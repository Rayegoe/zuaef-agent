# T015 Kernel 冻结收尾记录

日期：2026-08-20
基线：`14e0df06012c4b925012d3ee9be0734af0282a7d`
实现起点：`9c76eadbc726afd531f333bc735a521f83dfb225`

## 当前判定

**T015 尚未 PASS。** Kernel 的目标边界和冻结准入规则已落盘，遗留代码清理与 Gateway 分层也已闭合；但 T012 的五例 baseline/learned 人工比较尚无新格式产物，当前也没有运行中的 `run_writing_eval` 进程。`BUILD_MANIFEST.json` 因 T012/T014A/T014B 新文件和模块移动尚未最终再生，因此冻结门禁保持 **BLOCKED**，不以 schema 或旧测试结果冒充完成。

## 前序门禁证据

| 范围 | 证据 | 状态 |
|---|---|---|
| T000 | `docs/t000-baseline-audit-v1.2.md` | PASS |
| T001–T003 | commit `92e29f4`：receipt v2、integrity-only settlement | PASS |
| T004–T006 | commit `2780224`：opaque bindings、Case-owned context/isolation | PASS |
| T007 | commit `7efdd80`：document-first KnowledgeStore | PASS |
| T008/T013 | commit `12e54e0` 与 `tests/test_architecture_guards.py` | PASS |
| T009–T011 | commit `9c76ead` 与 `learning/cases/summer-nail-rewrite-20260819/` | PASS |
| T012 | 未发现 `eval/WCASE-*/baseline/`、`learned/` 与人工 pairwise judgment；无活动进程 | **BLOCKED** |
| T014A | `zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/T014A_RECORD.md`；三域真实插件共用自然 `str`/`RunReceipt` | PASS |
| T014B | `zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/T014B_AUDIT.md`；editorial control 降级为 benchmark/legacy，生产 factory 拒绝 | PASS |
| T014 最终回归 | plugin list/inspect/profile 已过；pytest/manifest 最终轮未过 | **BLOCKED** |

## 最终边界

- `src/zuaef_agent/verification.py` 与 `tests/test_verification.py` 已删除；Kernel 只保留 `integrity.py` 的路径包含、SHA-256、变更检测与 StepStore 事件投影。
- Case bounded context 位于 `plugins/zuaef-case/zuaef_case/context.py`；Kernel 只冻结 opaque `bindings`。
- surface、actor role 与回复传输事实位于 `src/zuaef_agent/gateway/interaction_projection.py`。旧根模块不存在，生产 import 全部为 Gateway-local。
- `receipt_store.py` 没有历史 receipt adapter；架构守卫不再为其保留例外。
- editorial sensors/veto/weight 仅在 `benchmarks/editorial-learning/legacy/`，生产插件和 profile 拒绝 `editorial_*`。

冻结后 Kernel 只因六类原因修改：PydanticAI/Harness 兼容、执行正确性、安全边界、durability/resume 正确性、composition ABI、通用操作事实。业务能力需求本身不是修改 Kernel 的理由。

## 代码形态（描述性指标）

- 对比基线的当前选定交付面：60 个文件变化，2730 行增加、2308 行删除。新增主要是回归/架构测试和真实学习证据，不是新 runtime/framework。
- 旧 `verification.py` 有 1 个异常类和 10 个函数；新 `integrity.py` 有 1 个异常类和 7 个函数，净删除 `verify_knowledge`、`parse_evidence_ref`、`verify_tool_effect` 三个语义函数。
- terminal receipt 字段：23 → 21；`verified_*`、`summary`、`degraded`、`status=partial` 被操作性 `execution_state`、`outcome`、artifact/tool-effect facts 替代。pause receipt 维持 18 字段，但删除 semantic evidence 字段并加入 bindings/facts。
- 核心执行模块（models/runtime/core/continuation/composition/receipt_store）的 `case_id` 出现次数：17 → 0。
- 删除生产 `editorial.py`，保留为显式 benchmark/legacy 资产；没有新增 registry、result schema、workflow runtime 或 event bus。

## 本轮命令与结果

```text
pytest -q tests/test_interaction_projection.py
10 passed

pytest -q tests/test_architecture_guards.py
7 passed

ruff check .
All checks passed

zuaef-agent plugin list
PASS（6 个插件）

zuaef-agent plugin inspect zuaef-emtb-budget
PASS（0.1.0，既有 entry point）

zuaef-agent profile check stillevo-fde --config-root .
PASS（composition_id 已生成，薄 PluginBundle ABI 未变）
```

较慢的 agent-loop 定向组合在 180 秒内超时，未出现失败断言；单独定位到 `test_deferred_case_plugin_absent_from_initial_surface` 与 `test_start_profile_run_completes_and_propagates_identity` 的既有慢路径。`tests/test_result_contract.py` 当前实际收集 3 项，首个三域用例在 600 秒仍未完成。超时不是 PASS，T014A 的既有真模型产物仍保留，但当前最终回归轮保持 BLOCKED。

Manifest 当前准确失败为：`AGENTS.md` hash/size drift，以及缺少 `gateway/interaction_projection.py`、`tests/test_result_contract.py`、`tools/pairwise_review.py`、`tools/result_contract_proof.py`。T012 文件面稳定后运行 `tools/regen_manifest.py`，随后重跑 manifest 与全量 pytest。
