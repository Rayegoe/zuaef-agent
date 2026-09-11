# Harness Resource Policy

## 1. Quant production 推荐 capability policy

建议 quant-decision profile 请求：

```toml
[generalist]
enable_conversation_search = true
enable_context_controls = true
enable_tool_search = true
enable_web_search = true
enable_web_fetch = true
```

前提：

Host ceiling 对应能力也已开启。

---

## 2. 明确保持关闭

Quant production 暂不启用：

```toml
enable_memory = false
enable_subagents = false
enable_shell = false
enable_repo_context = false
```

除非已有业务需求证明必要。

---

## 3. Context Controls

复用 Core 当前：

```text
ClearToolResults
ClampOversizedMessages
WarnNearLimits
```

不要在 Quant plugin 复制 compaction。

### 目标

- 旧 tool results 退出 prompt；
- StepPersistence 继续保留审计事实；
- 大输出由 ToolOutputLimits spill；
- context 临近模型窗口时提前收敛。

---

## 4. Conversation Search

正常 follow-up：

```text
最近 N 个 semantic turns
+
ConversationSearch
```

### Semantic turns

只保留：

```text
user text
assistant terminal business answer
```

默认不带：

```text
old tool calls
old tool results
old model request trajectory
```

ConversationSearch 用于需要旧研究时按需恢复。

---

## 5. StepPersistence

继续负责：

```text
execution truth
pause/resume
run reconstruction
inspect
```

不得把 StepPersistence 当“全部历史自动进入 prompt”的理由。

---

## 6. ToolOutputLimits

市场情报、文件、网页结果必须继续受：

```text
ToolOutputLimits
```

约束。

大网页/公告正文：

```text
spill
→ selective read
```

而不是完整注入 prompt。

---

## 7. Cache observability

若当前 Harness/provider usage 可获得 prompt cache / cache-bust 观测，则优先接入 Console。

不要自建 Cache Efficiency DB。

Console 至少能观察：

```text
largest input
context pressure
compaction count if available
cache hit/miss if upstream exposes
```
