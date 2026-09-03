# Acceptance Gates

## Business
- `NO_TRADE` 不算失败。
- 非专业用户 30 秒能看懂今天为什么不交易/观察。
- Candidate rank 永不等于 buy signal。

## Data
- 故意 100x volume mismatch => validator FAIL + live fail closed。
- future-data fixture => anti-leak FAIL。
- 财报在 announcement date 前不可用。

## Quant
- Composite score 可输出 5d/8d IC/RankIC/quantile evidence。
- 如果无增量价值，允许 demote/simplify candidate score。
- 所有 sibling trials 可追溯。
- 样本不足时 DSR/PBO 不输出伪精确值。
- Headline return 是 net。

## Agent
- 至少一次 non-preprogrammed research question。
- Agent 引用 Lesson/Forward evidence。
- hypothesis 可 falsify。
- Agent 能主动 REJECT 自己假设。
- Agent 不能改 evaluator/cost/split 后继续把结果叫可比。

## Provenance
- 同一天两次 run => 两个 report id / scan snapshot / observation。
- 第一份 immutable report 不改变。
- report 能解析到 agent_run/trace/commit。

## Harness Crash
- unresolved tool effect 可见。
- external side effect 不自动 retry。
- 默认只 resume complete snapshot。

## Anti-architecture
- 新持久 field 有 consumer；否则删除。
- 新 model-visible tool 有真实 action/effect rationale；否则拒绝。
- 无 mega schema / generic workflow / new DB。

## Forward honesty
- `forward_settled=0` 不显示 hit rate。
- PIT contaminated / anti-leak unknown 不宣称 proven profitability。

## Regression
保留现有 default/quant tests、ruff、fail-closed universe、financial sector-aware behavior、no broker。
