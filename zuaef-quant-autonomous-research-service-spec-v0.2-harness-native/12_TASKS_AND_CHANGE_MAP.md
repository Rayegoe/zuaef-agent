# Change Map & Tasks

## REUSE

```text
Harness:
FileSystem
Skills
Planning
StepPersistence
ToolOutputLimits
ConversationSearch
Context Controls
ToolSearch
WebSearch
WebFetch
CodeMode

Quant:
fetch_history
read_cache
history cache validation
get_symbol_context
watchlist
get_trading_context
get_live_signals
market rules
positions
```

---

## EXTEND

```text
profiles/quant-decision.toml
tools/quant_core.py
tools/quant_trading_monitor.py
plugins/zuaef-quant/zuaef_quant/toolset.py
plugins/zuaef-quant/zuaef_quant/plugin.py
plugins/zuaef-quant/skills/
gateway continuity path
gateway renderer
Console projection
tests
```

---

## MISSING

```text
history hydration seam
bounded structured market-intelligence tool
quant research skill
research packet
normal semantic carryover path
```

---

# Tasks

## T000 — Baseline & incident reconstruction — P0

- inspect current main；
- inspect OPi5 tree；
- `/inspect` failed 600550 run；
- identify exact unresolved tool；
- existing tests pass；
- record REUSE/EXTEND/MISSING。

---

## T001 — Enable Harness resource policy for Quant — P0

Quant profile requests:

```text
conversation_search
context_controls
tool_search
web_search
web_fetch
```

Host ceiling must be explicit.

Do not enable:

```text
memory
subagents
shell
repo_context
```

---

## T002 — Semantic continuity — P0

Change normal follow-up:

```text
bounded semantic recent turns
```

not full prior execution trajectory.

Preserve pause/resume exact history.

ConversationSearch becomes on-demand historical retrieval.

---

## T003 — History hydration seam — P0

Implement thin `ensure_history()` over existing `fetch_history()`.

---

## T004 — Auto-hydrate symbol context — P0

`cmd_symbol_context` uses `ensure_history`.

---

## T005 — Watchlist prewarm — P0

Add watchlist:

```text
persist
read-back
best-effort hydrate
```

---

## T006 — Quant research Skill — P1

Move research methodology from giant plugin instructions into Harness Skill.

Keep critical truth invariants in capability instructions.

---

## T007 — ToolSearch/deferred cleanup — P1

Identify low-frequency tools/capabilities and defer them.

Chinese discovery tests required.

---

## T008 — Structured market intelligence — P1

One bounded Quant tool for structured finance evidence.

Do not duplicate WebSearch/WebFetch.

---

## T009 — Harness web research integration — P1

Ensure full-analysis skill can use WebSearch/WebFetch when open-ended public research is materially useful.

Web evidence must preserve sources/times.

---

## T010 — CodeMode research recipes — P1

Add tested examples:

```text
forward distribution
similar-history
relative strength
volatility
```

No new sandbox.

---

## T011 — Research Packet — P1

Persist bounded business artifact.

---

## T012 — Customer evidence intake — P1

Case-bound → Case.
Unbound → scoped Quant research evidence.

---

## T013 — Runtime failure recovery — P1

Fix actual unresolved-tool root cause.

Read-only retry only if justified.

---

## T014 — Customer failure UX — P1

Hide operational dump from normal customer surface.

---

## T015 — Console Harness observability — P2

Expose available:

```text
context pressure
compaction
tool search activation
conversation search use
cache observability
```

No new telemetry platform.

---

## T016 — OPi5 real proof — P0 Exit

Real Feishu:

```text
为 600550 做个全面分析和趋势预测
```

with no prior history cache.

Must prove full service closure.
