# 08 — Implementation Tasks

Implement in this order. Do not fan out into parallel architecture work before the first causal slice works.

## P0 — Baseline and compatibility

### T001 — Read authorities

Read:
- `AGENTS.md`
- `src/zuaef_agent/core.py`
- `src/zuaef_agent/composition.py`
- `src/zuaef_agent/plugin_api.py`
- `src/zuaef_agent/profiles.py`
- `src/zuaef_agent/gateway/feishu.py`
- `src/zuaef_agent/gateway/bridge.py`
- `src/zuaef_agent/gateway/routing.py`
- `src/zuaef_agent/gateway/runner.py`
- one existing production plugin
- current pinned `pydantic-ai-harness` API from the installed environment

Do not assume upstream `main` APIs exactly match the pinned installed minor.

### T002 — Prove composition shape

In a disposable coding profile/plugin fixture, confirm:
- `FileSystem(...).prefix_tools("repo")` or equivalent current API;
- `Shell(...).prefix_tools("repo")`;
- `RepoContext`;
- `CodeMode` if enabled;
- no tool collisions with core.

If the API spelling differs, use the installed upstream primitive rather than recreating it.

## P1 — Production coding plugin

### T003 — Create `zuaef-coding` package

Add package, entry point and root workspace dependency.

### T004 — Implement config validation

Implement only the frozen config keys.

Fail closed on unknown keys.

### T005 — Repo root validation

Require a valid real repository path.

### T006 — Repo FileSystem

Compose upstream repo-scoped FileSystem under a prefix.

### T007 — Repo Shell

Compose upstream repo-scoped Shell under a prefix.

Use bounded allowed commands.

Conditionally include `codex` / `pi`.

### T008 — RepoContext

Compose upstream RepoContext against repo root.

### T009 — CodeMode

Enable only if the installed pinned API composes cleanly.

Do not block the product on CodeMode.

### T010 — Coding Skill

Add concise engineering guidance.

## P2 — Production profile

### T011 — Add `profiles/coding.toml`

Use the agreed generalist policy.

### T012 — Host ceiling

Ensure OPi5 deployment allows only the generalist capabilities requested by coding.

Do not globally authorize unrelated profiles by changing profile files.

### T013 — Profile routing

Configure alias/access policy without hard-coded Gateway business logic.

## P3 — Feishu attachment seam

### T014 — Wire max upload to Feishu adapter

Use existing Gateway max-upload configuration.

### T015 — Normalize file resources

Use current `lark-channel-sdk` public `InboundMessage.resources`.

### T016 — Download authorized resource

Use SDK download helper.

Persist under workspace-confined Feishu inbox.

### T017 — Build AttachmentRef

Populate:
- kind
- local_path
- original_name when known
- mime_type when known
- size when known

### T018 — File-only message

Do not silently discard an authorized file-only message.

### T019 — Transport failures

Surface download/permission/size failures without creating fake attachments.

## P4 — Self-hosting behavioral closure

### T020 — Direct repo edit

Run the real coding profile against the actual repo with a harmless requested source/doc edit in a disposable branch/worktree.

No Codex/Pi.

### T021 — Add a real component

Use the coding profile to create one small repository component through the correct extension layer, then verify it.

The component is part of the implementation itself where possible; do not invent a dummy feature just to test.

### T022 — Spec Pack path execution

Ask coding profile to execute a repo-local Spec Pack path.

### T023 — Feishu Spec attachment

Send a real Spec archive through Feishu and have the coding profile inspect it.

### T024 — Optional Codex command

If installed/configured, explicitly request Codex once and prove it is invoked as a Shell command, not through a backend abstraction.

### T025 — Optional Pi command

Same rule for Pi.

## P5 — Regression and deployment

### T026 — Targeted tests

Add focused tests for:
- plugin composition;
- invalid repo root;
- config keys;
- tool prefix/collision behavior;
- Feishu attachment normalization;
- unauthorized/non-supported resource handling.

These tests exist to protect production behavior; do not build a test-only architecture.

### T027 — Full repository gates

Run:
- relevant targeted pytest;
- full pytest;
- ruff gate according to repository policy;
- manifest coverage/update according to `AGENTS.md`.

### T028 — OPi5 install

`uv sync` / deployment sync using existing operational procedure.

### T029 — Real Feishu canary

Use actual Feishu, actual coding profile, actual repo/worktree.

### T030 — Final report

Report:
- files changed;
- profile composition;
- real Feishu result;
- tests;
- local commit;
- whether Gateway restart is still required;
- Codex/Pi role actually used.
