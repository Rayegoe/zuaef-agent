# Learning & Promotion

## 1. 从 Lesson Promotion 升级为 Intervention Promotion

旧思路：

```text
case
→ lesson
→ skill
```

新思路：

```text
case
→ independent review
→ hypothesis
→ smallest intervention
→ ablation
→ keep / simplify / replace / delete
```

---

## 2. Intervention 类型

允许：

```text
NOTHING
CORE PRINCIPLE
PROMPT LINE
EXAMPLE
TEST
TOOL FIX
PLUGIN FIX
DATA FIX
SKILL
ARCHITECTURE FIX
DELETE EXISTING SCAFFOLDING
```

这意味着“删除 Skill”也是成功的 learning outcome。

---

## 3. Promotion 标准

只有在真实证据表明：

```text
candidate > baseline
```

或者：

```text
candidate fixes a reproducible failure
```

时才长期保留。

---

## 4. Skill Retirement

新增概念：

```text
RETIREMENT CANDIDATE
```

当出现以下情况：

- 模型升级后 without Skill ≈ with Skill；
- Skill 只重复通识；
- Skill 增加 token/tool confusion；
- Skill 与 Core/Harness 能力重复；
- 真实案例证明没有边际价值；

则应：

```text
simplify
or
delete
```

---

## 5. Promotion 不自动化

保留当前原则：

```text
human review remains authoritative
```

LLM 可以提出：

```text
promotion candidate
retirement candidate
```

但不能自己改写长期系统规则。
