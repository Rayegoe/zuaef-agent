"""Profile loading and validation for the Plugin Composition Layer.

Profiles are one TOML file per explicit composition under
``$ZUAEF_CONFIG_ROOT/profiles/`` (default ``~/.config/zuaef/profiles/``).
Installing a plugin never activates it; only naming it in a profile does.

Secret policy: a profile may only carry non-secret configuration. A
secret-named key anywhere in plugin config fails the profile load, so the
CompositionSnapshot — which is JSON-serialized into receipts — can never
leak a credential value.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .plugin_api import CompositionError

DEFAULT_CONFIG_ROOT = Path.home() / ".config" / "zuaef"
PROFILES_DIRNAME = "profiles"

# §13 Secret Policy: a secret-named key in plugin config is rejected at load.
# Top-level keys only — the common mistake; nested domain values stay the
# plugin's own contract, and the snapshot's JSON-only rule still applies.
_SECRET_KEY = re.compile(
    r"(api[_-]?key|password|passwd|secret|private[_-]?key|access[_-]?token|token|credential)",
    re.IGNORECASE,
)

_PROFILE_NAME = re.compile(r"[A-Za-z0-9_.-]+")


class ProfilePluginConfig(BaseModel):
    """One enabled plugin row inside a profile."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    allow_capabilities: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class ProfileConfig(BaseModel):
    """A validated profile document (schema version 1)."""

    model_config = ConfigDict(extra="forbid")

    # The TOML key is ``schema`` (spec §12); the Python attribute avoids
    # shadowing BaseModel's own ``schema``.
    schema_version: Literal[1] = Field(
        default=1,
        validation_alias="schema",
        serialization_alias="schema",
    )
    name: str
    plugins: list[ProfilePluginConfig] = Field(default_factory=list)

    def check_secret_policy(self) -> None:
        """Fail the load when any plugin config key looks like a secret."""
        for plugin in self.plugins:
            for key in plugin.config:
                if _SECRET_KEY.search(key):
                    raise CompositionError(
                        f"profile {self.name!r}: plugin {plugin.id!r} config key "
                        f"{key!r} is secret-named — profiles hold non-secret "
                        "configuration only (use environment / provider "
                        "credential mechanisms)"
                    )


def profiles_dir(config_root: Path | None = None) -> Path:
    """Profile directory for the given (or env/default) config root."""
    root = config_root or Path(
        os.getenv("ZUAEF_CONFIG_ROOT", str(DEFAULT_CONFIG_ROOT))
    )
    return root / PROFILES_DIRNAME


def list_profiles(config_root: Path | None = None) -> list[str]:
    """Profile names under the config root, sorted; absent root is empty."""
    directory = profiles_dir(config_root)
    if not directory.is_dir():
        return []
    return sorted(
        path.stem for path in directory.glob("*.toml") if path.is_file()
    )


def load_profile(name: str, config_root: Path | None = None) -> ProfileConfig:
    """Load and validate one profile; a profile file maps to ``<name>.toml``.

    Raises CompositionError for any problem: invalid name, missing file,
    unparsable TOML, schema violations, a declared name that does not match
    the file, duplicate plugin ids, or a secret-named config key.
    """
    if not _PROFILE_NAME.fullmatch(name):
        raise CompositionError(f"invalid profile name: {name!r}")
    target = profiles_dir(config_root) / f"{name}.toml"
    try:
        data = tomllib.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CompositionError(f"profile {name!r} not found at {target}") from None
    except tomllib.TOMLDecodeError as exc:
        raise CompositionError(
            f"profile {name!r} is not valid TOML: {exc}"
        ) from exc
    try:
        profile = ProfileConfig.model_validate(data)
    except ValidationError as exc:
        raise CompositionError(
            f"profile {name!r} failed schema validation: {exc}"
        ) from exc
    if profile.name != name:
        raise CompositionError(
            f"profile {name!r}: declared name {profile.name!r} does not "
            f"match the file name"
        )
    plugin_ids = [plugin.id for plugin in profile.plugins]
    if len(plugin_ids) != len(set(plugin_ids)):
        duplicates = sorted(
            {pid for pid in plugin_ids if plugin_ids.count(pid) > 1}
        )
        raise CompositionError(
            f"profile {name!r}: duplicate plugin id(s): {', '.join(duplicates)}"
        )
    profile.check_secret_policy()
    return profile
