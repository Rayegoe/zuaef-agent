from __future__ import annotations

import math
import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of true/false/1/0/yes/no/on/off")


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _first_env_bool(*names: str) -> bool | None:
    for name in names:
        if os.getenv(name) is not None:
            return _env_bool(name, False)
    return None


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


# The generalist platform surface (SPEC v2.1 §4 / v1.0 §3). Availability is
# broad, authorization is per-deployment: AgentSettings holds the host ceiling,
# a profile's ``[generalist]`` section holds the deployment request, and the
# composition layer freezes ``host ∩ request`` as the effective policy.
#
# CLOSED (v1.2 SPEC §9): this tuple is a compatibility surface. Do NOT add new
# entries. A newly adopted Harness capability must first be evaluated as (1) a
# direct capability in an existing platform pack/profile, (2) a capability
# returned by a plugin, or (3) explicit local composition. A new global ZUAEF
# flag requires a written architecture decision and an explicit spec change.
GENERALIST_FLAGS = (
    "enable_web_search",
    "enable_web_fetch",
    "enable_tool_search",
    "enable_memory",
    "enable_conversation_search",
    "enable_context_controls",
    "enable_subagents",
    "enable_shell",
    "enable_repo_context",
)


def apply_generalist_policy(
    settings: AgentSettings,
    policy: dict[str, bool] | None,
    *,
    frozen: bool = False,
) -> AgentSettings:
    """Compute an effective-settings view from a generalist policy.

    ``frozen=False`` (composition time): ``effective = host ceiling ∩ request`` —
    a flag is on only when both the host allows it and the profile asks for it.

    ``frozen=True`` (resume): the snapshot's effective policy is the authority —
    it is applied exactly, reproducing the same deployment authority even when
    the current profile file changed after the pause.
    """
    if not policy:
        return settings
    changes: dict[str, object] = {}
    for flag in GENERALIST_FLAGS:
        requested = bool(policy.get(flag, False))
        changes[flag] = requested if frozen else getattr(settings, flag) and requested
    return settings.with_overrides(**changes)


@dataclass(frozen=True)
class AgentSettings:
    model: str = "openai:gpt-5.2"
    workspace_root: Path = Path("workspace")
    runtime_state_root: Path | None = None
    request_limit: int = 12
    tool_calls_limit: int = 40
    total_tokens_limit: int | None = None
    enable_planning: bool = True
    enable_skills: bool = True
    # Sandbox FileSystem capability (list_directory/read_file/...) — always on
    # for normal agents, but experiment runners that compose their own writing
    # toolset route file writes through save_artifact and disable the sandbox
    # so the model cannot derail into generic filesystem exploration.
    enable_filesystem: bool = True
    # Knowledge capability (search/read/list/write under knowledge/**) — same
    # discipline: off for single-purpose surfaces like the production writer.
    enable_knowledge: bool = True
    enable_tool_output_limits: bool = True
    enable_step_persistence: bool = True
    max_snapshots_per_run: int | None = 8
    skills_dir: Path = Path(".agents/skills")
    # Generalist platform surface (upstream primitives, SPEC v2.1 §4).
    # Availability is broad; AUTHORIZATION is per-deployment. The default
    # narrow business surface stays untouched; a deployment opts the
    # generalist capabilities in. Activation (LOAD/INVOKE) is task-driven.
    enable_shell: bool = False
    enable_repo_context: bool = False
    enable_web_search: bool = False
    enable_web_fetch: bool = False
    enable_tool_search: bool = False
    enable_memory: bool = False
    enable_conversation_search: bool = False
    enable_subagents: bool = False
    enable_context_controls: bool = False
    repo_context_dir: Path | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    compat_model: str | None = None
    openai_api_mode: str = "chat"
    openai_timeout_seconds: float = 180.0
    openai_max_retries: int = 3
    openai_enable_thinking: bool | None = None
    # Caller-owned durable delivery root (host setting, never plugin business
    # config): after a completed run, generic host transport copies the
    # receipt-listed artifacts here — outside the model-writable workspace so
    # cleanup of the runtime tree can never reach the delivered copies.
    delivery_root: Path | None = None

    def __post_init__(self) -> None:
        if self.request_limit <= 0:
            raise ValueError("request_limit must be > 0")
        if self.tool_calls_limit <= 0:
            raise ValueError("tool_calls_limit must be > 0")
        if self.total_tokens_limit is not None and self.total_tokens_limit <= 0:
            raise ValueError("total_tokens_limit must be > 0")
        if self.max_snapshots_per_run is not None and self.max_snapshots_per_run < 1:
            raise ValueError("max_snapshots_per_run must be >= 1 or None")
        if self.openai_base_url and not self.compat_model:
            raise ValueError("compat_model is required when openai_base_url is set")
        if self.openai_api_mode not in {"chat", "responses"}:
            raise ValueError("openai_api_mode must be one of chat/responses")
        if (
            not math.isfinite(self.openai_timeout_seconds)
            or self.openai_timeout_seconds <= 1
        ):
            raise ValueError("openai_timeout_seconds must be finite and > 1")
        if not 0 <= self.openai_max_retries <= 10:
            raise ValueError("openai_max_retries must be between 0 and 10")
        workspace = self.workspace_root.resolve()
        state = self.state_root.resolve()
        if state == workspace or state.is_relative_to(workspace):
            raise ValueError(
                "runtime state must live outside the model-writable workspace"
            )
        if self.delivery_root is not None:
            delivery = self.delivery_root.resolve()
            if delivery == workspace or delivery.is_relative_to(workspace):
                raise ValueError(
                    "delivery_root must live outside the model-writable workspace"
                )

    @property
    def state_root(self) -> Path:
        if self.runtime_state_root is not None:
            return self.runtime_state_root
        return self.workspace_root.parent / ".zuaef-state"

    @property
    def step_store_dir(self) -> Path:
        return self.state_root / "steps"

    @property
    def tool_result_dir(self) -> Path:
        return self.state_root / "tool-results"

    @property
    def receipt_dir(self) -> Path:
        return self.state_root / "receipts"

    @classmethod
    def from_env(cls) -> AgentSettings:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        max_snapshots = _env_int(
            "ZUAEF_MAX_SNAPSHOTS_PER_RUN", cls.max_snapshots_per_run
        )
        return cls(
            model=os.getenv("ZUAEF_MODEL", cls.model),
            workspace_root=Path(os.getenv("ZUAEF_WORKSPACE", str(cls.workspace_root))),
            runtime_state_root=Path(os.environ["ZUAEF_STATE_ROOT"])
            if os.getenv("ZUAEF_STATE_ROOT")
            else None,
            delivery_root=(
                Path(os.environ["ZUAEF_DELIVERY_ROOT"])
                if os.getenv("ZUAEF_DELIVERY_ROOT")
                else None
            ),
            request_limit=_env_int("ZUAEF_REQUEST_LIMIT", cls.request_limit),
            tool_calls_limit=_env_int("ZUAEF_TOOL_CALLS_LIMIT", cls.tool_calls_limit),
            total_tokens_limit=(
                _env_int("ZUAEF_TOTAL_TOKENS_LIMIT", 0)
                if os.getenv("ZUAEF_TOTAL_TOKENS_LIMIT")
                else None
            ),
            enable_planning=_env_bool("ZUAEF_ENABLE_PLANNING", cls.enable_planning),
            enable_skills=_env_bool("ZUAEF_ENABLE_SKILLS", cls.enable_skills),
            enable_filesystem=_env_bool(
                "ZUAEF_ENABLE_FILESYSTEM", cls.enable_filesystem
            ),
            enable_knowledge=_env_bool("ZUAEF_ENABLE_KNOWLEDGE", cls.enable_knowledge),
            enable_tool_output_limits=_env_bool(
                "ZUAEF_ENABLE_TOOL_OUTPUT_LIMITS", cls.enable_tool_output_limits
            ),
            enable_step_persistence=_env_bool(
                "ZUAEF_ENABLE_STEP_PERSISTENCE", cls.enable_step_persistence
            ),
            max_snapshots_per_run=max_snapshots,
            # Generalist surface: individually authorized by deployment.
            enable_shell=_env_bool("ZUAEF_ENABLE_SHELL", cls.enable_shell),
            enable_repo_context=_env_bool(
                "ZUAEF_ENABLE_REPO_CONTEXT", cls.enable_repo_context
            ),
            enable_web_search=_env_bool(
                "ZUAEF_ENABLE_WEB_SEARCH", cls.enable_web_search
            ),
            enable_web_fetch=_env_bool("ZUAEF_ENABLE_WEB_FETCH", cls.enable_web_fetch),
            enable_tool_search=_env_bool(
                "ZUAEF_ENABLE_TOOL_SEARCH", cls.enable_tool_search
            ),
            enable_memory=_env_bool("ZUAEF_ENABLE_MEMORY", cls.enable_memory),
            enable_conversation_search=_env_bool(
                "ZUAEF_ENABLE_CONVERSATION_SEARCH", cls.enable_conversation_search
            ),
            enable_subagents=_env_bool("ZUAEF_ENABLE_SUBAGENTS", cls.enable_subagents),
            enable_context_controls=_env_bool(
                "ZUAEF_ENABLE_CONTEXT_CONTROLS", cls.enable_context_controls
            ),
            repo_context_dir=(
                Path(os.environ["ZUAEF_REPO_CONTEXT_DIR"])
                if os.getenv("ZUAEF_REPO_CONTEXT_DIR")
                else None
            ),
            openai_base_url=_first_env("ZUAEF_OPENAI_BASE_URL", "LLM_API_BASE"),
            openai_api_key=_first_env("ZUAEF_OPENAI_API_KEY", "LLM_API_KEY"),
            compat_model=_first_env("ZUAEF_COMPAT_MODEL", "LLM_MODEL"),
            openai_api_mode=(
                _first_env("ZUAEF_OPENAI_API_MODE", "LLM_API_MODE")
                or cls.openai_api_mode
            ).lower(),
            openai_timeout_seconds=_env_float(
                "ZUAEF_OPENAI_TIMEOUT_SECONDS", cls.openai_timeout_seconds
            ),
            openai_max_retries=_env_int(
                "ZUAEF_OPENAI_MAX_RETRIES", cls.openai_max_retries
            ),
            openai_enable_thinking=_first_env_bool(
                "ZUAEF_OPENAI_ENABLE_THINKING", "LLM_ENABLE_THINKING"
            ),
        )

    def with_overrides(self, **changes: object) -> AgentSettings:
        return replace(self, **changes)
