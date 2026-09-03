# Agent Participation + Harness Reliability

## 两种运行态

### A. Decision Mode

用于今天的真实决策：

- active strategy 冻结；
- data/evaluator/cost/market rules host-owned；
- 不研究、不改参数、不改代码。

Agent 必须：

1. 读取 deterministic trigger evidence；
2. 结合 candidate quality / risk / data state；
3. 给 `NO_TRADE / WATCH / ENTER_CANDIDATE / HOLD / REDUCE / EXIT`；
4. 写 why + invalidation + uncertainty；
5. 保存 Decision Brief。

典型 daily run 不应因为“Agent 要有参与感”疯狂调工具。现有 `get_live_signals + record_decision_brief` 通常足够。

### B. Research Mode

Agent 不是数值参数按钮。它可以：

- 读 Research Log / Lessons / Open Questions / forward evidence；
- 自主选择高价值未知；
- 提出经济机制与可证伪假设；
- 设计 ablation/factor/exit/regime test；
- 提出新 factor / entry / exit / event mechanism；
- 必要时驱动 Engineering Agent/Codex 在**隔离 experiment worktree**实现代码；
- 读 deterministic evaluator 结果；
- 对照 parent/baseline；
- 主动 REJECT 自己的假设；
- 更新 Lesson impact 和 Next Question。

禁止：

- 同一 live run 自改 active strategy；
- 自改 evaluator/cost/split 后自己宣称成功；
- 自动 promotion；
- 删除失败实验；
- 只保存 winner。

## Agent Participation Proof

验收必须出现一次**非 host 预写答案**的 Research Run：

`recall -> choose uncertainty -> hypothesis -> experiment -> deterministic evidence -> comparison -> reject/support -> lesson -> next question`

如果永远只是固定 A0→A1→A2 或改几个 numeric threshold，判定 `FAIL_AGENT_PARTICIPATION`。

## Harness

直接复用 Pydantic AI/Harness：

- StepPersistence；
- run/conversation lineage；
- tool-effect ledger；
- approval boundary；
- OpenTelemetry instrumentation；
- existing workspace/filesystem。

不要造 quant-specific Agent runtime。

## Traceability

关键关系：

`report_id -> decision_id / experiment_id -> agent_run_id -> trace_id`

只存 refs，不在所有 artifact 复制所有字段。

## Crash / Side Effect

`started` 无 `completed/failed` => `UNKNOWN_AFTER_CRASH`。

对于 strategy activation / external write / future broker action，禁止自动 retry，先 reconcile。默认只从 `complete` snapshot resume。
