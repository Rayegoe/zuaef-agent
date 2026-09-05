# Reconciled Architecture Audit

## 1. Executive finding

The two reports converge on the same core conclusion: **ZUAEF is already a thin business runtime built on PydanticAI/Harness primitives rather than a competing agent framework.**

The user's report is strongest on current-repository evidence and no-clone verification. The assistant report adds the missing upstream-version view and identifies compatibility seams that deserve explicit tests.

## 2. What the user's report got especially right

### 2.1 Direct primitive reuse

Current `src/zuaef_agent/core.py` directly composes upstream primitives including:

- Harness: FileSystem, Planning, Skills, StepPersistence/FileStepStore, ToolOutputLimits/LocalFileStore;
- optionally Harness: RepoContext, Memory, ConversationSearch, SubAgents, context-control capabilities, Shell;
- PydanticAI core: WebSearch, WebFetch, ToolSearch.

This is exactly the upstream "capabilities all the way down" model.

### 2.2 No cloned generic Harness

Repository `AGENTS.md` explicitly forbids cloning upstream filesystem, planning, skills, tool-output limiting, approval, usage-limit or durable-runtime implementations.

`plugin_api.py` reinforces the same boundary: a plugin may return Toolsets, Skill directories and explicitly allowed Capabilities, but has no event bus, agent registry, alternate approval system or alternate receipt runtime.

### 2.3 ZUAEF-specific mechanisms are mostly legitimate domain/control-plane additions

These are not evidence of a competing Harness:

- `Knowledge` + protected `knowledge/*` write path;
- CJK-aware ToolSearch strategy passed through the upstream extension point;
- `ReceiptStore` as operational index/settlement output rather than a second model loop;
- Gateway/Telegram as interaction/transport surfaces;
- plugin composition freeze and resume identity.

## 3. What the assistant report added

### 3.1 Separate production version from upstream latest

The repository production pin is still Harness 0.27.x. Upstream has moved through 0.28.x to 0.29.0.

This distinction matters because architectural alignment does not imply immediate version promotion.

### 3.2 New upstream changes are especially relevant to ZUAEF's durability boundary

Harness 0.28 added durability-related changes including durable summarization and replay-safe capability reads/model calls. Harness 0.29 raised the PydanticAI floor to 2.38.0 and continued composition/durability work.

This makes pause/resume, StepPersistence and context-compaction behavior the highest-value compatibility gates.

### 3.3 Private API tests are a maintenance risk

`tests/test_writing_codemode_skills.py` currently inspects `Skills._deferred_capabilities`.

That is a private Harness implementation detail. A minor upstream release can legitimately rename/remove it without changing public behavior. Tests should prefer observable behavior/catalog/tool-surface assertions.

## 4. Corrections and precision improvements

### 4.1 Do not say the current repository uses `fork_run` unless evidence appears

A repository search on current `main` found no `fork_run` reference. Current continuation evidence shows `continue_run(..., include_interrupted=True)`.

Therefore the alignment table should say:

> StepPersistence + FileStepStore + continue_run are in current production use; fork behavior is not claimed here.

### 4.2 Spend and UsageLimits are not equivalents

`UsageLimits` bounds one run by requests/tool calls/tokens.

Harness Spend addresses cross-window/currency-aware cost budgets and accounting.

The correct statement is:

> ZUAEF currently needs and uses run-local UsageLimits. Harness Spend is not admitted because no cross-window USD-budget failure/requirement has been established.

### 4.3 StepPersistence is not the same thing as full durable execution

Current ZUAEF has a real process-restart pause/resume seam because it explicitly persists an interrupted frontier and resumes it using Harness `continue_run`.

That is sufficient for the implemented approval continuation case when its invariants hold.

It does **not** mean ZUAEF has Temporal/DBOS-style general event-sourced durable execution, arbitrary activity replay or exactly-once external side-effect semantics.

The correct architecture language is:

> StepPersistence is the admitted lightweight persistence primitive for current continuation/debug needs. Full durable execution remains unadmitted until a reproduced requirement exceeds this seam.

### 4.4 Do not use "latest README = 0.27" language

0.27.x is the ZUAEF production minor line, not the latest upstream line as of 2026-09-05.

## 5. Combined alignment score

| Area | Assessment | Notes |
|---|---:|---|
| PydanticAI core alignment | 9/10 | native Agent, approvals, usage limits, deferred tools |
| Harness primitive reuse | 9/10 | broad direct capability reuse |
| Plugin/composition boundary | 9/10 | thin packaging, no second runtime |
| Runtime/continuation boundary | 8/10 | sound, but highest upstream-coupling seam |
| Public-API discipline | 8/10 | one known private-test dependency should be removed |
| Upstream-version freshness | 7/10 | intentional 0.27.x pin vs upstream 0.29.0 |
| Ability to track future Harness | 9/10 | architecture is composition-friendly |

## 6. Final merged conclusion

The next work is **not a Harness migration**.

It is a Harness-follow discipline:

1. keep generic capabilities upstream-owned;
2. keep business semantics/domain tools in ZUAEF plugins;
3. keep ZUAEF's runtime settlement/control-plane boundary thin;
4. test public observable behavior across Harness minors;
5. promote versions only after compatibility evidence;
6. admit new capabilities only after a reproduced task/deployment failure.
