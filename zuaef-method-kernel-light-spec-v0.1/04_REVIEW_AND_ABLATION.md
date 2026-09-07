# Independent Review & Ablation

## 1. 泛化 llm_reviewer

不要新建 Reviewer Framework。

复用/扩展：

```text
tools/llm_reviewer.py
```

把输入 contract 泛化成：

```text
task
context/evidence
result
validation evidence
source pointers
```

Reviewer 保持独立，不接收主 Agent 的“自我解释”作为 authority。

---

## 2. Reviewer 核心问题

至少覆盖：

```text
What was actually accomplished?
What is actually proven?
What is merely claimed?
What important requirement was missed?
What evidence is weak or missing?
What counterexample could break the conclusion?
Is there a simpler explanation or implementation?
What should be preserved?
What, if anything, is generalizable?
```

---

## 3. Reviewer 触发条件

不是每次调用。

建议用于：

```text
release candidate
important architecture change
customer-critical deliverable
high-cost research result
strategy/policy change
learning promotion candidate
```

---

## 4. Ablation Harness

新增一个极薄的 experiment runner。

目标：

```text
same cases
same model
same evidence
same evaluator
baseline config
vs
candidate config
```

比较：

```text
outcome quality
task completion
factual errors
requests
input/output tokens
tool calls
latency
```

---

## 5. Ablation 对象

可以比较：

```text
with / without Skill
with / without prompt line
with / without tool
with / without capability
old / new plugin behavior
old / new context policy
```

---

## 6. 不建立统一单分数

不要硬凑一个：

```text
AGENT_SCORE = 87
```

保留多维证据。

不同任务可以使用不同 evaluator。

---

## 7. 最小 CLI

建议最终有类似：

```bash
uv run python tools/ablate.py \
  --cases learning/cases/... \
  --baseline profiles/base.toml \
  --candidate profiles/candidate.toml
```

具体 CLI 以当前项目风格决定，不强制字段名。
