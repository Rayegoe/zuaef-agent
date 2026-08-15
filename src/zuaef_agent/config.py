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
    enable_tool_output_limits: bool = True
    enable_step_persistence: bool = True
    max_snapshots_per_run: int | None = 8
    skills_dir: Path = Path(".agents/skills")
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    compat_model: str | None = None
    openai_api_mode: str = "chat"
    openai_timeout_seconds: float = 180.0
    openai_max_retries: int = 3
    openai_strict_tool_definitions: bool = True
    openai_multiple_system_messages: bool = True
    openai_supports_max_completion_tokens: bool = True
    openai_enable_thinking: bool | None = None

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
        if not math.isfinite(self.openai_timeout_seconds) or self.openai_timeout_seconds <= 1:
            raise ValueError("openai_timeout_seconds must be finite and > 1")
        if not 0 <= self.openai_max_retries <= 10:
            raise ValueError("openai_max_retries must be between 0 and 10")
        workspace = self.workspace_root.resolve()
        state = self.state_root.resolve()
        if state == workspace or state.is_relative_to(workspace):
            raise ValueError("runtime state must live outside the model-writable workspace")

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
        raw_max_snapshots = os.getenv("ZUAEF_MAX_SNAPSHOTS_PER_RUN")
        max_snapshots = cls.max_snapshots_per_run if raw_max_snapshots is None else int(raw_max_snapshots)
        return cls(
            model=os.getenv("ZUAEF_MODEL", cls.model),
            workspace_root=Path(os.getenv("ZUAEF_WORKSPACE", str(cls.workspace_root))),
            runtime_state_root=Path(os.environ["ZUAEF_STATE_ROOT"]) if os.getenv("ZUAEF_STATE_ROOT") else None,
            request_limit=int(os.getenv("ZUAEF_REQUEST_LIMIT", str(cls.request_limit))),
            tool_calls_limit=int(os.getenv("ZUAEF_TOOL_CALLS_LIMIT", str(cls.tool_calls_limit))),
            total_tokens_limit=int(os.environ["ZUAEF_TOTAL_TOKENS_LIMIT"]) if os.getenv("ZUAEF_TOTAL_TOKENS_LIMIT") else None,
            enable_planning=_env_bool("ZUAEF_ENABLE_PLANNING", cls.enable_planning),
            enable_skills=_env_bool("ZUAEF_ENABLE_SKILLS", cls.enable_skills),
            enable_tool_output_limits=_env_bool(
                "ZUAEF_ENABLE_TOOL_OUTPUT_LIMITS", cls.enable_tool_output_limits
            ),
            enable_step_persistence=_env_bool(
                "ZUAEF_ENABLE_STEP_PERSISTENCE", cls.enable_step_persistence
            ),
            max_snapshots_per_run=max_snapshots,
            openai_base_url=_first_env("ZUAEF_OPENAI_BASE_URL", "LLM_API_BASE"),
            openai_api_key=_first_env("ZUAEF_OPENAI_API_KEY", "LLM_API_KEY"),
            compat_model=_first_env("ZUAEF_COMPAT_MODEL", "LLM_MODEL"),
            openai_api_mode=(
                _first_env("ZUAEF_OPENAI_API_MODE", "LLM_API_MODE") or cls.openai_api_mode
            ).lower(),
            openai_timeout_seconds=float(
                _first_env("ZUAEF_OPENAI_TIMEOUT_SECONDS", "LLM_TIMEOUT_SECONDS")
                or cls.openai_timeout_seconds
            ),
            openai_max_retries=int(
                _first_env("ZUAEF_OPENAI_MAX_RETRIES", "LLM_MAX_RETRIES")
                or cls.openai_max_retries
            ),
            openai_enable_thinking=_first_env_bool(
                "ZUAEF_OPENAI_ENABLE_THINKING", "LLM_ENABLE_THINKING"
            ),
        )

    def with_overrides(self, **changes: object) -> AgentSettings:
        return replace(self, **changes)
