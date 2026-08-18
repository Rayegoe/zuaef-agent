# Writing v0.2 — 人工盲评操作说明（Phase 9 剩余动作）

这是 v0.2 唯一未闭环的验收步骤：**Writing Quality 需要人类证明**。
机器门已确认事实完整与运行约束；这里判断的是文章质量。

## 要做的事（按顺序）

1. **WCASE 评审**：读 `wcase-review-sheet.md`，对 WCASE-1..4 四份成品逐维度打分，
   写书面编辑注记。WCASE-4 请分别评 draft 与 revision，判断修订是否实质回应反馈。
2. **Editorial A/B 盲评**：读 `editorial-ab-sheet.md`，只凭两篇成品（样品X/Y）打分，
   **不要先看 `editorial-key.md`**。重点看：模板感、叙事推进、过早解释、具体性、
   可发表性，以及是否有事实退化。
3. 盲评完成后打开 `editorial-key.md` 核对哪份是 ON。记录结论：
   - ON 稳定优于 OFF → 考虑默认开启（并启动 Editorial Intelligence follow-up SPEC 评估）
   - 无稳定优势 → 按 SPEC §20，`editorial_control` 保持 optional/experimental，
     不继续加 sensor。

## 维度说明（SPEC §26）

| 维度 | 看什么 |
| --- | --- |
| Task Fitness | 是否真正完成所指任务 |
| Selection | 多材料时是否抓到重要材料 |
| Fact Integrity | 是否越界或编造（机器门已查，人工复核） |
| Structure | 结构是否自然有效 |
| Human Presence | 是否有人、场景、具体观察 |
| Language | 是否模板化、概念化 |
| Revision Quality | 修改是否回应反馈 |
| Overall | 编辑是否愿意继续采用（权重最高） |

## 已出结论（2026-08，盲评完成）

- **样品Y（Editorial Control OFF）质量更好**（Overall：Y > X）。
- 决策（SPEC §20）：Editorial Control **保持 optional**——生产默认
  `ace-writing` 已改为 `editorial_control = false`；ON 侧可按需使用
  `profiles/ace-writing-editorial.toml`。不再追加 machine sensor。
- WCASE 评审表仍可继续填写以积累写作质量证据，但 v0.2 的决策闭环已达成。

## 已知运行接口缺陷（与写作能力无关，勿计入评分）

- WCASE-4 修订轮 receipt 为 `partial`，根因是 RunSummary 的 artifacts 引用漏了
  `artifacts/` 前缀（host 校验拒绝该引用）。修订稿**已实际保存并经 host 验证**
  （`revision.md`），修订内容达到目标。已在提示词中写入字面示例，后续运行应 completed。
- A/B 的 ON 侧为 `partial`，同样属于 summary 引用格式问题，产物已保存。