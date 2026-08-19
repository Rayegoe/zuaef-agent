---
title: 'Phase 2 产品验收与收口'
type: 'feature'
created: '2026-08-19'
status: 'ready-for-dev'
review_loop_iteration: 0
context: ['{project-root}/zuaef-phase2-product-completion-v1.0/SPEC.md', '{project-root}/zuaef-phase2-product-completion-v1.0/TASKS.md']
---

<frozen-after-approval reason="人类确认的 Phase 2 收口目标；未经重新协商不得改变">

## Intent

**Problem:** Phase 2 结构代码和定向测试已在 dirty working tree，但 P2-1～P2-8 尚无完整产品证据；真实 Gateway 两轮 FDE、Case 连续性、材料/产物和 approval 仍未证明。

**Approach:** 先审计现有变更，运行 Ruff 和全量回归；只有真实 acceptance proof 暴露缺口才改代码，最终以 `GatewayService + stillevo-fde + bound Case + literal turns + real model` 收口。

## Boundaries & Constraints

**Always:** 保留 Phase 1；权限为 host ceiling ∩ profile request 且冻结到 snapshot；业务域使用 upstream deferred loading；Gateway 机械绑定 Case，工具执行隔离；Turn 2 不注入隐藏提醒；外发只走现有 approval/resume；证据来自 receipt、StepPersistence、Case trajectory、artifact verification 和 tool effects。

**Ask First:** 仅当出现无法归属的变更、需删除非 Phase 2/runtime 文件，或证据要求扩大范围时暂停；已确认的 dirty tree 不得覆盖。

**Never:** 不新增 harness、router、agent registry、workflow、RBAC、database、event bus、vector store 或 custom ToolSearch/Memory/history；不重写插件；不把 runtime state、凭据或 proof residue 盲目提交；不以 `ace-writing` 单独 proof 或定向单测宣称完成。

## I/O & Edge-Case Matrix

| 场景 | 输入 / 状态 | 预期 | 错误处理 |
|---|---|---|---|
| 权限 | host 拒绝、profile 请求开启 | effective 关闭且 identity 可重放 | 模型不可绕过 |
| 发现 | stillevo-fde、bound Case、writing 请求 | Case 初始可见；Writing/Budget/WordPress 延迟，ToolSearch 只加载相关域 | 无 tool_search 则组合失败 |
| 两轮 | 两条 literal Golden Turn | 同 Case/conversation、不同 run；保留 no-price 和背景 | 缺 history/Case/产物则 PARTIAL/BLOCKED |
| 外发 | send_to_customer | PausedRun 后 approve/deny 都经 shared resume | 禁止自动发送 |
| residue | fixture、proof 输出、runtime state 混合 | 逐项归类后只留有意源码/fixture/docs | 无法归属时暂停 |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/config.py:40-128`、`profiles.py:43-177` -- generalist/defer schema 与 host ceiling。
- `src/zuaef_agent/composition.py:197-342`、`plugin_api.py:71-147` -- resolve、snapshot identity、DeferredLoadingToolset。
- `src/zuaef_agent/gateway/store.py:26-255`、`gateway/models.py:55-81` -- SQLite Case binding、迁移、`/new` 保留 Case。
- `src/zuaef_agent/gateway/service.py:95-266`、`gateway/bridge.py:100-146`、`models.py:120-128` -- dispatch、`CoreDeps.case_id`、approval 路径。
- `plugins/zuaef-case/zuaef_case/toolset.py:74-278`、`src/zuaef_agent/runtime.py:109-150,630-679` -- isolation、pause frontier、receipt。
- `profiles/stillevo-fde.toml:19-62`、`tools/fde_two_turn_proof.py:1-783` -- deployment 和权威 proof；后者必须真实运行。
- `tests/test_phase2_*.py` -- 确定性机械证据，不能替代真实 proof；`workspace/cases/stillevo-beauty/situation.json` 是待分类的 fixture/runtime 变更。

## Tasks & Acceptance

**Execution:**
- [ ] 按 CODE、FIXTURE、PROOF ARTIFACT、RUNTIME STATE、UNRELATED 审计全部 diff，并映射 P2-T003～T016。
- [ ] 运行 Ruff、全量 pytest、Phase 2 定向测试；只修复可复现缺口。
- [ ] 运行真实两轮 proof，核验 Case/material/artifact/history/price/publish/loaded-dormant/approval 证据。
- [ ] 更新 README、`.env.example`、profile/Gateway 文档，清理 residue 和重复 proof authority，最后只提交有归属变更。

**Acceptance Criteria:**
- Given profile 与 host ceiling，when resolve/resume，then P2-1 交集、冻结 identity 和兼容性可验证。
- Given bound `stillevo-fde`，when 初始运行并 ToolSearch，then P2-2 可见/加载/休眠域符合 SPEC。
- Given 两次 Golden Turn，when 经 Gateway，then P2-3～P2-5 的 Case/conversation/run、history、材料、产物和 no-price 证据齐全。
- Given customer-visible send，when approve 或 deny，then P2-6 走同一 continuation 且身份保持。
- Given 回归和文档通过，then 输出 `PHASE 2 = 100% — STOP`；否则如实 PARTIAL/BLOCKED。

## Design Notes

定向测试证明机械约束，真实 proof 证明产品 seam。Case 仅保存 ACE 资源引用，正文由 ACE 工具读取；源码 Case 与 `/tmp` proof workspace 分离。

## Verification

**Commands:**
- `uv run ruff check .` -- lint 通过。
- `uv run pytest -q` -- 全量回归通过。
- `uv run pytest -q tests/test_phase2_*.py` -- 定向证据通过。
- `uv run python tools/fde_two_turn_proof.py --workspace /tmp/zuaef-fde-proof-p2` -- real model 可用时 P2-4～P2-6 PASS，并输出 receipt/trajectory/artifact evidence。

