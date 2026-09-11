# Source of Truth

## 当前代码基线

Repo:

```text
Rayegoe/zuaef-agent
```

当前 ZUAEF Core 已经直接组合 Harness/PydanticAI primitives：

```text
FileSystem
Planning
Skills
StepPersistence
ToolOutputLimits
ToolSearch
ConversationSearch
Context Controls
WebSearch
WebFetch
Memory
SubAgents
RepoContext
Shell
```

其中 generalist capabilities 由 host ceiling 与 profile policy 共同决定是否授权。

当前 Core 已经实现：

```text
enable_tool_search
enable_conversation_search
enable_context_controls
enable_web_search
enable_web_fetch
```

因此本专项不得新增另一套 Resource Governor Framework。

---

## 当前 Quant 已有能力

### get_symbol_context

任意 6 位 A 股：

```text
quote
membership
market rules
price limit
history sufficiency
S3 distances
MA5
```

### Analysis Watchlist

按 `analysis_scope` 隔离。

### CodeMode

当前 production quant profile 已：

```toml
code_mode = true
```

Sandbox：

```text
read-only /quant-cache
```

### fetch_history

`tools/quant_core.py` 已有：

```text
cache validation
live AKShare/Tencent fetch
bounded retry
normalization
metadata
write_cache
```

---

## 冲突优先级

```text
OPi5 running facts
>
current GitHub main
>
this spec
>
old docs
```

Codex 开工前必须 baseline 当前 main 和 OPi5。
