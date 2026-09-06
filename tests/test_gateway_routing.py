"""Gateway routing policy tests — Feishu Surface v0.1 (spec pack 03 §4–§6).

The routing policy is data (JSON environment values): aliases, chat-level
default profiles and per-profile access rules. These tests pin parsing and
the admission decisions the Gateway Service applies before any run.
"""

from __future__ import annotations

import pytest

from zuaef_agent.gateway.routing import (
    ProfileAccessRule,
    RoutingPolicy,
    parse_access_policy,
    parse_json_mapping,
)

# ── parsing ────────────────────────────────────────────────────────────────


def test_parse_json_mapping_empty_and_valid():
    assert parse_json_mapping(None) == {}
    assert parse_json_mapping("") == {}
    assert parse_json_mapping('{"quant": "quant-decision"}') == {
        "quant": "quant-decision"
    }


def test_parse_json_mapping_rejects_non_flat_values():
    with pytest.raises(ValueError, match="flat JSON object"):
        parse_json_mapping('{"a": {"b": "c"}}')
    with pytest.raises(ValueError, match="flat JSON object"):
        parse_json_mapping("[1, 2]")


def test_parse_access_policy_empty_and_valid():
    assert parse_access_policy(None) == {}
    raw = (
        '{"example-profile": {"allowed_chat_types": ["group"], '
        '"allowed_channel_ids": ["oc_1"], "allowed_surfaces": ["feishu"]}}'
    )
    rules = parse_access_policy(raw)
    assert rules["example-profile"] == ProfileAccessRule(
        allowed_surfaces=("feishu",),
        allowed_chat_types=("group",),
        allowed_channel_ids=("oc_1",),
    )


def test_parse_access_policy_rejects_unknown_keys_and_shapes():
    with pytest.raises(ValueError, match="unknown profile-access key"):
        parse_access_policy('{"p": {"forbidden": true}}')
    with pytest.raises(ValueError, match="array of strings"):
        parse_access_policy('{"p": {"allowed_chat_types": "group"}}')
    with pytest.raises(ValueError, match="keyed by profile id"):
        parse_access_policy('["p"]')


# ── alias resolution ───────────────────────────────────────────────────────


def test_resolve_alias_hit_and_miss():
    routing = RoutingPolicy(profile_aliases={"expert": "writing"})
    assert routing.resolve_alias("expert") == "writing"
    assert routing.resolve_alias("unknown") is None
    assert RoutingPolicy().resolve_alias("expert") is None


# ── access policy decisions ────────────────────────────────────────────────


def test_access_error_allows_unlisted_profiles():
    assert RoutingPolicy().access_error("writing", surface="feishu") is None
    assert RoutingPolicy().access_error(None) is None


def test_access_error_surface_restriction():
    routing = RoutingPolicy(
        profile_access={"p": ProfileAccessRule(allowed_surfaces=("feishu",))}
    )
    assert routing.access_error("p", surface="feishu") is None
    error = routing.access_error("p", surface="telegram")
    assert error is not None
    assert "telegram" in error


def test_access_error_chat_type_restriction_denies_dm():
    """Spec pack 07 B4: a group-only profile must be denied in P2P/DM."""
    routing = RoutingPolicy(
        profile_access={"p": ProfileAccessRule(allowed_chat_types=("group",))}
    )
    assert routing.access_error("p", chat_type="group") is None
    error = routing.access_error("p", chat_type="p2p")
    assert error is not None
    assert "group" in error


def test_access_error_chat_type_denies_unknown_chat_type():
    routing = RoutingPolicy(
        profile_access={"p": ProfileAccessRule(allowed_chat_types=("group",))}
    )
    assert routing.access_error("p", chat_type=None) is not None


def test_access_error_channel_allowlist():
    """Spec pack 07 B5: an approved generic group outside the profile's
    channel allowlist must be denied."""
    routing = RoutingPolicy(
        profile_access={"p": ProfileAccessRule(allowed_channel_ids=("oc_lab",))}
    )
    assert routing.access_error("p", channel_id="oc_lab") is None
    error = routing.access_error("p", channel_id="oc_other")
    assert error is not None
    assert "approved channels" in error


def test_access_error_checks_are_cumulative():
    routing = RoutingPolicy(
        profile_access={
            "p": ProfileAccessRule(
                allowed_surfaces=("feishu",),
                allowed_chat_types=("group",),
                allowed_channel_ids=("oc_lab",),
            )
        }
    )
    assert routing.access_error("p", surface="feishu", chat_type="group", channel_id="oc_lab") is None
    # right channel, wrong chat type → denied
    assert routing.access_error("p", surface="feishu", chat_type="p2p", channel_id="oc_lab") is not None
    # right chat type, wrong channel → denied
    assert routing.access_error("p", surface="feishu", chat_type="group", channel_id="oc_x") is not None
