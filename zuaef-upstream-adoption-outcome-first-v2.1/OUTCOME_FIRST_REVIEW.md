# OUTCOME-FIRST REVIEW — v2.1 Correction

## What v2.0 got wrong

v2.0 over-applied the rule:

> only repeated real failure justifies new architecture

to **upstream-provided baseline capabilities**.

That rule should prevent ZUAEF from inventing new abstractions.

It should NOT prevent a generalist platform from integrating the standard primitives it is expected to have.

For a Pi/Codex-like FDE core, the following distinction is essential:

```text
building a custom subsystem
≠
making an upstream capability available
```

Integrating released Harness Memory is not the same as designing a ZUAEF memory architecture.

Integrating SubAgents is not the same as changing the default topology to multi-agent.

Integrating ToolSearch is not the same as building an intent router.

Integrating compaction is not the same as creating a summarization service.

---

# Correct Outcome-First interpretation

## Platform plane

The platform should be broadly capable:

```text
FileSystem
Shell
RepoContext
Web
Planning
Skills
ToolSearch
Context management
Persistence
Memory
ConversationSearch
SubAgents
```

The cost of adding these should be low because they come from upstream.

## Active-context plane

Each task should remain narrow:

```text
load only relevant capabilities
invoke only relevant tools
keep irrelevant domains dormant
```

## Business plane

ZUAEF engineering effort should go into:

```text
Case
customer understanding
decision policy
writing
budget
WordPress
business evidence
verification
receipts
channels
```

and not into recreating the platform primitives.

---

# Positive feedback loop

The correct learning loop is:

```text
Upstream primitive integrates cleanly
→ READY
→ keep it available

Task does not need it
→ DORMANT
→ good, no unnecessary context/action

Task needs it
→ LOAD
→ model gets relevant capability

Capability improves outcome
→ INVOKE
→ keep the policy

Local duplicate is now unnecessary
→ DELETE

Business-specific component remains valuable
→ KEEP

Baseline + real outcome pass
→ STOP generic infrastructure work
```

This produces the desired asymmetry:

```text
platform capability breadth ↑
active context width ↓
ZUAEF generic infrastructure ↓
business capability depth ↑
```

That is the target.
