# Runtime & Chat UX

## 1. unresolved tool call

真实 600550 FAILED 必须优先通过 `/inspect` 定位。

先确认：

```text
tool name
call id
started/completed/failed
timeline
timeout/cancel
CodeMode relation
effect ledger
```

之后才能决定修法。

---

## 2. Retry

允许安全 retry 的前提：

```text
read-only
idempotent
known transient failure
```

例如：

```text
history fetch
quote fetch
web read
market intelligence read
```

禁止 blanket retry：

```text
record_trade_outcome
ack-buy
ack-sell
external send
customer delivery
```

---

## 3. Customer Surface

正常 successful completed：

```text
business output only
```

Research PARTIAL：

```text
业务结果 + 缺失层说明
```

Runtime FAILED：

只给 bounded message：

```text
本次研究没有完整结束，因此没有使用不完整证据给出预测。
系统已保留运行诊断，可直接重试。
```

不要默认展示：

```text
tokens
tool count
usage limits
unresolved effects
full run id
```

---

## 4. Operator Surface

完整 operational truth 继续放：

```text
/inspect
/status
Console
receipts
```

---

## 5. Model identity

模型/profile 可由 host metadata 或 `/status` 确定。

不要让 LLM猜自己的模型。

非本专项 blocker。

---

## 6. Context observability

Console 最少增加/复用：

```text
current input size
largest request input
compaction activity if available
conversation search usage if available
tool search activation if available
```

以 upstream exposure 为准。

不新增第二个 telemetry DB。
