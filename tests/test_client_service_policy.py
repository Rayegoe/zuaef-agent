"""Deterministic policy engine tests (SPEC v0.1 Gate A, §38/§39).

The ten scenarios mirror slice_root/policies/policy_tests.yaml T-001..T-010
(feature inputs + expected policy refs). No model, no corpus, no network.
"""

from __future__ import annotations

import pytest
from zuaef_client_service.policy import decide, match_policies, merge_matches

# (features, expected matched policy ids) — transcribed from the private
# corpus's policy_tests.yaml; feature inputs only, no customer content.
REGRESSION_CASES: list[tuple[dict, list[str]]] = [
    ({"paid": False, "prior_disclosure": "high", "request": "implementation_details"}, ["POL-C-001", "POL-C-002"]),
    ({"asks_case": True, "authority": "unknown", "budget": "unknown"}, ["POL-C-006"]),
    ({"prompt_changes_failed": True}, ["POL-C-004"]),
    ({"existing_stack": True, "software_need": "not_now"}, ["POL-C-010", "POL-C-018"]),
    ({"scale_signal": "very_large", "meeting_request": True}, ["POL-C-008", "POL-C-009"]),
    ({"request": "platform_guarantee"}, ["POL-C-016", "POL-C-022"]),
    ({"real_failure_sample": True}, ["POL-C-012"]),
    ({"asks_price": True}, ["POL-C-021"]),
    ({"goal": "unclear", "asks_full_solution": True}, ["POL-C-017", "POL-C-005"]),
    ({"corpus_reuse": "high"}, ["POL-C-019", "POL-C-022"]),
]


class TestGateARegression:
    @pytest.mark.parametrize(
        "features,expected",
        REGRESSION_CASES,
        ids=[f"T-{i:03d}" for i in range(1, len(REGRESSION_CASES) + 1)],
    )
    def test_policy_matches_exact(self, features: dict, expected: list[str]) -> None:
        match = decide(features)
        assert sorted(match.matched_policy_ids) == sorted(expected)

    def test_every_match_has_strategy_and_approval(self) -> None:
        for features, _ in REGRESSION_CASES:
            match = decide(features)
            assert match.strategy in {
                "ANSWER_DIRECTLY",
                "EXPLAIN_GENERAL_DIRECTION",
                "QUALIFY_NEED",
                "QUALIFY_AUTHORITY",
                "QUALIFY_BUDGET",
                "QUALIFY_BEFORE_DISCLOSE",
                "RESTRICT_DISCLOSURE",
                "REQUEST_MORE_CONTEXT",
                "PROPOSE_PAID_DIAGNOSIS",
                "ESCALATE_TO_HUMAN",
                "DECLINE_COMMITMENT",
            }
            assert match.approval_level in {"R0", "R1", "R2", "R3"}


class TestMergeRules:
    """§57: restricted wins, approval maxes, disclosure ceilings low."""

    def test_restricted_actions_union_and_priority(self) -> None:
        match = decide({"asks_price": True})
        assert "show_tiered_quote" in match.allowed_actions
        assert "commit_to_contract" in match.restricted_actions
        # an allowed action that is also restricted anywhere must not appear
        # as allowed
        assert set(match.allowed_actions).isdisjoint(match.restricted_actions)

    def test_approval_takes_highest(self) -> None:
        # T-002: POL-C-006 alone -> R2
        match = decide({"asks_case": True, "authority": "unknown"})
        assert match.approval_level == "R2"
        # mixed R1 + R2 -> R2
        match = decide({"paid": False, "prior_disclosure": "high", "request": "implementation_details"})
        assert match.approval_level == "R2"

    def test_disclosure_takes_lowest_ceiling(self) -> None:
        # T-006: POL-C-016 (D1) + POL-C-022 (D2) -> D1
        match = decide({"request": "platform_guarantee"})
        assert match.disclosure_ceiling == "D1"

    def test_no_match_falls_back_to_request_more_context(self) -> None:
        match = decide({"customer_likes_weather": True})
        assert match.matched_policy_ids == []
        assert match.strategy == "REQUEST_MORE_CONTEXT"
        assert match.approval_level == "R0"


class TestMatchSemantics:
    def test_missing_feature_key_fails_closed(self) -> None:
        # POL-C-006 requires asks_case + authority; authority alone is not
        # enough, missing asks_case means no match (no guessing, §48)
        match = decide({"authority": "unknown"})
        assert "POL-C-006" not in match.matched_policy_ids

    def test_list_valued_feature_matches_any(self) -> None:
        # request is a list-valued feature; any element matching an allowed
        # value satisfies the condition
        matches = match_policies({"request": ["platform_guarantee", "case"]})
        ids = {p.policy_id for p in matches}
        assert "POL-C-016" in ids  # request platform_guarantee
        assert "POL-C-022" in ids  # any_trigger group on platform_guarantee
        assert "POL-C-006" not in ids  # needs asks_case + authority booleans

    def test_any_trigger_group_or_semantics(self) -> None:
        # POL-C-022 fires on either request root-cause/platform OR corpus_reuse
        a = decide({"request": "platform_guarantee"})
        b = decide({"corpus_reuse": "high"})
        assert "POL-C-022" in a.matched_policy_ids
        assert "POL-C-022" in b.matched_policy_ids

    def test_merge_empty_is_stable(self) -> None:
        merged = merge_matches([])
        assert merged.matched_policy_ids == []
        assert merged.strategy == "REQUEST_MORE_CONTEXT"


class TestPolicyShape:
    def test_all_policies_have_evidence(self) -> None:
        from zuaef_client_service.canonical import CANONICAL_POLICIES

        for policy in CANONICAL_POLICIES:
            assert policy.policy_id.startswith("POL-C-")
            assert policy.evidence_ids, policy.policy_id
            assert policy.strategy, policy.policy_id

    def test_trigger_keys_within_vocabulary(self) -> None:
        from zuaef_client_service.canonical import CANONICAL_POLICIES

        known = {
            "paid", "prior_disclosure", "request", "asks_case", "asks_price",
            "asks_full_solution", "authority", "budget", "prompt_changes_failed",
            "existing_stack", "software_need", "scale_signal", "meeting_request",
            "real_failure_sample", "corpus_reuse", "repeat_consulting", "goal",
            "method_validated", "root_cause_unclear",
        }
        for policy in CANONICAL_POLICIES:
            keys = set(policy.trigger) | {
                k for group in policy.any_trigger for k in group
            }
            assert keys <= known, (policy.policy_id, keys - known)

    def test_policy_roundtrip(self) -> None:
        from zuaef_client_service.canonical import CANONICAL_POLICIES, policy_by_id

        for policy in CANONICAL_POLICIES:
            assert policy_by_id(policy.policy_id) is policy
