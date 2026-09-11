# Architecture Decisions

## ADR-01 — Harness owns agent infrastructure

不得在 Quant plugin 内重新实现：

```text
context manager
conversation search
tool search platform
message history database
sandbox runtime
workflow engine
sub-agent scheduler
generic memory engine
```

这些优先复用 PydanticAI / Harness primitives。

---

## ADR-02 — Quant owns business evidence

Quant plugin / side-env 可以并且应该拥有：

```text
history fetch
quote fetch
market rules
strategy distances
candidate membership
watchlist
positions
trade ledger
structured financial evidence
research packet business semantics
```

因为这些属于业务事实，不属于 Agent infrastructure。

---

## ADR-03 — Normal continuity != execution continuation

### Pause / resume

使用完整 StepPersistence execution history。

原因：

```text
pending tool call
approval frontier
tool_call_id
exact model/tool messages
```

必须保真。

### Normal chat follow-up

使用：

```text
recent semantic messages
+
Harness ConversationSearch
```

旧 tool call/result 不默认回灌 prompt。

---

## ADR-04 — Structured finance research != open web research

### Quant-owned

```text
公告结构化接口
公司财务
历史行情
行业结构化数据
exchange/market rules
```

### Harness-owned

```text
WebSearch
WebFetch
开放网页研究
跨来源 discovery
```

不得把所有开放研究能力塞进 `get_market_intelligence()`。

---

## ADR-05 — No fixed workflow

“全面分析”不是硬编码：

```text
step1 → step2 → step3
```

而是一个 Harness Skill + stable evidence capabilities。

Agent 根据问题决定是否需要：

```text
symbol context
market intelligence
web research
CodeMode
portfolio context
research memory
```

---

## ADR-06 — No fixed per-category tool quotas

不得平台级硬编码：

```text
search <= 2
read <= 8
plan <= 1
```

只保留：

```text
request_limit
tool_calls_limit
token limits
effect permissions
sandbox boundaries
```

以及 Harness 的 context pressure / compaction。

---

## ADR-07 — Generic Memory 暂不承载 market truth

不启用 Generic Memory 保存：

```text
current quote
latest news
position state
candidate state
strategy trigger
```

这些全部有明确 authoritative sources。

Memory 未来可用于：

```text
user preference
reporting preference
research style
non-market stable preferences
```

---

## ADR-08 — Single Agent by default

Quant production 暂不启用：

```text
SubAgents
DynamicWorkflow
Advisor swarm
```

除非真实 production evidence 证明单 Agent 无法完成并行/隔离工作。

---

## ADR-09 — Research result is a business artifact

Research Packet 是业务研究结果，不是 execution state。

建议：

```text
workspace/artifacts/quant/research/<scope>/<symbol>/
```

不新增数据库。
