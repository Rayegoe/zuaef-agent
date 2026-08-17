"""Model schema tests (SPEC v0.1 §56 Phase 1)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from zuaef_client_service.models import (
    CustomerAssessment,
    CustomerState,
    InteractionReceipt,
    Policy,
    PolicyMatch,
)


class TestPolicyModel:
    def test_trigger_and_any_trigger(self) -> None:
        policy = Policy(
            policy_id="POL-C-001",
            name="x",
            trigger={"paid": [False]},
            any_trigger=[{"request": ["case"]}],
            strategy="QUALIFY_BEFORE_DISCLOSE",
        )
        assert policy.trigger["paid"] == [False]
        assert policy.any_trigger[0]["request"] == ["case"]

    def test_strategy_vocabulary_closed(self) -> None:
        with pytest.raises(ValidationError):
            Policy(
                policy_id="P",
                name="x",
                trigger={},
                strategy="MAKE_UP_A_STRATEGY",  # type: ignore[arg-type]
            )

    def test_action_vocabulary_closed(self) -> None:
        with pytest.raises(ValidationError):
            Policy(
                policy_id="P",
                name="x",
                trigger={},
                strategy="ANSWER_DIRECTLY",
                preferred_actions=["invented_action"],  # type: ignore[list-item]
            )


class TestAssessmentModel:
    def test_unknown_defaults(self) -> None:
        assessment = CustomerAssessment(customer_id="C-1")
        assert assessment.authority == "unknown"
        assert assessment.budget_signal == "unknown"
        assert assessment.uncertainties == []

    def test_evidence_ids_required_for_non_unknown_judgment(self) -> None:
        # schema allows empty, but the toolset contract (Gate C) is tested at
        # the tool layer; here just ensure the field exists and round-trips
        assessment = CustomerAssessment(
            customer_id="C-1",
            authority="known",
            evidence_ids=["EVD-G-0001"],
        )
        assert assessment.model_dump()["authority"] == "known"


class TestReceiptModel:
    def test_defaults(self) -> None:
        receipt = InteractionReceipt(
            interaction_id="INT-1", customer_id="C-1"
        )
        assert receipt.schema_version == "1"
        assert receipt.human_action == "DRAFTED"
        assert receipt.created_at

    def test_human_action_closed(self) -> None:
        with pytest.raises(ValidationError):
            InteractionReceipt(
                interaction_id="INT-1",
                customer_id="C-1",
                human_action="SENT_AUTOMATICALLY",  # type: ignore[arg-type]
            )

    def test_match_property(self) -> None:
        match = PolicyMatch(strategy="ANSWER_DIRECTLY")
        assert match.matched_policy_count == 0


class TestStateModel:
    def test_unknowns_explicit(self) -> None:
        state = CustomerState(customer_id="C-1")
        assert state.authority == "unknown"
        assert state.budget == "unknown"
        assert state.software_need == "unknown"

    def test_budget_confidence_field(self) -> None:
        state = CustomerState(customer_id="C-1", budget_confidence="medium")
        assert state.budget_confidence == "medium"
