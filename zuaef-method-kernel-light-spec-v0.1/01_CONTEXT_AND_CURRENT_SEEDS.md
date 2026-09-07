# Context & Existing Seeds

## 1. ZUAEF 已经有的种子

本专项不是从零搭建。

### Core Instructions

当前 `src/zuaef_agent/core.py` 已经包含：

- outcome ownership；
- tools are capabilities, not mandatory workflow；
- complex work may plan, but no process for process's sake；
- inspect existing files/knowledge before replacements；
- distinguish observed facts from assumptions；
- name unknowns instead of guessing；
- large tool outputs are retrieval material。

这些已经属于 Method Kernel，只是还没有被明确收敛。

### Independent Reviewer

当前：

```text
tools/llm_reviewer.py
```

已经要求 reviewer：

- 不看 human opinion；
- 独立判断；
- 检查实际完成了什么；
- 检查遗漏；
- 检查事实来源；
- 检查推理、结构、业务判断；
- 提出可泛化 lesson；
- 允许“没有可复用 lesson”。

这是“独立审查 / falsification”的现成基础。

### Human-gated Promotion

当前：

```text
tools/promote_lesson.py
```

已经明确：

- LLM 不能自己宣布 lesson 生效；
- human review 是 authority；
- promoted unit 可以是 guideline / example / plugin fix / skill；
- promotion 可独立版本化和删除。

这已经非常接近“promote proven intervention”。

---

## 2. 当前缺口

### G1 — 方法论散落

Core、reviewer、learning loop 各有一部分原则，但没有一个统一的“元级契约”。

### G2 — Skill 仍容易成为默认沉淀单位

未来更合理的是：

```text
failure / success
→ hypothesis
→ intervention
→ ablation
→ keep / simplify / replace / delete
```

Skill 只是 intervention 的一种。

### G3 — 缺少真正的 Ablation Harness

当前还没有一个非常轻的标准机制，用同一组 cases 比较：

```text
baseline
vs
candidate intervention
```

并观察：

```text
quality
completion
factual errors
requests
tokens
tool calls
latency
```

### G4 — Reviewer 尚偏 writing/learning case

需要泛化成：

```text
implementation
research
architecture
business artifact
quant result
```

都能使用的 independent critic primitive。

---

## 3. 明确不做

本专项不引入：

- 新 Agent；
- 新 Multi-Agent topology；
- Swarm / Graph；
- 新 Workflow Engine；
- 新 Skill Registry；
- 新数据库；
- 新 Memory 系统；
- 固定八步执行流程；
- 每个任务强制 reviewer；
- 每个任务强制 ablation。
