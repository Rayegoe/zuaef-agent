# 12 — Codex Master Prompt

You are implementing `ZUAEF Self-Hosting Coding Profile v0.1` in the current `Rayegoe/zuaef-agent` repository.

Treat this entire Spec Pack as the authorized task. Do not stop after analysis. Implement the production feature, run the real repository gates, and leave the worktree in a reviewable state.

## Outcome

Make the existing ZUAEF Agent itself a production coding agent reachable from Feishu.

The primary execution engine is the existing PydanticAI Agent plus released PydanticAI/PydanticAI Harness capabilities.

Do **not** introduce a new ZUAEF worker framework.

Codex/Pi, if supported, are optional Shell commands only.

## First actions

1. Read `AGENTS.md`.
2. Read all files in this Spec Pack.
3. Inspect the current live repository implementation, especially:
   - core composition;
   - profile/plugin composition;
   - Feishu adapter;
   - attachment model;
   - routing;
   - current pinned Harness package/API.
4. Confirm current branch/worktree and protect unrelated operator changes.
5. Reconcile any Spec example with the actual installed Harness minor. Prefer the installed public upstream API over guessed signatures.

Do not ask the operator to repeat information already present in the repository or this pack.

## Non-negotiable architecture

### Keep

- one ZUAEF Agent;
- existing runtime;
- existing receipts;
- existing StepPersistence;
- existing Gateway;
- existing profile routing;
- existing plugin composition;
- existing approval semantics.

### Add

- production `coding` profile;
- thin `zuaef-coding` composition plugin;
- repo-scoped upstream FileSystem under `PrefixTools`;
- repo-scoped upstream Shell under `PrefixTools`;
- upstream RepoContext;
- CodeMode if it composes correctly on the pinned Harness;
- concise coding Skill;
- Feishu file-resource normalization into existing `AttachmentRef`.

### Do not add

- WorkerRunRequest;
- WorkerBackend;
- CodexBackend;
- PiBackend;
- coding job queue;
- second runtime;
- second receipt store;
- new state machine;
- new event bus;
- new hash/checksum/manifest mechanism;
- Gateway coding business logic.

## Critical implementation insight

The current ZUAEF core already composes FileSystem, Planning, Skills, ToolOutputLimits and StepPersistence.

Do not add `Coder()` wholesale and duplicate them.

Use upstream Coder's building-block pattern.

The normal workspace and repository are two different roots. The coding plugin must expose repo-rooted tools without colliding with the normal workspace tools. Prefer PydanticAI `PrefixTools` / `.prefix_tools(...)`.

## Feishu

The generic attachment seam already exists.

Do not modify Runtime to understand Feishu files.

Extend `FeishuAdapter` to:
- inspect authorized normalized message resources;
- use the current `lark-channel-sdk` public resource download helper;
- save under workspace-confined Feishu inbox;
- build `AttachmentRef`;
- permit file-only messages;
- honor the existing max-upload limit.

The adapter must not parse Spec semantics or extract archives.

## Coding behavior

The coding profile must be able to modify this repository with its own Harness abilities.

It may add or change:
- Skills;
- Toolsets;
- Plugins;
- Profiles;
- tests/docs;
- Core only when the repo's kernel admission rules genuinely require it.

Codex and Pi:
- optional;
- enabled only by coding plugin config;
- invoked through Shell;
- never mandatory;
- never the authority for whether the task is complete.

## Deployment boundary

Do not add `systemctl` to autonomous Shell merely to claim activation.

A source change can be:
- implemented;
- verified;
- locally committed;
- restart-required.

Say so truthfully.

Do not kill the Feishu Gateway before it can deliver its terminal reply.

## Verification

At minimum complete the gates in `09_ACCEPTANCE_GATES.md`.

Run targeted tests during development and then the real repository regression gates.

Update `BUILD_MANIFEST.json` surgically according to `AGENTS.md`.

If an existing unrelated lint/test failure is present, distinguish it from regressions introduced by this task.

## Acceptance standard

The task is complete only when a real Feishu operator can select the coding profile, send/reference a Spec Pack, and the existing ZUAEF Agent can inspect/edit/test the real repo without requiring Codex/Pi.

Return a final implementation report containing:
- architecture implemented;
- files changed;
- profile/tool surface;
- Feishu attachment behavior;
- tests/results;
- real Feishu canary result if environment permits;
- local commit;
- activation/restart state;
- any genuinely unresolved blocker.

Do not replace the requested business outcome with a framework-design exercise.
