# Final Freeze

This is the current final project strategy and architecture boundary.

## What Is Frozen

The stable product loop is:

```text
SELECT
  real market -> active watch universe

MONITOR
  active universe -> seconds/minutes state updates

DECIDE
  material opportunity -> NO_ACTION/WATCH/READY/INVALIDATED

MANAGE
  user-confirmed position -> HOLD/REDUCE/EXIT

OBSERVE
  forward market path -> realized/paper outcome

LEARN
  outcome + controls -> lesson -> research -> strategy retained/changed/retired
```

P0–P6 are the assurance and learning spine beneath this loop. They are not a replacement for it.

## Strategy Is Not Frozen Forever

S3 is the current hypothesis. It may fail.

Do not protect S3 because engineering was built around it. Preserve the live trading loop and replace/simplify the policy when evidence requires it.

## Architecture Freeze Rule

Do not write a new top-level architecture because a new framework or idea appears.

Reopen architecture only when real evidence shows one of the following cannot be solved cleanly with the current design:

- real market selection failure;
- intraday monitoring/latency/reliability failure;
- position-management failure;
- semantic/temporal/data truth failure;
- inability to replay a material decision sufficiently to learn;
- Agent cannot perform a real high-value research action with existing capabilities;
- operational crash/effect ambiguity;
- forward evidence requires a new data modality;
- a validated new strategy mechanism truly needs a new capability.

Not valid reasons:

- another project has more Agents;
- a vector/graph database looks advanced;
- more schema would appear cleaner;
- more tools would look capable;
- more metrics would look professional;
- the current strategy return is unattractive;
- a new conceptual worldview has not yet been experimentally supported.

## Operating Default After Core Build

Default mode is not architecture development. It is:

`run -> monitor -> alert -> manage -> settle -> review -> learn`

Engineering re-enters only on observed failure or a validated strategy requirement.

## Final North Star

> 在有限资金和有限注意力下，让系统持续替用户扫描、盯盘、管理交易，并用真实市场结果不断提高下一次决策质量。

Supporting principle:

> 更少的无依据交易，更高质量的可解释决策，更可靠的策略证据，更快地从真实结果中学习。
