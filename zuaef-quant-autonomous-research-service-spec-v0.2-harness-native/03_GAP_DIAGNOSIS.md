# Gap Diagnosis

## G01 — Data capability exists but orchestration missing

当前：

```text
symbol-context
→ quote fetch
→ read_cache(history)
→ miss = 0 bars
```

但已有：

```text
fetch_history()
```

因此不是“系统不能补历史”，而是 Agent-facing path 未接。

---

## G02 — Normal chat replays too much execution history

当前 Gateway normal follow-up 仍可能：

```text
prior_run_history
→ fork_run
→ full previous messages
```

这会把旧 tool calls/results 重带入 prompt。

---

## G03 — Harness context controls exist but Quant production 未正式利用

已有：

```text
ClearToolResults
ClampOversizedMessages
WarnNearLimits
```

需要进入 Quant production effective policy。

---

## G04 — Harness ConversationSearch exists but未成为正常 continuity 主路径

正常 long-running chat 需要：

```text
bounded recent turns
+
ConversationSearch
```

---

## G05 — ToolSearch exists but Quant research能力增加后可能 tool surface 膨胀

当前少量 tools 尚可；
加入 intelligence / case / research 后应采用 progressive disclosure。

---

## G06 — “全面分析”没有 Research Skill contract

需要 Harness Skills 承载 domain methodology，而不是 Core workflow。

---

## G07 — 开放式市场研究能力不足

不能只靠 AKShare 结构化新闻接口解决所有“为什么”。

需要 Harness WebSearch/WebFetch，但应按 deployment policy 授权。

---

## G08 — Research memory 尚未标准化

需要 durable Research Packet，但不应该使用 generic Memory 保存 current market truth。

---

## G09 — Runtime FAILED UX 泄露 operational internals

正常客户 Surface 不需要 token/tool/runtime dump。

---

## G10 — unresolved tool accident 尚需真实定位

真实 600550 Run：

```text
FAILED
Requests 2
Tool calls 1
unresolved tool call(s)
```

必须先 `/inspect` 定根因。
