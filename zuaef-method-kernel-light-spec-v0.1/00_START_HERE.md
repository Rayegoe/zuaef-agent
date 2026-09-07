# ZUAEF Method Kernel — Lightweight Spec v0.1

## 目标

把 ZUAEF 中已经存在但分散的“好方法”收敛成一个很薄的元级方法论内核：

> 不规定每类任务具体怎么做，只规定面对未知问题时，怎样重建事实、判断证据、减少不确定性、寻找反例、选择最小干预，并把真正有效的方法沉淀下来。

这不是新的 Skill 系统，不是 Workflow，不是 Governor，不是 Multi-Agent Framework。

---

## 背景

近期 ZUAEF 在 Quant、Runtime、StillWrite、Case 等项目里反复出现同一种问题：

- 模型会做很多事，但容易被长上下文、工具轨迹、旧假设带偏；
- 一旦缺少数据或某个能力没接上，容易把内部缺口转嫁给用户；
- Skill / Prompt / Tool 会不断增加，但缺少“它到底有没有用”的系统证据；
- 有些通用方法其实已经被更强模型内化，继续维护长篇 Skill 的边际价值越来越低；
- 真正长期有价值的不是“某个固定流程”，而是第一性原理、证据意识、反例、消融、奥卡姆剃刀、不确定性和模块边界。

因此提出：

> Skill 可以退休；方法论和证据机制应长期存在。

---

## Method Kernel 六条原则

1. **Reconstruct reality before proposing change.**  
   先确认问题真实存在、当前状态、成功条件和根因。

2. **Evidence outranks explanation.**  
   完整故事不能替代证据；区分观察、推导、判断。

3. **Prefer the smallest intervention that can prove the outcome.**  
   能修一个 seam，就不要先造一个 framework。

4. **Make material uncertainty explicit.**  
   重要未知、未测试场景和假设必须显式存在。

5. **Try to falsify important conclusions.**  
   高价值结论应主动寻找反例、替代解释或独立审查。

6. **Promote only what survives evidence.**  
   Skill、Prompt、Tool、规则、架构只有经过真实案例验证才进入长期系统。

---

## 最核心的一句话

> What is the cheapest experiment that would most reduce uncertainty about the outcome?

中文：

> 现在做什么最小动作，最能减少对最终结果的不确定性？

这句话是本 Spec 的最高优先级。
