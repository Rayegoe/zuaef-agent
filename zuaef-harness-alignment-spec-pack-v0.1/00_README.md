# ZUAEF × PydanticAI Harness Alignment Spec Pack v0.1

Date: 2026-09-05
Target repository: `Rayegoe/zuaef-agent`
Purpose: reconcile the two architecture reports and turn the result into an executable, evidence-gated Harness follow strategy.

## Decision

ZUAEF should **continue following PydanticAI/PydanticAI Harness as its generic agent substrate**. It should not build a competing Harness.

The current architecture is already substantially aligned:

- PydanticAI owns the typed agent loop, native approvals, deferred tool results, usage limits and core capabilities.
- PydanticAI Harness owns generic reusable capabilities such as FileSystem, Planning, Skills, StepPersistence, ToolOutputLimits, Memory, ConversationSearch, RepoContext, Shell, SubAgents and CodeMode.
- ZUAEF owns business state, policy, domain actions, composition identity, operational settlement/evidence indexing and interaction surfaces.
- Plugins package Toolsets, Skills and explicitly allowed Capabilities; they do not create a second runtime.

## The important reconciliation

The two reports were both materially correct, but they answered different questions:

1. **Current production baseline**
   - `zuaef-agent` declares `pydantic-ai>=2.35.3,<3`.
   - It declares `pydantic-ai-harness[skills,code-mode]>=0.27,<0.28`.
   - Therefore production intentionally follows the Harness 0.27 minor line.

2. **Current upstream state**
   - Harness v0.28.0 was released 2026-08-31.
   - Harness v0.29.0 was released 2026-09-04.
   - Current upstream `pyproject.toml` requires `pydantic-ai-slim>=2.38.0`.

So the correct sentence is:

> ZUAEF is architecturally aligned with current Harness, while production is intentionally pinned two minor lines behind the newest upstream release pending compatibility evidence.

## Scope of this pack

This pack does **not** authorize a production upgrade by itself. It creates a controlled compatibility lane and acceptance gates.

It is subordinate to:

- repository `AGENTS.md`;
- `.agents/skills/zuaef-runtime-coach/SKILL.md`;
- `docs/runtime-refoundation/*`;
- the current runtime-refoundation task order.

Any production runtime change must still satisfy the repository's reproduce → measure → smallest change → compare → delete-obsolete-authority discipline.

## Files

- `01_RECONCILED_AUDIT.md` — report-vs-report reconciliation and corrections.
- `02_ARCHITECTURE_BOUNDARY.md` — the architecture that should remain stable.
- `03_SPEC.md` — requirements and non-goals.
- `04_TASKS.md` — executable work sequence.
- `05_ACCEPTANCE.md` — promotion gates for a Harness minor upgrade.
- `06_VERSION_AND_CAPABILITY_POLICY.md` — version and capability admission policy.
- `07_PATCH_TARGETS.md` — likely code/test touchpoints and what must not be rewritten.
- `08_CODEX_MASTER_PROMPT.md` — ready-to-use Codex execution prompt.

## Success condition

The pack succeeds when ZUAEF can evaluate a newer Harness minor with bounded work, prove compatibility at observable behavior boundaries, and either:

- promote the newer minor with no architecture expansion; or
- remain on the current minor with a precise, reproduced incompatibility record.

A failed upgrade is an acceptable result. Building a second Harness to force an upgrade is not.
