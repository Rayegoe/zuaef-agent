# ZUAEF Architecture Subtraction & Evidence Reset — Spec Pack v1.0

**Repository:** `Rayegoe/zuaef-agent`
**Baseline:** `main@14e0df06012c4b925012d3ee9be0734af0282a7d`
**Date:** 2026-08-20

## Executive decision

This package is a **subtraction refactor**, not a new platform initiative.

The current repository has already found the correct macro-shape:

```text
PydanticAI / pydantic-ai-harness
        ↓
thin ZUAEF runtime
        ↓
PluginBundle + Profile + CompositionSnapshot
        ↓
business plugins / gateway / real work
```

The next step is **not** to add a Context Plane, Evidence Plane, Quality Plane, Binding Framework, Service Registry, Event Bus, or another runtime.

The next step is to remove accidental abstractions and reset the meaning of “evidence” and “verification”.

### Core correction

The current code conflates three very different things:

1. **Execution integrity**
   - a file exists;
   - bytes changed;
   - SHA-256 can be calculated;
   - a tool call started/completed/failed;
   - a pause can be resumed from the same composition.

2. **Epistemic evidence**
   - a factual claim is supported by an inspectable source;
   - the source has a real URL / stable resource location;
   - a reader can follow that source and judge whether it supports the claim.

3. **Quality judgment**
   - the result is useful, correct, well-written, persuasive, appropriate, or preferred;
   - a human or LLM reviewer can explain why;
   - repeated reviewed cases improve future behavior.

Only **(1)** belongs in the generic runtime.

The current `verification.py` and `RunReceipt` use names such as `verified_artifacts`, `verified_knowledge`, `verified_tool_effects`, `evidence`, `degraded`, and `partial` in ways that make execution bookkeeping look like semantic validation. That must stop.

A changed file hash does **not** prove the artifact is correct.
A `tool_call_completed` event does **not** prove the business outcome is good.
A frontmatter field saying `sources:` does **not** prove a claim is supported.
A hard-coded sensor/action/weight tuple does **not** encode editorial truth.

## New authority model

```text
RUNTIME PLANE
records operational facts only
(run, usage, errors, pause/resume, tool events, artifact byte facts)
            │
            ├───────────────────────────────────┐
            │                                   │
            ▼                                   ▼
RESULT ARTIFACT                          QUALITY / LEARNING LOOP
human-readable result                   offline, review-driven
with inspectable source URLs            LLM critique + human annotation
            │                                   │
            ▼                                   ▼
reader can inspect sources              accepted revisions / guidelines
                                                │
                                                ▼
                                      Skill / examples / plugin assets
```

## What remains protected

This cleanup must **not** delete real safety or durability invariants:

- native PydanticAI approval for external/destructive effects;
- path containment and secret boundaries;
- pause/resume continuity;
- exact `CompositionSnapshot` reconstruction;
- usage limits;
- StepPersistence;
- tool execution event history;
- artifact byte hashes when useful for identity/integrity;
- plugin version/entry-point matching.

These are operational invariants. They must simply stop pretending to be semantic “verification”.

## Package contents

- `PRD.md` — product problem, goals, scope, non-goals.
- `SPEC.md` — normative target architecture and code contracts.
- `QUALITY_LOOP.md` — source-linked result evidence and LLM/human iteration loop.
- `MIGRATION.md` — current → target mapping by file and schema.
- `PLAN.md` — implementation sequence and stop rules.
- `TASKS.md` — coding-agent executable tasks.
- `ACCEPTANCE.md` — acceptance gates based on real behavior, not decorative fields.
- `DECISIONS.md` — architecture decisions and forbidden abstractions.
- `CODING_AGENT_PROMPT.md` — prompt to hand directly to a coding agent.

## Repository facts motivating this package

At the baseline commit:

- `PluginBundle` is already deliberately thin: toolsets, skill dirs, capabilities.
- `composition.py` already uses the standard Python `zuaef.plugins` entry-point mechanism and freezes exact composition for resume.
- multiple real business plugins already exist.
- `verification.py` parses hard-coded `artifact:`, `knowledge:`, and `tool-effect:` evidence references.
- `runtime.py` can downgrade a run because those bookkeeping checks “degraded”.
- `KnowledgeStore` has hard-coded semantic knowledge types and source requirements.
- `CoreDeps` still contains `case_id`, so a business concept leaks into the core.
- Gateway still invokes Case-specific host context projection.
- Editorial Learning `human_patches.jsonl` encodes human judgment into fields such as `trigger_signals`, `action`, `directive`, `weight`, and `approved_by`.
- curated learning sources already contain the much more valuable primitive: **real source URLs**.

The refactor should preserve the good architecture and delete the false authority.

## One-line target

> **A frozen, small runtime records what happened; useful artifacts show what they are based on; quality improves through reviewed examples, not schema cosplay.**

## v1.1 correction — Capability owns the result shape

This spec pack explicitly rejects a second mistake: deleting fake evidence fields must not collapse every business output into one generic result format.

The intended model is:

```text
Kernel = how work runs
Capability = what a good result in this domain looks like
Artifact = the actual result
```

Writing, research, budget, negotiation, and WordPress may all have different result structures. Those structures live in Capability/plugin instructions and tools, not in `RunSummary`, receipt fields, or `PluginBundle.result_schema`.


## v1.2 correction — Pydantic is a data contract, not a workflow gate

The target architecture does not replace old evidence fields with new phase/status fields.

```text
Pydantic:
  describes objects

Capability:
  shapes domain behavior and deliverables

Agent loop:
  decides how work proceeds

Native approval:
  guards real external/destructive effects
```

Do not encode reasoning progression as Pydantic state.
