# Coding profile

`coding` composes the existing single Agent with upstream Harness repository
FileSystem/Shell (`repo_*`), workspace Shell, RepoContext and a deferred coding
Skill. Core workspace files, Skills, Planning, output limits and StepPersistence
retain their current authority. No external coding CLI or second runtime is required.

## Install and configure

Run `uv sync --inexact` in the deployment checkout (preserves installed optional
groups), then `uv run --no-sync zuaef-agent plugin list` and
`uv run --no-sync zuaef-agent profile check coding --config-root .`.

The Gateway resolves profiles from the deployment config root
(`$ZUAEF_CONFIG_ROOT/profiles/`, default `~/.config/zuaef/profiles/`), **not**
from the checkout's `profiles/` directory: install the profile with
`cp profiles/coding.toml <config-root>/profiles/`. `--config-root .` only
verifies the checkout copy. Profile TOMLs are read per run, so installing or
editing one needs no restart; `.env` and code changes still do.

`profiles/coding.toml` explicitly configures `repo_root = "~/zuaef-agent"`:
Barry expands this to `/home/barry/zuaef-agent`; OPi5's orangepi user expands it
to `/home/orangepi/zuaef-agent`. For another checkout or disposable worktree,
set this value to its absolute path. The plugin never falls back to workspace
and never creates a missing repo. It requires the Git worktree root and
`AGENTS.md` plus `pyproject.toml`; linked Git worktrees are supported.

The six strictly validated config keys are `repo_root`, `code_mode`,
`allow_codex`, `allow_pi`, `allow_local_commit`, `output_language`.
Unknown keys and invalid types fail before model work. Current defaults in the
shipped profile permit local commits after verification, disable Codex/Pi and
CodeMode, and request Chinese output. Optional CLI flags authorize Shell command
names; they do not install executables or inject credentials.

CodeMode ON/OFF both pass native file edit, Shell verification and completion
checks on Harness 0.29.0/PydanticAI 2.40.0. ON exposes one `run_code` and leaves
Shell directly available. OFF is the production default until a real coding
trajectory demonstrates a benefit; compatibility alone is not admission evidence.

The profile requests only context controls; ToolSearch and ConversationSearch
are denied at the profile level (still subject to the existing host ceiling,
`ZUAEF_ENABLE_CONTEXT_CONTROLS` etc.). The single-purpose profile has no
reproduced coding failure that needs either search surface, and the 2026-09-09
execution-discipline evidence (run `aea67372`: an 18-request limit_reached
small-demo run dominated by inventory/planning/exploration) removed them.
RepoContext comes from the plugin.

## Execution discipline (2026-09-09, Spec v0.1)

Coding behavior is **always-on plugin instruction**, not a deferred skill load:

- RepoContext autoloads `AGENTS.md` only (repository authority); README is
  retrieval material for on-demand reading, and the `inventory_agent_context`
  asset-inventory tool is disabled.
- The core coding discipline (match effort to task size, no
  planning/inventory startup on small tasks, edit as soon as evidence suffices,
  narrowest verification immediately, Planning only for genuinely multi-step
  work) never depends on `load_capability`. The `coding` skill remains
  registered as optional deeper material (Spec packs, archive safety, Codex/Pi
  verification protocol).
- Acceptance observation for a small task: ~4-8 model requests / 6-14 tool
  calls (acceptable <=12 with a real test failure); these are observational
  metrics, not runtime gates. Baseline failure:
  `aea67372b0eb4bd799c8b5fa4585572d` (18/18 requests, 31 tool calls, zero
  implementation calls).

**Intentional adjustment to the Spec's recommended shape:** generalist `shell`
is false. The existing core Shell inherits the host environment without credential
filtering. The plugin instead supplies both workspace and repo Shell with the
same explicit command list and Harness environment filtering. This preserves
attachment extraction while avoiding an unfiltered second Shell; Core and other
profiles are untouched. Do not enable core Shell alongside this plugin.

## Trusted Feishu access

Restrict `FEISHU_USER_ALLOWLIST` to trusted supervisors and, for groups, use
`FEISHU_GROUP_ALLOWLIST` plus the existing mention policy. Merge these examples
into existing routing mappings rather than replacing other profiles' entries:

```sh
ZUAEF_GATEWAY_PROFILE_ALIASES='{"coding":"coding"}'
ZUAEF_GATEWAY_PROFILE_ACCESS='{"coding":{"allowed_surfaces":["feishu"],"allowed_chat_types":["p2p","group"],"allowed_channel_ids":["<dedicated-chat-id>"]}}'
```

Use `/profile coding` or the configured `/coding` alias. Gateway reads `.env` at
process start, so configuration or imported-code changes require an operator
restart **after the current terminal reply**. This feature does not restart or
push automatically. A profile check is composition verification, not proof that
an already-running Gateway has loaded the source.

## Shell permissions and limits

Both Shell roots allow `git`, `rg`, `grep`, `find`, `ls`, `cat`, `sed`, `head`,
`tail`, `python`, `uv`, `pytest`, `ruff`, `make`, with optional `codex`/`pi`.
Harness strips common provider environment variables and names matching API
keys, tokens, secrets, passwords, credentials and SSH agent sockets. Repository
FileSystem denies `.git`, `.env` variants, key files, secrets/credentials and
obvious SSH key paths, including resolved symlink aliases.

This is a trusted operator facility, **not a hostile-code sandbox**. Python,
Git, build scripts and child processes can read host files, load `.env` or spawn
other commands. Command allowlists cannot enforce local-commit versus push
semantics. `allow_local_commit` is explicit model-visible policy, not a Git
subcommand security filter. Source access allows changing future agent code.
The agent must not use Shell to read secrets, push/publish, restart or perform
destructive host operations; external effects require a separately native
approval-gated tool, which this plugin does not supply. Isolate the deployment
at the OS/user level if the input or repository cannot be trusted.

## File attachments

Authorized SDK `file` resources download through `download_resource` and become
workspace-relative `inbox/feishu/<message-id>/<original-name>` AttachmentRefs.
Text+file and file-only messages use the existing prompt/run seam; file-only
text is neutral. Unsupported resources do not trigger downloads. The adapter
never interprets Specs or extracts archives.

`ZUAEF_GATEWAY_MAX_UPLOAD_BYTES` applies to downloaded bytes. SDK 1.4 provides
no size metadata or streaming cap: the full response is allocated **before**
the length check. MIME is unknown; size is measured. Invalid names/message IDs,
symlink destinations and existing files are rejected; exclusive writes cannot
overwrite another attachment. A failed resource produces a transport error and
no run for that message. Earlier successfully stored files from a multi-resource
message may remain in inbox; no partial envelope is dispatched.

The SDK must have message-resource read permissions. Real Feishu routing,
file-download and engineering canaries are deployment acceptance gates, not
inferred from offline tests. Final engineering replies must state changes,
verification, local commit and activation/restart status independently.
