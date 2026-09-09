"""Thin trusted-repository composition; execution remains owned by Harness."""

import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai_harness import CodeMode, FileSystem, RepoContext, Shell
from pydantic_ai_harness.shell import LLM_API_KEY_ENV_PATTERNS

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv


class CodingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    repo_root: str = Field(min_length=1)
    code_mode: bool = False
    allow_codex: bool = False
    allow_pi: bool = False
    allow_local_commit: bool = False
    output_language: str = Field(default="zh-CN", min_length=1)


REPO_DENIED_PATTERNS = (
    ".git", ".git/*", "**/.git", "**/.git/*",
    "**/.env", "**/.env.*", "*.pem", "*.key", "**/secrets*",
    "**/credentials*", "**/id_rsa*", "**/id_ed25519*", "**/.ssh/*",
)
BASE_COMMANDS = (
    "git", "rg", "grep", "find", "ls", "cat", "sed", "head", "tail",
    "python", "uv", "pytest", "ruff", "make",
    # Read-only executable lookup: the guidance requires checking CLI
    # installation before claiming availability, so a probe must exist.
    "which",
)
DENIED_ENV_PATTERNS = (
    *LLM_API_KEY_ENV_PATTERNS, "*API_KEY*", "*TOKEN*", "*SECRET*", "*PASSWORD*",
    "*CREDENTIAL*", "SSH_AUTH_SOCK",
)


def build_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    try:
        options = CodingConfig.model_validate(config)
    except ValidationError as exc:
        raise CompositionError(f"invalid coding config: {exc}") from exc
    root = Path(options.repo_root).expanduser().resolve()
    if not root.is_dir() or not all(
        (root / anchor).is_file() for anchor in ("AGENTS.md", "pyproject.toml")
    ):
        raise CompositionError("coding repo_root must exist with AGENTS.md and pyproject.toml")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        if Path(result.stdout.strip()).resolve() != root:
            raise CompositionError("coding repo_root must be the Git worktree root")
    except (OSError, subprocess.SubprocessError) as exc:
        raise CompositionError("coding repo_root is not a readable Git worktree") from exc

    commands = [*BASE_COMMANDS]
    commands.extend(name for name, enabled in (
        ("codex", options.allow_codex), ("pi", options.allow_pi),
    ) if enabled)
    capabilities = [
        Shell(cwd=env.workspace_root, allowed_commands=commands,
              denied_env_patterns=DENIED_ENV_PATTERNS),
        FileSystem(root_dir=root, denied_patterns=REPO_DENIED_PATTERNS).prefix_tools("repo"),
        Shell(cwd=root, allowed_commands=commands,
              denied_env_patterns=DENIED_ENV_PATTERNS).prefix_tools("repo"),
        # AGENTS.md is the only always-on repo authority; README is retrieval
        # material and the asset inventory is a startup ritual this single-purpose
        # profile does not need (run aea67372 execution-discipline evidence).
        RepoContext(workspace_dir=root, home_dir=None, filenames=("AGENTS.md",),
                    expose_inventory_tool=False),
    ]
    if options.code_mode:
        capabilities.append(CodeMode())
    # Always-on execution discipline (Spec v0.1 §6); no mandatory skill-load step.
    guidance = FunctionToolset(instructions=(
        "You are the coding profile for the configured ZUAEF Git repository. "
        "Own the requested engineering outcome and act directly. Repository "
        "AGENTS.md is already supplied by RepoContext and is authoritative; do "
        "not reread it unless you need its literal contents for an edit. Use repo "
        "tools for source/tests and workspace tools for attachments/artifacts. "
        f"Output language: {options.output_language}. "
        "Match effort to task size. For small, example, demo, validation, typo, "
        "localized or clearly bounded tasks: do not create, read or maintain a "
        "plan; do not inventory agent capabilities or browse agent assets; do not "
        "search conversation history unless the user explicitly asks for an old "
        "decision; inspect only the smallest relevant repository surface; prefer "
        "a change touching no more than two files when that fully solves the "
        "task; make the edit as soon as you have enough evidence; run the "
        "narrowest relevant verification immediately after the edit; inspect the "
        "resulting diff/state and return the result; expand investigation only "
        "when the first implementation or verification fails. "
        "Use Planning only for genuinely multi-step work such as an explicit "
        "Spec Pack, migration, cross-cutting change, or work that cannot "
        "reasonably fit one focused inspect/edit/test cycle. "
        "README, broad repository searches, old conversations, Codex and Pi are "
        "on-demand resources, not startup steps. "
        "For an ambiguous request asking for a coding example, choose one "
        "genuinely useful, low-risk, repository-local improvement that "
        "demonstrates read/edit/test. Do not turn the request into a repository "
        "audit. "
        "Prefer the repository's lowest valid extension layer: Skill, Toolset, "
        "Plugin/Profile, admitted Capability, then Core only when lower layers "
        "cannot solve the task. "
        f"Local commits allowed: {options.allow_local_commit}; commit locally "
        "only when relevant checks are green. "
        f"Codex permitted: {options.allow_codex}; Pi permitted: {options.allow_pi}; "
        "they are optional helpers, never required for ordinary coding and never "
        "the authority for task completion; CLI installation must be checked "
        "before claiming availability. "
        "Shell matches bare allowed command names only: invoke pytest/uv/ruff "
        "directly or through uv run; path-prefixed executables such as "
        ".venv/bin/pytest are rejected; probe CLI availability with which. "
        "Do not read credentials via Shell. Never push, publish, restart "
        "services, or perform destructive host operations through Shell; those "
        "require a separately approval-gated tool that this plugin does not "
        "supply. "
        "Report changed, tested, committed and activation state separately."
    ))
    return PluginBundle(
        capabilities=capabilities, toolsets=[guidance],
        skill_dirs=[Path(__file__).parent / "skills"],
    )
