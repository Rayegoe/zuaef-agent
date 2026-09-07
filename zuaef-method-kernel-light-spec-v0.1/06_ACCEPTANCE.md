# Acceptance

## A. Core

简单问答不应因为 Method Kernel 而：

```text
自动规划
自动 reviewer
自动 ablation
```

复杂 debug/architecture 任务应明显更倾向：

```text
先复现
先找证据
先最小修复
```

---

## B. Reality Reconstruction

选一个历史事故，例如：

```text
600550 history cache miss
```

Agent 应能识别：

```text
已有 fetch_history
缺口是 orchestration seam
```

而不是提出新 Data Platform。

---

## C. Reviewer Independence

Reviewer 不读取 human final decision。

Reviewer 能指出至少一个主实现未显式承认的：

```text
missing evidence
untested case
simpler explanation
```

---

## D. Ablation

同一个真实 case：

```text
baseline
candidate
```

有可比较运行事实。

至少记录：

```text
completion
quality evaluator
requests
tokens
tool calls
latency
```

---

## E. Skill Retirement

必须证明系统支持这样的结论：

```text
“这个 Skill 没有显著边际收益，建议删除。”
```

而不是所有 learning 结果只能新增资产。

---

## F. No New Framework

最终 diff 不应出现：

```text
method_engine/
reasoning_workflow/
critic_scheduler/
meta_agent/
```

除非真实失败证明不可避免。
