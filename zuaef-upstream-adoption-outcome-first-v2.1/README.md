# ZUAEF Upstream Adoption — Outcome-First v2.1

Target: `Rayegoe/zuaef-agent`

Upstreams:

- `pydantic/pydantic-ai`
- `pydantic/pydantic-ai-harness`

## Core correction from v2.0

v2.0 incorrectly treated several generalist capabilities as “only integrate after a failure proves the need”.

That is too conservative for a platform FDE.

The correct rule is:

> **Capability Surface complete; Active Context minimal.**

ZUAEF should have the standard generalist execution capabilities **installed, composable, testable, and available**.

Outcome-First governs whether a capability is:

- enabled for this deployment,
- loaded into the current context,
- selected by the model,
- actually invoked,

not whether the platform bothered to integrate the capability at all.

## Five-stage capability lifecycle

```text
1. AVAILABLE
   capability exists in the platform/runtime

2. AUTHORIZED
   deployment/user policy allows it

3. DISCOVERABLE
   model can see a compact description/catalog entry

4. LOADED
   full instructions/tools enter active context when useful

5. INVOKED
   model actually calls the tool/capability for this task
```

The platform should aim for:

```text
AVAILABLE set = broad
AUTHORIZED set = deployment-specific
DISCOVERABLE set = broad but compact
LOADED set = small
INVOKED set = smaller
```

This is how ZUAEF can be a generalist FDE without turning every turn into a huge prompt/tool dump.

## Baseline generalist capability surface

Where released upstream APIs permit, the platform baseline should include:

```text
FileSystem
Shell
RepoContext
Planning
Skills
ToolOutputLimits
StepPersistence
WebSearch
WebFetch
ToolSearch / on-demand capability discovery
Context compaction / context controls
Memory
ConversationSearch
SubAgents
```

These are platform primitives.

Their default activation policy is separate.

## Positive signals

These are all GOOD results:

- **READY** — capability is integrated and testable but dormant.
- **DORMANT** — capability was correctly not loaded/called for a task.
- **LOAD** — capability was loaded because the task justified it.
- **INVOKE** — capability was actually used because it improved the outcome.
- **KEEP** — existing thin ZUAEF business code remains because it owns real business semantics.
- **DELETE** — duplicated generic infrastructure is removed in favor of upstream.
- **REUSE** — upstream public primitives are adopted directly.
- **STOP** — once the platform baseline and real FDE outcome pass, stop adding harness abstractions.

A capability not being invoked is not evidence that it should not exist.
