---
title: 'T015：删除遗留死代码并冻结 Kernel'
type: 'refactor'
created: '2026-08-20'
status: 'in-progress'
baseline_commit: '9c76eadbc726afd531f333bc735a521f83dfb225'
review_loop_iteration: 0
context:
  - '{project-root}/zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/TASKS.md'
  - '{project-root}/zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/ACCEPTANCE.md'
  - '{project-root}/zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/DECISIONS.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem：** T001–T014B 已完成主要减法，但 README 仍描述 `verified_*`、Kernel 直接接收 `case_id` 和模型声明 evidence refs；架构测试也为实际不存在的 receipt adapter 留有例外。直接冻结会让文档、守卫与代码矛盾。

**Approach：** 核验前序门禁，删除失真的例外与旧术语，更新 README/AGENTS 并留下可复现的减法记录。只有真实证据齐全才宣布冻结；缺凭证、环境或人工判断时明确记为 `NOT RUN`/blocked。

## Boundaries & Constraints

**Always：** 保留当前未提交的 T014A/T014B 成果；Kernel 仅拥有通用执行、完整性、审批、持久化、恢复、组合 ABI 与操作事实；Gateway 可持有 Case 路由字段，进入 Kernel 后只能是 opaque `bindings`。

**Ask First：** 若需绕过“所有前序门禁先通过”、删除真实历史数据仍需的 adapter，或改变 receipt v2、Plugin ABI、审批语义，停止并询问。

**Never：** 不新增 registry、通用 ResultSchema、Binding Framework 或 workflow state machine；不兼容双写，不伪造人工/真实运行证明，不删除仍覆盖现行行为的测试。

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/gateway/interaction_projection.py` -- 已从 Kernel 根目录暂存 100% rename；唯一生产调用者为 `gateway.bridge.start_profile_run`。`bridge.py`、`gateway/models.py` 和投影测试仍引用旧模块，须闭合移动。
- `src/zuaef_agent/{integrity.py,models.py,receipt_store.py}` -- 完整性与 receipt v2 边界；无历史 adapter，不恢复语义 verification。
- `plugins/zuaef-case/zuaef_case/context.py` -- Case-owned context；与 Gateway-owned interaction facts 分层。
- `tests/test_architecture_guards.py` -- T014B 守卫已加入；T015 删除虚构 adapter 豁免并冻结旧标识、薄 ABI 与无替代框架。
- `T014A_RECORD.md`、`T014B_AUDIT.md`、`tests/test_result_contract.py` -- 前序三域真实插件 proof 与 Pydantic-not-workflow 审计，直接引用而不重做。
- `README.md`、`AGENTS.md`、`docs/t015-kernel-freeze.md` -- 修正文档并记录减法、门禁、`NOT RUN`。
- `BUILD_MANIFEST.json` -- 等 T012 新 skill/比较资产稳定后最终再生，避免锁定临时文件集。

## Tasks & Acceptance

**Execution：**
- [x] `src/zuaef_agent/gateway/{bridge.py,models.py}`、`tests/test_interaction_projection.py` -- 改为 Gateway-local import；保持投影文本、调用顺序和写作运行面不变。
- [x] `tests/test_architecture_guards.py` 及含旧术语的行为测试 -- 删除无依据豁免，中性化名称/注释，保留覆盖。
- [x] `README.md`、`AGENTS.md`、`docs/t015-kernel-freeze.md` -- 对齐边界并记录冻结准入、真实门禁与最终增删。
- [ ] `BUILD_MANIFEST.json` -- T012 文件面稳定后再生；随后跑全量、定向、插件/profile 与 manifest 检查。

**Acceptance Criteria：**
- Given interaction projection 已迁入 Gateway，when 导入并运行投影/Gateway 测试，then 所有引用只走 `zuaef_agent.gateway.interaction_projection`，行为不变且生产写作面不受影响。
- Given Kernel 源码，when 执行守卫与旧标识搜索，then 无 semantic verification、根级交互/Case 投影、死 adapter 或替代 registry/framework。
- Given README/AGENTS，when 阅读边界，then 与代码一致并列明冻结后允许修改 Kernel 的六类原因。
- Given pytest、ruff、composition、pause/resume、三域 proof 与 manifest 门禁，when 执行，then 全部成功；缺人工/凭证/环境则记录 `NOT RUN`/blocked，不虚报冻结。
- Given baseline `14e0df06012c4b925012d3ee9be0734af0282a7d`，when 统计增删，then 记录可复核且体现概念减法。

## Spec Change Log

## Verification

**Commands：**
- `env UV_CACHE_DIR=/tmp/zuaef-t015-uv-cache uv run ruff check .` -- 无错误。
- `env UV_CACHE_DIR=/tmp/zuaef-t015-uv-cache uv run pytest -q tests/test_interaction_projection.py tests/test_gateway_bridge.py tests/test_gateway_service.py tests/test_architecture_guards.py tests/test_result_contract.py tests/test_manifest_integrity.py` -- 关键边界通过。
- `env UV_CACHE_DIR=/tmp/zuaef-t015-uv-cache timeout 600 uv run pytest -q` -- 全量通过。
- `env UV_CACHE_DIR=/tmp/zuaef-t015-uv-cache uv run zuaef-agent plugin list`、`plugin inspect zuaef-emtb-budget`、`profile check stillevo-fde --config-root .` -- 薄 ABI/profile 正常。
