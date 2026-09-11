# Research Capability via Harness Skills

## 1. Research 方法论放 Skill

新增 Quant research skill，例如：

```text
plugins/zuaef-quant/skills/quant-research/SKILL.md
```

通过现有 Harness `Skills` Capability 加载。

不要把复杂 methodology 全塞进 `QUANT_INSTRUCTIONS`。

---

## 2. Skill 定义的内容

### Full Analysis

覆盖：

```text
current market
trend/volume
history
strategy context
portfolio
structured finance evidence
open web research when useful
sandbox-derived statistics
scenario forecast
recommendation
unknowns
```

---

## 3. Skill 不规定固定执行顺序

它提供：

```text
evidence hierarchy
coverage checklist
degradation rules
forecast methodology
result semantics
```

Agent 自主选择必要能力。

---

## 4. Evidence hierarchy

```text
canonical trade/market state
structured official evidence
structured public evidence
customer-reported evidence
sandbox-derived evidence
LLM interpretation
```

Interpretation 永远不是 observed fact。

---

## 5. Research status

```text
COMPLETE
PARTIAL
INSUFFICIENT_EVIDENCE
```

这些是业务研究状态。

Runtime：

```text
completed
failed
limit_reached
```

是另一层。

两者不得混淆。
