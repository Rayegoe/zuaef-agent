# 02 — Architecture

## Target path

```text
Feishu message / attachment
        |
        v
FeishuAdapter
  - allowlist
  - group policy
  - mention policy
  - text normalization
  - NEW: resource download -> AttachmentRef
        |
        v
GatewayService
  - existing routing
  - existing /profile and aliases
  - existing ack/progress
        |
        v
bridge.start_profile_run()
        |
        v
build_profile_agent(profile="coding")
        |
        +---------------- existing ZUAEF core ----------------+
        | FileSystem(workspace)                               |
        | Planning                                             |
        | Skills                                               |
        | ToolOutputLimits                                     |
        | StepPersistence                                      |
        | ConversationSearch / ContextControls if authorized   |
        +------------------------------------------------------+
        |
        +-------------- zuaef-coding plugin -------------------+
        | PrefixTools(FileSystem(repo_root), "repo")           |
        | PrefixTools(Shell(repo_root), "repo")                |
        | RepoContext(repo_root)                               |
        | CodeMode() when enabled                              |
        +------------------------------------------------------+
        |
        v
one existing PydanticAI Agent
        |
        v
repo edit -> test -> inspect diff -> optional local commit
        |
        v
existing RuntimeOutcome / RunReceipt
        |
        v
existing Gateway terminal delivery
```

## Why a small plugin is still correct

The plugin is not a coding runtime.

It only says:

> For this profile, compose these upstream capabilities against this repository root.

That is exactly what the current `PluginBundle(capabilities=...)` contract exists to do.

The plugin must not:
- schedule jobs;
- spawn a worker supervisor;
- own retries;
- persist execution state;
- interpret Feishu;
- create its own approval model;
- create a second receipt system.

## Why repo tools are prefixed

The normal ZUAEF core already owns workspace file tools.

Coding needs a second filesystem rooted at the Git repository.

Use PydanticAI `PrefixTools`:

```python
repo_fs = FileSystem(...).prefix_tools("repo")
repo_shell = Shell(...).prefix_tools("repo")
```

Conceptual model-facing names become repo-scoped rather than colliding with normal workspace tools.

Do not rename upstream tool functions manually.

## CodeMode placement

`CodeMode` is a PydanticAI Harness capability and uses Monty sandboxed Python for programmatic tool calling.

For coding:
- it may orchestrate multiple file/search/tool operations in one `run_code`;
- it is not a replacement for OS shell execution;
- recent Harness behavior intentionally does not fold Shell command tools into CodeMode.

Implementation must verify the pinned Harness API before enabling it in the final profile.

If CodeMode creates a real incompatibility, the coding profile must still ship using FileSystem + Shell + RepoContext. CodeMode is not allowed to become a blocker for the business outcome.

## No whole `Coder()` capability

`Coder()` is a useful upstream reference implementation, but the current ZUAEF core already includes several of its pieces.

Therefore v0.1 uses Coder's composition **principles**, not the combined capability as one object.

This avoids:
- duplicate FileSystem;
- duplicate Planning;
- duplicate context controls;
- duplicate tool output controls;
- duplicated or conflicting tool schemas.

## Self-extension path

```text
user asks for new ability
        |
        v
coding profile inspects AGENTS.md + relevant source
        |
        v
chooses lowest valid extension layer
        |
        +-> Skill
        +-> Toolset
        +-> Plugin
        +-> Profile
        +-> Capability
        |
        v
edits source directly
        |
        v
tests/profile check
        |
        v
local commit if requested/allowed
        |
        v
reports activation state
```

Core changes remain possible only when the existing repository's kernel rules permit them.

## Deployment activation boundary

A running Python Gateway cannot safely be expected to import its own modified plugin source mid-run.

Therefore v0.1 separates:
- **engineering completion**: edit + verify + optional commit;
- **activation**: process reload/restart after result delivery.

Do not kill the active Feishu process in the middle of the run just to claim self-activation.

A future verified hot-reload mechanism is not part of this scope.
