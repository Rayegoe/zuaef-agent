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
        RepoContext(workspace_dir=root, home_dir=None, filenames=("AGENTS.md", "README.md")),
    ]
    if options.code_mode:
        capabilities.append(CodeMode())
    # Existing upstream instruction carrier; no new capability/runtime class.
    guidance = FunctionToolset(instructions=(
        f"Coding profile: repo tools edit/test the configured Git repository. "
        f"Workspace tools handle attachments/artifacts. Output language: {options.output_language}. "
        f"Local commits allowed: {options.allow_local_commit}. "
        f"Codex permitted: {options.allow_codex}; Pi permitted: {options.allow_pi}; "
        "CLI installation must be checked before claiming availability. "
        "Load the coding skill for engineering work. Never push, publish, restart services, "
        "or perform destructive host operations through Shell. These require a separately "
        "approval-gated tool; none is supplied by this plugin. Shell allowlisting is an "
        "accident guardrail, not hostile-code isolation. Shell matches bare command names "
        "only: path-prefixed executables such as .venv/bin/pytest are rejected, so invoke "
        "pytest/uv/ruff directly or through uv run. Do not read credentials via Shell. "
        "Report changed, tested, committed and activation state separately."
    ))
    return PluginBundle(
        capabilities=capabilities, toolsets=[guidance],
        skill_dirs=[Path(__file__).parent / "skills"],
    )
