---
name: sales-disclosure-boundary
description: Disclosure levels and approval levels for pre-sales
---

# Sales Disclosure Boundary — 披露边界

## 用途

本 Skill 规定售前对话中"什么可以披露、什么不可以、需要什么审批"。披露级别与审批级别定义见插件 models（§31/§32）。

## 披露级别（D0-D5）

- D0 公开：平台规则、行业常识。
- D1 一般原则：平台变化需要持续适配；模型不是首要变量。
- D2 服务范围：可做内容诊断、Agent 工作流、现有系统适配。
- D3 案例摘要：某类客户曾存在类似模板化问题（不点名、不给完整材料）。
- D4 实现细节：具体检索、审核、风格控制、工作流结构。
- D5 专属方案：客户专属完整架构、规则库、Prompt、工作流与代码。

## 审批级别（R0-R3）

- R0 只读（检索/总结/评估/策略匹配）：自动。
- R1 低风险建议（常规解释、已公开信息）：shadow 下仍只生成草稿。
- R2 商业风险（报价、案例披露、服务范围、资格判断、付费诊断建议）：必须人工批准。
- R3 高风险外部承诺（折扣、定制范围、合同、退款、保证结果、工期、独家）：必须人工批准。

## 硬规则

- 多 policy 命中时：restricted 优先于 allowed；approval 取最高；disclosure 取最低 ceiling（§57，fail closed）。
- 决策权或预算 unknown 时，禁止披露案例与完整方案（先资格后披露）。
- 任何 R2/R3 输出都不自动发出——草稿等待人工决定。
