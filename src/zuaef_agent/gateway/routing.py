"""Gateway profile-routing policy — Feishu Surface v0.1 (spec pack 03).

Data-driven, surface-agnostic routing that the Gateway Service applies on
every dispatch:

- ``profile_aliases`` — slash-command aliases (``/alias -> profile-id``);
- ``group_defaults``  — per-channel default profile (the chat-level binding);
- ``profile_access``  — per-profile admission policy (surface / chat-type /
  channel allowlists), enforced BEFORE any agent execution.

Everything is configuration (JSON environment values), never code: the
gateway source must not name a business profile. Profile admission answers
"may this session use that profile"; surface admission (which chat/user may
talk at all, mention policy, bot filtering) stays owned by the surface
adapter — the two gates are deliberately separate (spec pack 03 §6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProfileAccessRule:
    """One profile's admission policy. ``None`` means unrestricted."""

    allowed_surfaces: tuple[str, ...] | None = None
    allowed_chat_types: tuple[str, ...] | None = None
    allowed_channel_ids: tuple[str, ...] | None = None


@dataclass(frozen=True)
class RoutingPolicy:
    profile_aliases: dict[str, str] = field(default_factory=dict)
    group_defaults: dict[str, str] = field(default_factory=dict)
    profile_access: dict[str, ProfileAccessRule] = field(default_factory=dict)

    def resolve_alias(self, command: str) -> str | None:
        """Map a slash-command token (no leading slash) to a profile id."""
        return self.profile_aliases.get(command)

    def access_error(
        self,
        profile: str | None,
        *,
        surface: str | None = None,
        chat_type: str | None = None,
        channel_id: str | None = None,
    ) -> str | None:
        """Admission decision for one profile use. Returns ``None`` when
        allowed, otherwise a user-facing denial reason."""
        if profile is None:
            return None
        rule = self.profile_access.get(profile)
        if rule is None:
            return None
        if rule.allowed_surfaces is not None and surface not in rule.allowed_surfaces:
            return (
                f"profile {profile!r} is not available on surface {surface!r}"
                + self._surfaces_hint(rule.allowed_surfaces)
            )
        if rule.allowed_chat_types is not None and (
            chat_type not in rule.allowed_chat_types
        ):
            return (
                f"profile {profile!r} is enabled only for "
                f"{', '.join(rule.allowed_chat_types)} chats"
            )
        if rule.allowed_channel_ids is not None and (
            channel_id not in rule.allowed_channel_ids
        ):
            return (
                f"profile {profile!r} is enabled only in approved channels"
            )
        return None

    @staticmethod
    def _surfaces_hint(surfaces: tuple[str, ...]) -> str:
        if not surfaces:
            return ""
        return f" (available on: {', '.join(surfaces)})"


def parse_json_mapping(raw: str | None) -> dict[str, str]:
    """Parse a flat string-to-string JSON env value (aliases, group defaults)."""
    if not raw or not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in data.items()
    ):
        raise ValueError("expected a flat JSON object of string to string")
    return dict(data)


def parse_access_policy(raw: str | None) -> dict[str, ProfileAccessRule]:
    """Parse the ``ZUAEF_GATEWAY_PROFILE_ACCESS`` JSON env value.

    Shape (spec pack 03 §5):

    ``{"<profile-id>": {"allowed_chat_types": ["group"],
    "allowed_channel_ids": ["oc_..."]}}`` — every key optional.
    """
    if not raw or not raw.strip():
        return {}
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        # Config-parse contract: the CLI reports ValueError as a process
        # error, so malformed configuration must stay a ValueError.
        raise ValueError("expected a JSON object keyed by profile id")  # noqa: TRY004
    rules: dict[str, ProfileAccessRule] = {}
    for profile, spec in data.items():
        if not isinstance(profile, str) or not isinstance(spec, dict):
            raise ValueError(  # noqa: TRY004 — same config-parse contract
                "profile access entries must be string to object"
            )
        for key in spec:
            if key not in ("allowed_surfaces", "allowed_chat_types", "allowed_channel_ids"):
                raise ValueError(f"unknown profile-access key: {key!r}")
        rules[profile] = ProfileAccessRule(
            allowed_surfaces=_string_tuple(spec.get("allowed_surfaces")),
            allowed_chat_types=_string_tuple(spec.get("allowed_chat_types")),
            allowed_channel_ids=_string_tuple(spec.get("allowed_channel_ids")),
        )
    return rules


def _string_tuple(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a JSON array of strings")
    return tuple(value)
