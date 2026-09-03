# P0 — Data & Execution Truth

**Business question:** 我们今天和历史里比较的是不是同一个事实？

## P0.1 Volume Semantic Proof

实时 Tencent field 6 已 `手 -> checksumres`。必须证明 historical cached volume canonical unit 同样是 checksumres。

新增最小 validator：`tools/quant_validate_semantics.py`。

至少抽 20 个候选保存并可重算：live raw volume、normalization、historical recent volumes、20d avg、volume ratio。

若确定性单位错位：

- `BROKEN_DATA`；
- live trigger fail closed；
- 停止策略优化。

## P0.2 Semantic Quality ≠ Coverage

Data quality 分开：coverage / freshness / semantic integrity / source degradation / PIT。

`coverage=100%` 不等于 overall green。

## P0.3 PIT

历史研究必须明确：

- index membership as-of；
- financial report period；
- announcement/effective date；
- historical valuation as-of；
- adjustment semantics。

状态：`PIT_CLEAN / PIT_PARTIAL / PIT_CONTAMINATED`。

没有 announcement date 不能把 report period 当可用日。

## P0.4 Automated Anti-Leakage

新增 `tools/quant_anti_leakage_check.py`。

借鉴 Freqtrade lookahead-analysis 的**行为验证**：

- full-history replay；
- truncated/date-sliced replay；
- 比较同一历史日期的 factor / candidate membership / entry intent / exit intent。

删除未来数据后，过去结果不应变化。变化 => `LOOKAHEAD_FAIL`。

## P0.5 Independent Execution Truth

保留 Qlib 与 `quant_core` 双引擎。

Qlib = research efficiency。

`quant_core` = T+1、涨跌停、停牌、整手、佣金、最低佣金、印花税、滑点、next-open 等现实执行真相。

不以 Qlib NAV 替代执行证明。
