# 01 — Product Requirements

## User

Primary operator: trusted ZUAEF supervisor using Feishu.

This profile is not a customer-facing general chat profile.

## Primary job

The operator can say:

```text
@ZUAEF-BOT /coding
```

then:

```text
把我刚上传的 spec 包执行掉，目标是 zuaef-agent。
```

or:

```text
执行仓库里的 zuaef-xxx-spec-v0.1，把 coding profile 做完整。
```

or:

```text
给你自己增加一个 GitHub issue 处理组件，按现有 plugin 边界实现并验证。
```

The Agent should perform the engineering task with its own PydanticAI/Harness capabilities.

## Functional requirements

### FR1 — Coding profile

A production `coding` profile must be available through the normal profile resolver and Gateway routing.

### FR2 — Repo visibility

The profile must be able to inspect:
- `AGENTS.md`;
- source tree;
- plugins;
- profiles;
- skills;
- tests;
- docs;
- pyproject/uv configuration;
- Git state.

### FR3 — Repo mutation

The profile must be able to create/edit normal repository source files without using Codex/Pi.

### FR4 — Engineering command execution

The profile must be able to run a bounded command set that supports normal repository work, including at minimum:
- `git`
- `rg`
- `grep`
- `find`
- `ls`
- `cat`
- `sed`
- `head`
- `tail`
- `python`
- `uv`
- `pytest`
- `ruff`
- `make`

Optional, only when configured:
- `codex`
- `pi`

### FR5 — Test and validation

The Agent must be able to:
- run targeted tests while editing;
- run `profile check`;
- run repository regression gates relevant to the change;
- inspect `git diff`;
- leave a concise engineering result.

### FR6 — Self-extension

A normal coding task may create a new:
- plugin;
- profile;
- skill;
- toolset;
- capability wrapper;
- integration adapter;

when the task outcome requires it.

The Agent must prefer the repository's existing extension seams over core modifications.

### FR7 — Spec Pack input from local repo

If the user names a path/spec directory already present in the repo or workspace, the Agent can open it directly.

### FR8 — Spec Pack input from Feishu attachment

Feishu `file` resources must be downloaded into the existing workspace inbox and represented as `AttachmentRef`.

ZIP/tar extraction itself may be performed with the existing coding Shell/Python tool; do not build a new Spec parser runtime.

### FR9 — Existing Feishu UX

Keep current:
- allowlists;
- mention policy;
- profile access;
- natural ack;
- progress ping;
- terminal reply;
- approvals;
- thread/session semantics.

### FR10 — Codex/Pi explicit invocation

The following may work if the CLI is installed and permitted:

```text
用 codex 帮你完成这个修改。
```

```text
让 pi 先做一轮代码审查。
```

The model invokes the CLI through Shell. No backend adapter.

## Non-functional requirements

### NFR1 — No regression to other profiles

Quant and General Knowledge Worker must compose exactly as before.

### NFR2 — No global shell expansion

Do not make privileged coding commands available to every profile.

### NFR3 — No duplicate tool names

Repo-scoped FileSystem/Shell tools must be prefixed using upstream `PrefixTools`.

### NFR4 — Secrets stay unavailable

Repository `.env`, key files and obvious credential files must remain protected from repo FileSystem.

Shell command environments must use Harness credential stripping and must not intentionally inject credentials.

### NFR5 — Fail closed

If repo root is missing, not a Git worktree, outside configured trust assumptions, or required capability composition fails, profile resolution fails before model work.

### NFR6 — No fake execution claims

The final Feishu answer must distinguish:
- changed;
- tested;
- committed;
- not activated;
- blocked;
- external worker invoked or not invoked.

### NFR7 — Keep model-boundary cost bounded

Use CodeMode only if composition on the pinned Harness version is valid and it materially improves coding workflow. Do not add extra model turns for host bookkeeping.
