# 00 — Source of Truth

## Product outcome

Build one privileged production profile named `coding` that turns the existing ZUAEF Agent into a self-hosting coding agent.

"Self-hosting" means the Agent can use the repository as its engineering workspace, modify its own source/components, run verification, and leave the repository in a usable state.

It does **not** mean:
- a second agent runtime;
- a generic worker service;
- a backend abstraction around Codex/Pi;
- arbitrary hot-patching of a currently executing Python process;
- automatic production restart before the current reply is safely delivered.

## Existing facts that must be reused

Current ZUAEF already has:

- one core Agent;
- profile composition;
- plugin factories returning `PluginBundle`;
- PydanticAI/Harness `FileSystem`;
- Planning;
- Skills;
- ToolOutputLimits;
- StepPersistence;
- optional Shell;
- optional RepoContext;
- optional ToolSearch;
- optional ConversationSearch;
- optional ContextControls;
- Feishu WebSocket Gateway;
- profile aliases/defaults/access policy;
- run ack/progress/terminal rendering;
- `InboundEnvelope.attachments`;
- `bridge.project_prompt()` that adds attachment paths to the model-visible prompt;
- an existing real Codex CLI launcher elsewhere in `tools/supervisor_loop.py`.

Do not recreate any of these.

## Frozen architecture decisions

### D1 — ZUAEF stays one Agent

No agent registry. No `CodingAgent` subclass. No nested ZUAEF runtime.

The existing `build_profile_agent()` path remains the only agent assembly path.

### D2 — Upstream Harness is the coding harness

Use released PydanticAI/PydanticAI Harness primitives directly.

The ZUAEF plugin is allowed to be a thin composition adapter because profile/plugin composition is already the repository's production extension mechanism. It must not become a runtime framework.

### D3 — Do not compose `Coder()` wholesale

The current ZUAEF core already composes several capabilities that `Coder()` also bundles:
- FileSystem
- Planning
- ToolOutputLimits
- context/persistence-related capabilities

Adding `Coder()` wholesale risks duplicated behavior and tool collisions.

Use the upstream building blocks directly and only add the missing repo-scoped execution surface.

### D4 — Keep normal workspace and repo workspace distinct

The regular ZUAEF workspace remains the business/runtime workspace.

The coding profile additionally receives a repo-rooted engineering surface.

Repo engineering tools must be namespaced with upstream `PrefixTools` so they can coexist with the normal workspace tools.

### D5 — No `WorkerBackend`

Forbidden production additions:

```text
WorkerBackend
WorkerRunRequest
WorkerDispatcher
CodexBackend
PiBackend
coding worker daemon
coding job queue
coding state machine
```

Unless a future measured failure proves one is necessary, none belongs in v0.1.

### D6 — Codex and Pi are optional tools

If installed and explicitly allowed in profile config, `codex` and/or `pi` may appear in the repo Shell command allowlist.

The Agent decides whether they materially help, or the user can explicitly request one.

They remain subprocess tools, not architecture.

### D7 — Self-extension primarily means source-level extension

The Agent may directly:
- add/edit a plugin;
- add/edit a profile;
- add/edit a Skill;
- add/edit a Toolset;
- update repository-local composition;
- update tests/docs;
- run `uv`, `pytest`, `ruff`, `git` and other bounded engineering commands.

PydanticAI Harness Runtime Capability Creation is acknowledged upstream, but it is not required for v0.1. ZUAEF's frozen composition/resume semantics must not be weakened merely to load dynamic authored capabilities.

### D8 — Feishu remains transport-only

Feishu does not understand coding semantics.

Its only new responsibility is media normalization:
- identify supported incoming file resources;
- download them safely into the existing workspace inbox;
- create `AttachmentRef`;
- pass the normal `InboundEnvelope` upward.

### D9 — Existing execution truth remains unchanged

No new receipts, hashes, task ledgers, worker receipts or custom durability layer.

Use current:
- StepPersistence;
- RunReceipt;
- Gateway session state;
- normal terminal delivery.

### D10 — No new hash/integrity machinery

Do not introduce new SHA/checksum/fingerprint/manifest mechanisms for this feature.

Git state, existing profile composition identity, path containment, typed config and behavioral verification are sufficient unless a real failure proves otherwise.
