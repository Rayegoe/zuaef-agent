- source_spec: `_bmad-output/implementation-artifacts/spec-console-fact-fidelity-t016b.md`
  summary: 完成 T017/T018 的 Agent-readable projection 与 Markdown/JSON 互操作，并推进 T019–T023 的两个只读工具、Analyze 入口、analysis.md、Stillwrite 人工批注闭环。
  evidence: 用户明确要求先完成 T016B 的 Console Fact Fidelity Fix；Run Analysis 闭环需在 live、unknown、竞态与重试事实稳定后再实现。
- source_spec: `_bmad-output/implementation-artifacts/spec-zuaef-run-analysis-quality-hardening.md`
  summary: 加固 Analysis workspace 的 run ID 路径边界，拒绝 `.`、`..` 与超长文件名组件。
  evidence: 现有 `_safe_run_id` 允许点路径段，可能折叠或逃逸每个 subject 的 workspace；该问题早于本故事且不属于事实渲染职责调整。
- source_spec: `_bmad-output/implementation-artifacts/spec-zuaef-run-analysis-quality-hardening.md`
  summary: 为 `analysis.md` 写入补充原子独占创建与中断恢复语义。
  evidence: 现有 existence-check 后 `write_text` 存在 TOCTOU 与部分写入窗口；这是既有 artifact handoff 的耐久性问题，本故事未授权扩大写入机制。
- source_spec: `_bmad-output/implementation-artifacts/spec-zuaef-run-analysis-quality-hardening.md`
  summary: 审计 Analysis action 的跨 workspace transient state 隔离、线程启动失败清理与文件状态 reconciliation。
  evidence: `_in_flight`/`_results` 仅按 subject run ID 缓存且缺少生命周期清理；这是既有 action state 设计问题，不由 Host-owned facts 引入。
- source_spec: `_bmad-output/implementation-artifacts/spec-zuaef-run-analysis-quality-hardening.md`
  summary: 使 `selected_event` scope 真正约束 inspection，并验证与限制 `selected_row_id`。
  evidence: 现有 scope 只进入 prompt 文本，工具仍可读取 full run，且 row ID 无长度/换行校验；这是既有 Analysis API 语义缺口。
