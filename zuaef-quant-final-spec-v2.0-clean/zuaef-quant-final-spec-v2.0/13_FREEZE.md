# Final Freeze

这是当前阶段最终架构/Spec。

P0–P5 通过后，不因为看见新框架就再写 v2.1。

运行方式：

```text
DAILY: market -> scan -> Agent decision -> immutable report
FORWARD: decision -> future path -> outcome
RESEARCH: evidence -> Agent question -> experiment -> deterministic evaluation -> lesson
REVIEW: lessons + outcomes -> continue / adjust / retire
```

只有真实证据可以重新打开架构：

- semantic data failure；
- report 无法重放；
- Agent 遇到现有工具无法完成的真实研究动作；
- operational crash/effect ambiguity；
- forward evidence 需要新的数据模态；
- 新 strategy mechanism 真正需要新 capability。

以下不能作为理由：

- “别人的 Agent 更多”；
- “可以加向量数据库”；
- “schema 更规范”；
- “多一个工具更方便”；
- “再加指标看起来更专业”；
- “回测收益还不够高”。

North Star：**更少的无依据交易，更高质量的可解释决策，更可靠的策略证据，更快地从真实结果中学习。**
