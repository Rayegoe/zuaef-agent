# Minimal Change Plan

## P0 — Baseline

### T000

核对当前：

```text
src/zuaef_agent/core.py
tools/llm_reviewer.py
tools/promote_lesson.py
learning/
tests/
```

输出：

```text
REUSE
EXTEND
MISSING
```

禁止先重构。

---

## P1 — Method Kernel

### T001 — Core Principles

在 `CORE_INSTRUCTIONS` 中加入/收敛 6 条原则。

要求：

- 短；
- 不超过约 150–250 英文 token；
- 不加入固定 checklist；
- 不包含 Quant/StillWrite 等 domain 名称；
- 不重复 Harness 已经做的功能。

### T002 — Regression

跑现有 Core tests，确保简单任务没有因为元原则而变成长流程。

---

## P1 — Reviewer

### T003 — Generalize Reviewer

让当前 `llm_reviewer.py` 可以审查：

```text
writing
implementation
research
architecture
business artifact
```

保持 prose-first，不引入 enum taxonomy。

### T004 — Independent Review Proof

选一个历史真实 case，证明 reviewer 能指出主实现遗漏，而不是复述主 Agent。

---

## P1 — Learning Promotion

### T005 — Intervention-neutral Promotion

修改 promotion 文案和数据语义：

从：

```text
lesson → skill/example/plugin
```

升级为：

```text
accepted intervention
```

允许：

```text
keep
simplify
replace
delete
```

### T006 — Retirement Candidate

支持人工标记某个 Skill / rule 为 retirement candidate。

不自动删除。

---

## P1 — Ablation

### T007 — Minimal Ablation Runner

复用现有：

```text
profiles
runtime
receipts
tests/evaluators
```

实现 baseline vs candidate。

### T008 — First Real Ablation

建议先测试一个真实对象：

```text
Quant Research Skill
with
vs
without
```

或：

```text
某条长 prompt
with
vs
without
```

用真实 cases 比较。

---

## P2 — Optional Runtime Integration

### T009

若后续有价值，可让 Agent 在高风险任务结束前自行提出：

```text
independent review recommended
ablation recommended
```

但不自动强制执行。

---

## Stop Condition

如果 T001 + T003 + T005 + T007 已经能证明：

```text
方法论原则可复用
review 可独立发现问题
ablation 能淘汰无效 scaffolding
```

就停止专项。

不要继续扩成平台。
