# 03 — Coding Profile and Plugin Spec

## New profile

Create:

`profiles/coding.toml`

Recommended production shape:

```toml
schema = 1
name = "coding"

[generalist]
web_search = false
web_fetch = false
tool_search = true
memory = false
conversation_search = true
context_controls = true
subagents = false
shell = true
repo_context = false

[[plugins]]
id = "coding"
allow_capabilities = true
defer_tools = false

[plugins.config]
repo_root = "/home/orangepi/zuaef-agent"
code_mode = true
allow_codex = true
allow_pi = true
allow_local_commit = true
output_language = "zh-CN"
```

Notes:

- `shell = true` keeps the existing workspace-rooted Shell available for attachment extraction and normal workspace operations.
- `repo_context = false` because the coding plugin contributes RepoContext for the actual repository root.
- `subagents = false` in v0.1; do not add delegation until a real coding failure justifies it.
- `web_search/web_fetch = false` initially. The coding profile can be expanded later if a measured docs/information failure requires open web.
- `tool_search = true` is compatible with large/deferred capability surfaces.
- `repo_root` is deployment configuration, not a secret.

## New plugin package

Create:

```text
plugins/zuaef-coding/
  pyproject.toml
  zuaef_coding/
    __init__.py
    plugin.py
    skills/
      coding/
        SKILL.md
```

Entry point:

```toml
[project.entry-points."zuaef.plugins"]
coding = "zuaef_coding.plugin:build_plugin"
```

Add the workspace package to root `pyproject.toml` the same way as existing production plugins.

## Plugin contract

The plugin factory receives existing `PluginEnv`.

It validates configuration and returns only `PluginBundle`.

Expected config keys:

```text
repo_root
code_mode
allow_codex
allow_pi
allow_local_commit
output_language
```

Unknown keys fail composition.

No secret-named keys.

## Repo root validation

Before returning the bundle:

1. Resolve/expand the configured path.
2. Require it to exist and be a directory.
3. Require `.git` worktree semantics:
   - either `.git` exists, or
   - `git rev-parse --show-toplevel` resolves successfully via a bounded host check if needed.
4. Require expected project anchors for this deployment:
   - `AGENTS.md`
   - `pyproject.toml`
5. Do not silently fall back to the normal workspace.
6. Do not create the repo root automatically.

A bad `repo_root` is a composition error before model work.

## Repo FileSystem capability

Use upstream Harness `FileSystem`.

Repo file operations must protect at minimum:

```text
.git/*
.env
.env.*
*.pem
*.key
**/secrets*
```

Do **not** protect:
- `plugins/**`
- `profiles/**`
- `.agents/skills/**`
- `src/**`
- `tests/**`
- `docs/**`

because self-extension must be able to modify them.

Wrap using upstream `PrefixTools` / `.prefix_tools("repo")`.

## Repo Shell capability

Use upstream Harness `Shell`.

Root it at the real repo.

Base allowlist:

```text
git
rg
grep
find
ls
cat
sed
head
tail
python
uv
pytest
ruff
make
```

Conditional additions:

```text
codex   # if allow_codex = true
pi      # if allow_pi = true
```

Do not add by default:

```text
ssh
scp
rsync
curl
wget
gh
systemctl
sudo
docker
podman
```

These may become separate deliberately approved capabilities later if the product outcome requires them.

Use the Harness LLM/API credential-stripping environment patterns. Add local deployment-specific secret environment patterns only if the installed Shell API supports them cleanly.

## RepoContext

Use upstream Harness `RepoContext` pointed at `repo_root`.

It should load the repository's engineering authority, especially:
- `AGENTS.md`
- `README.md`

Do not duplicate their content into giant coding system prompts.

## CodeMode

If `code_mode = true`, compose upstream Harness `CodeMode`.

Acceptance:
- profile composition succeeds on the repository's pinned Harness;
- one `run_code` surface exists as expected;
- Shell remains directly available according to upstream behavior;
- no duplicate `run_code` tool;
- no change to other profiles.

If the pinned API differs from upstream main, use the installed release API rather than coding against documentation from another minor version.

## Coding Skill

`skills/coding/SKILL.md` should be concise.

Required principles:

- Own the requested engineering outcome.
- Read `AGENTS.md` first for architecture constraints.
- Prefer the lowest extension layer that solves the task.
- Inspect before replacing.
- Use repo tools for source, workspace tools for attachments/artifacts.
- Run targeted verification after meaningful changes.
- Do not claim activation when only source/tests changed.
- Codex/Pi are optional helpers, never mandatory workflow steps.
- Do not implement a worker framework.
- Do not introduce new hash/manifest machinery without a concrete requirement.
- Stop if the requested operation would require a capability not actually composed.

Do not put a long procedural coding checklist in always-on instructions.
