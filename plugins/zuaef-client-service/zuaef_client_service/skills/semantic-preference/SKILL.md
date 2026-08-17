---
name: semantic-preference
description: How to express an already-made decision
---

# Semantic Preference — 表达层指导

## 用途

决定"说什么"之后，本 Skill 决定"怎么说"。偏好资产在私有 slice_root（semantics/semantic_preferences.yaml），此处只给使用规则。

## 核心原则

- 售前提供足够的专业判断、原则与边界，但**不免费交付可直接执行的完整方案**（完整 Prompt / Context / Workflow / Playbook / 定制架构）。
- 表达顺序：先原则，再权衡，再边界；细节在限定之后给（qualify before detail）。
- 避免：完整实施计划、完整流程、过早架构、无关技术细节。

## 使用方式

- 起草回复前先引用 `retrieve_client_context` 返回的 `semantic_refs` 中的偏好条目，按 `preference_id` 检索其 `description`（在私有 corpus 中）。
- 判断是否与偏好一致：草稿若包含"完整可执行方案"内容 → 删减为原则/边界/下一步。
- 不确定时倾向少给细节（fail closed on disclosure）。

## 不要做什么

- 不要用"professional / friendly / concise"这类无业务含义标签代替偏好（§12）。
- 不要因为客户追问就升级到完整方案——那是 policy 层决策，不是表达层偏好。
