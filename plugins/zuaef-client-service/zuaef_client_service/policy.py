"""Deterministic decision policy engine (SPEC v0.1 §56 Phase 3, §57 merge).

Matching is pure and deterministic: a policy matches when every trigger
feature key is present in the input features and its value is one of the
allowed values. Multiple hits merge under §57 — restricted actions union,
approval level takes the highest (R3 > R2 > R1 > R0), disclosure ceiling
takes the lowest, evidence ids union. No model is consulted here; Gate A
(10/10 regression tests) runs on this module alone.
"""

from __future__ import annotations

from .canonical import CANONICAL_POLICIES
from .models import (
    ApprovalLevel,
    DisclosureLevel,
    FeatureValue,
    Policy,
    PolicyMatch,
)

_APPROVAL_ORDER: dict[ApprovalLevel, int] = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
_DISCLOSURE_ORDER: dict[DisclosureLevel, int] = {
    "D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5,
}


def match_policies(
    features: dict[str, FeatureValue],
    *,
    corpus: list[Policy] | None = None,
) -> list[Policy]:
    """Every policy whose trigger conditions are fully satisfied.

    A trigger condition {key: [values]} is satisfied when ``key`` is present
    in features AND features[key] equals one of the allowed values (for a
    list-valued feature, when any element matches). ``any_trigger`` groups are
    alternatives (OR). A missing feature key means the policy does not match
    (fail closed — no guessing on unknowns, §48).
    """
    matches: list[Policy] = []
    for policy in corpus if corpus is not None else CANONICAL_POLICIES:
        if _policy_matches(policy, features):
            matches.append(policy)
    return matches


def _feature_value_matches(value: FeatureValue, allowed: list[FeatureValue]) -> bool:
    if isinstance(value, list):
        return any(v in allowed for v in value)
    return value in allowed


def _conditions_hold(
    conditions: dict[str, list[FeatureValue]], features: dict[str, FeatureValue]
) -> bool:
    for key, allowed in conditions.items():
        value = features.get(key)
        if value is None:
            return False
        if not _feature_value_matches(value, allowed):
            return False
    return True


def _policy_matches(policy: Policy, features: dict[str, FeatureValue]) -> bool:
    if not _conditions_hold(policy.trigger, features):
        return False
    if policy.any_trigger:
        return any(
            _conditions_hold(group, features) for group in policy.any_trigger
        )
    return True


def merge_matches(matches: list[Policy]) -> PolicyMatch:
    """Merge matched policies under §57 (fail closed)."""
    if not matches:
        return PolicyMatch(
            matched_policy_ids=[],
            strategy="REQUEST_MORE_CONTEXT",
            approval_level="R0",
            disclosure_ceiling="D5",
        )
    restricted: list[str] = []
    for policy in matches:
        for action in policy.restricted_actions:
            if action not in restricted:
                restricted.append(action)
    allowed: list[str] = []
    for policy in matches:
        for action in policy.preferred_actions:
            if action not in allowed and action not in restricted:
                allowed.append(action)
    approval = max(matches, key=lambda p: _APPROVAL_ORDER[p.approval_level]).approval_level
    ceiling = min(matches, key=lambda p: _DISCLOSURE_ORDER[p.disclosure_ceiling]).disclosure_ceiling
    # Primary strategy: highest-constraint policy wins; ties fall to lower
    # disclosure ceiling, then corpus order (stable, deterministic).
    primary = min(
        matches,
        key=lambda p: (
            -_APPROVAL_ORDER[p.approval_level],
            _DISCLOSURE_ORDER[p.disclosure_ceiling],
            CANONICAL_POLICIES.index(p) if p in CANONICAL_POLICIES else 0,
        ),
    )
    evidence: list[str] = []
    for policy in matches:
        for eid in policy.evidence_ids:
            if eid not in evidence:
                evidence.append(eid)
    return PolicyMatch(
        matched_policy_ids=[p.policy_id for p in matches],
        strategy=primary.strategy,
        allowed_actions=allowed,
        restricted_actions=restricted,
        approval_level=approval,
        disclosure_ceiling=ceiling,
        evidence_ids=evidence,
    )


def decide(
    features: dict[str, FeatureValue],
    *,
    corpus: list[Policy] | None = None,
) -> PolicyMatch:
    """Match + merge in one call: the deterministic policy decision."""
    return merge_matches(match_policies(features, corpus=corpus))
