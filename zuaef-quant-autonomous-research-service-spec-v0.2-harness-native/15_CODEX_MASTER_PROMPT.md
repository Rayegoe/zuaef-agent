# Codex Master Prompt — v0.2 Harness-Native

You are implementing `ZUAEF Quant Autonomous Research Service v0.2`.

The core architectural rule is:

> Harness owns agent infrastructure. Quant owns market/business evidence. The LLM owns interpretation.

Do not create a new ZUAEF agent framework.

## Primary outcome

A Feishu user can ask:

```text
为 600550 做个全面分析和趋势预测
```

even when 600550 has never been cached before.

The running Agent should autonomously:

```text
obtain current symbol evidence
auto-hydrate missing history
retrieve prior research only if needed
use structured market evidence
use Harness WebSearch/WebFetch for open public research when useful
use existing Harness CodeMode for temporary statistics
synthesize Bull/Base/Bear scenarios
provide a conditional recommendation
persist a Research Packet
```

without a developer writing stock-specific code.

---

# Mandatory architectural decisions

## 1. Use current Harness primitives

Use existing:

```text
ConversationSearch
Context Controls
ToolSearch
Skills
StepPersistence
ToolOutputLimits
WebSearch
WebFetch
CodeMode
```

where applicable.

Do not reimplement their function in Quant.

## 2. Quant profile

Request:

```text
enable_conversation_search
enable_context_controls
enable_tool_search
enable_web_search
enable_web_fetch
```

through the repository's existing host-ceiling ∩ profile-request policy.

Do not globally widen host authorization without explicit deployment config.

## 3. Keep disabled

Do not enable by default:

```text
Memory
SubAgents
Shell
RepoContext
DynamicWorkflow
```

unless the current repository already has an evidence-backed reason.

## 4. Conversation continuity

Normal follow-up must not blindly fork the full previous execution trajectory.

Implement:

```text
bounded recent semantic turns
+
ConversationSearch when needed
```

Preserve exact StepPersistence history for pause/resume.

## 5. History data

Reuse:

```text
tools/quant_core.py::fetch_history
```

Add only a thin `ensure_history` orchestration seam.

`get_symbol_context` must auto-hydrate on cache miss.

## 6. Tool disclosure

Use current ToolSearch/deferred capability mechanics.

Do not implement:

```text
ToolGovernor
ToolRouterV2
request_tool_scope
DOMAIN/RETRIEVAL state machine
```

## 7. Research methodology

Put detailed full-analysis methodology in a Quant Harness Skill.

Keep only hard evidence invariants in plugin instructions.

## 8. Market intelligence

Build one bounded structured-finance evidence adapter if needed.

Use Harness WebSearch/WebFetch for open-ended research.

Do not turn the Quant tool into a general web crawler.

## 9. CodeMode

Reuse current read-only Quant CodeMode.

Never make the sandbox writable to solve cache misses.

Hydrate before sandbox use.

## 10. Research memory

Persist a bounded Research Packet as a Quant business artifact.

Do not use generic Harness Memory for current market truth.

## 11. Customer intelligence

Customer-reported claims may be stored as evidence with provenance and verification state.

They may influence research attention/hypotheses.

They may not directly modify:

```text
candidate
READY/NEAR
strategy
fills
```

## 12. Runtime

Before adding retry behavior, inspect the real failed 600550 Run and identify the exact unresolved tool call.

Only retry safe idempotent reads when evidence supports it.

## 13. Surface UX

Normal Feishu customer output should be business-first.

Operational details stay in:

```text
/inspect
/status
Console
```

---

# Do not

Do not:

- increase request limits as the main fix;
- add Redis/Kafka/Celery;
- add a research database;
- add multi-agent orchestration;
- create per-stock scripts;
- redesign frozen S3;
- change candidate semantics;
- auto-trade;
- use conversation memory as current market evidence;
- duplicate Harness primitives in Quant;
- add fixed hard quotas for search/read/planning categories;
- require approval for normal read-only research.

---

# Implementation order

1. Baseline and incident reconstruction.
2. Enable Harness resource policy for quant profile.
3. Separate semantic follow-up from execution continuation.
4. Add history hydration seam.
5. Auto-hydrate symbol context.
6. Prewarm watchlist additions.
7. Move research methodology to Harness Skill.
8. Apply ToolSearch/deferred loading.
9. Add structured market intelligence.
10. Integrate Harness WebSearch/WebFetch.
11. Reuse CodeMode for research stats.
12. Persist Research Packet.
13. Add customer evidence intake.
14. Fix actual unresolved-tool root cause.
15. Improve customer failure UX.
16. Prove on OPi5.

---

# Definition of Done

The project is complete only after a real OPi5 Feishu proof demonstrates:

```text
new symbol
no preexisting history cache
→ full analysis request
→ history auto-hydration
→ bounded tool/context behavior
→ open web research when useful
→ CodeMode statistics when useful
→ Bull/Base/Bear scenarios
→ conditional recommendation
→ research persistence
→ follow-up retrieves prior research without replaying full old tool history
→ /inspect clean
→ monitor/dashboard unaffected
```

Return a final implementation report:

```text
Reused Harness capabilities
Reused Quant capabilities
Changed files
Real runtime evidence
Remaining limitations
Operator verification commands/messages
```
