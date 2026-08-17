---
name: client-service
description: Client service pre-sales decision workflow
---

# Client Service Decision Slice — 工作流程

## 用途

本 Skill 定义 Client Service 售前对话中"如何走完整流程"，不包含任何真实客户内容。

## 流程（shadow mode，§33）

1. `retrieve_client_context(customer_id, query)` — 先取最小上下文：客户状态、知识、语义偏好、policy 候选、evidence 引用。
2. `assess_customer(customer_id, message)` — 生成结构化评估（stage / signals / authority / budget / uncertainties / evidence_ids）。**Unknown 必须显式保留，不许猜**（§48）。
3. `select_response_strategy(customer_id, assessment)` — 取确定性策略：strategy、matched policies、allowed/restricted actions、approval_level、disclosure_ceiling、evidence_ids。
4. 依据 strategy + semantic preferences + retrieved evidence 起草回复。**工具产出判断，模型产出表达**（§9）——不发明案例、价格、承诺或政策禁止的动作。
5. R2/R3 决策只是草稿，等人工批准；`record_interaction` 在批准后才记录。

## 硬约束

- 没有匹配到任何 policy 时，strategy 必须是 `REQUEST_MORE_CONTEXT`，不得自行发明策略（§30 封闭词汇、§41）。
- 非 unknown 判断必须有 evidence 支持（§41）；推断必须标记。
- 禁止承诺平台结果、免费完整方案、外包承接、折扣或合同（§32 R3、§16/§22 policy）。

## 终止状态（§47）

- completed：assessment + strategy + draft 齐备。
- partial：knowledge 可读但 state 不完整（unknown authority/budget）——仍可给有限建议，但要标明。
- blocked：corpus 损坏或 policy 无法解析——不要伪造结果继续。
