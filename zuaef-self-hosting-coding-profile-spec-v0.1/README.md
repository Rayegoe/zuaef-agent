# ZUAEF Self-Hosting Coding Profile v0.1 — Spec Pack

Status: implementation-ready  
Target repository: `Rayegoe/zuaef-agent`  
Baseline reviewed: GitHub `main`, 2026-09-08  
Primary outcome: make ZUAEF itself a production coding agent reachable from Feishu, using PydanticAI / PydanticAI Harness primitives directly.

## One-sentence product definition

From Feishu, the operator can switch to a privileged `coding` profile, give a coding objective or attach/reference a Spec Pack, and the existing ZUAEF Agent can inspect, modify, test, and extend its own repository through Harness-native file/shell/code capabilities, without introducing a second ZUAEF worker runtime.

## Architectural correction frozen by this pack

This pack explicitly rejects the earlier design:

```text
Feishu -> ZUAEF -> WorkerRunRequest -> WorkerBackend -> Codex/Pi
```

The production architecture is:

```text
Feishu
  -> existing Gateway
  -> existing profile composition
  -> coding profile
  -> PydanticAI / Harness capabilities
       - workspace FileSystem
       - repo-scoped FileSystem
       - repo-scoped Shell
       - RepoContext
       - Planning / Skills / StepPersistence / ToolOutputLimits
       - CodeMode when admitted
  -> modify repo / add plugin / add skill / add profile / run tests
  -> existing receipt + terminal delivery
```

`codex` and `pi` are optional shell-accessible external coding tools. They are not backends, not required for the loop, and not execution authorities above the ZUAEF Agent.

## Required end state

The following must be true in production, not only in tests:

1. `profiles/coding.toml` exists and resolves through the current composition layer.
2. The profile can operate on the real ZUAEF Git worktree while the normal workspace remains available.
3. The model can read/edit repo files and run bounded engineering commands using upstream Harness primitives.
4. The model can create or modify ZUAEF `plugin`, `profile`, `skill`, `toolset`, tests and docs directly.
5. It can validate the result with the real repository toolchain.
6. Feishu can select the coding profile through existing routing.
7. Feishu file messages can be normalized into the already-existing `InboundEnvelope.attachments` seam.
8. A Feishu-attached Spec Pack can be downloaded into the workspace and used as task input.
9. Existing Quant, Knowledge Worker, WordPress and other profiles remain unchanged.
10. No new worker framework, event bus, state machine, execution ledger, backend registry or orchestration runtime is added.

## Pack contents

- `00_SOURCE_OF_TRUTH.md` — frozen product and architecture decisions
- `01_PRD.md` — product requirements
- `02_ARCHITECTURE.md` — target architecture and boundaries
- `03_PROFILE_AND_PLUGIN_SPEC.md` — exact coding-profile composition
- `04_SELF_HOSTING_FLOW.md` — how ZUAEF changes itself
- `05_FEISHU_SPEC_INGEST.md` — Feishu file/spec ingestion
- `06_CODEX_PI_ROLE.md` — optional Codex/Pi role
- `07_SECURITY_APPROVAL_DEPLOYMENT.md` — trust and activation boundaries
- `08_IMPLEMENTATION_TASKS.md` — implementation sequence
- `09_ACCEPTANCE_GATES.md` — production acceptance
- `10_FILES_AND_PATCH_MAP.md` — expected repository changes
- `11_UPSTREAM_REFERENCES.md` — current upstream technical references
- `12_MASTER_PROMPT.md` — paste directly into Codex to execute the pack

## Outcome-first rule

Do not expand scope merely because Harness exposes more capabilities. The coding profile exists to produce working repository changes from a Feishu request. Add only what is necessary for that end-to-end outcome.
