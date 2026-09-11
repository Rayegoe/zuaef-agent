"""P4 engine-consolidation guards.

These tests protect the single production authority introduced by P4:

- ``zuaef_quant.scan`` owns the frozen entry decision and clause-gap math;
- ``zuaef_quant.scan_sidecar`` (CLI / semantic tool path),
  ``zuaef_quant.monitor`` (READY/NEAR projection) and
  ``zuaef_quant.candidates_sidecar`` (ranking input) import that same
  authority instead of re-deriving the clauses;
- ``zuaef_quant.validation`` owns the canonical forward-observation count
  projection used by both the model-facing validation surface and the
  dashboard's formal-forward counters.

Pure engine tests intentionally run without pandas; the plugin-owned identity
check is skipped when the quant side dependency is unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from zuaef_quant.scan import entry_clause_gaps, entry_trigger, evaluate_entry
from zuaef_quant.trading import mark_to_market, position_pnl
from zuaef_quant.validation import forward_evidence_counts

REPO_ROOT = Path(__file__).parents[1]


class TestEntryDecision:
    @pytest.mark.parametrize(
        ("pullback", "ratio", "strength", "expected"),
        [
            (-0.05, 1.80, 0.0, True),   # all three clauses exactly met
            (-0.06, 2.00, 0.05, True),
            (-0.0499, 1.80, 0.0, False),  # pullback just short
            (-0.05, 1.7999, 0.0, False),  # volume just short
            (-0.05, 1.80, -0.0001, False),  # strength negative
            (0.0, 3.0, 1.0, False),
        ],
    )
    def test_frozen_clause_truth_table(self, pullback, ratio, strength, expected):
        assert entry_trigger(
            pullback,
            ratio,
            strength,
            entry_pullback_max=-0.05,
            entry_volume_ratio_min=1.80,
        ) is expected

    def test_clause_gaps_are_zero_when_met_and_positive_otherwise(self):
        met = entry_clause_gaps(
            -0.06,
            1.80,
            0.01,
            10.0,
            entry_pullback_max=-0.06,
            entry_volume_ratio_min=1.80,
        )
        assert met == {"pullback": 0.0, "volume": 0.0, "strength": 0.0}

        short = entry_clause_gaps(
            -0.045,
            1.60,
            -0.05,
            10.0,
            entry_pullback_max=-0.06,
            entry_volume_ratio_min=1.80,
        )
        assert short["pullback"] == pytest.approx(0.25)
        assert short["volume"] == pytest.approx(0.111111, abs=1e-6)
        assert short["strength"] == pytest.approx(0.005)

    def test_strength_gap_fails_closed_when_price_unusable(self):
        gaps = entry_clause_gaps(
            -0.06,
            1.80,
            -0.01,
            0.0,
            entry_pullback_max=-0.06,
            entry_volume_ratio_min=1.80,
        )
        assert gaps["strength"] == 1.0

    def test_evaluate_entry_projects_trigger_gaps_and_near_band(self):
        ready = evaluate_entry(
            -0.06,
            2.00,
            0.05,
            10.0,
            entry_pullback_max=-0.05,
            entry_volume_ratio_min=1.80,
            near_band=0.25,
        )
        assert ready["trigger"] is True and ready["near"] is False
        assert ready["clause_distances"] == {
            "pullback": 0.0,
            "volume": 0.0,
            "strength": 0.0,
        }

        near = evaluate_entry(
            -0.045,
            1.60,
            -0.05,
            10.0,
            entry_pullback_max=-0.06,
            entry_volume_ratio_min=1.80,
            near_band=0.25,
        )
        assert near["trigger"] is False and near["near"] is True
        assert near["clause_distances"]["pullback"] == pytest.approx(0.25)
        assert near["clause_distances"]["volume"] == pytest.approx(0.111111, abs=1e-6)
        assert near["clause_distances"]["strength"] == pytest.approx(0.005)


class TestForwardEvidenceCountProjection:
    def test_distinct_settled_views_share_one_parse(self):
        counts = forward_evidence_counts(
            {
                "observations": [
                    {"kind": "EXECUTED", "d8": 0.01},
                    {"kind": "EXECUTED"},
                    {"kind": "SKIP", "d8": 0.02},
                ]
            }
        )
        assert counts == {
            "present": True,
            "count": 3,
            "executed": 2,
            "skipped": 1,
            "settled_all_kinds": 2,
            "settled_executed": 1,
            "accumulating_executed": 1,
        }

    def test_absent_forward_state_is_honest_zero_never_fabricated(self):
        assert forward_evidence_counts({}) == {
            "present": False,
            "count": 0,
            "executed": 0,
            "skipped": 0,
            "settled_all_kinds": 0,
            "settled_executed": 0,
            "accumulating_executed": 0,
        }
        assert forward_evidence_counts(None)["present"] is False


def test_plugin_scan_surfaces_import_the_shared_authority():
    """The CLI, monitor and candidate builder must hold the engine function
    objects themselves, not private copies of the clause expression."""
    pytest.importorskip("pandas")
    from zuaef_quant import candidates_sidecar as builder
    from zuaef_quant import monitor
    from zuaef_quant import scan_sidecar as live_scan

    assert live_scan.entry_trigger is entry_trigger
    assert monitor.evaluate_entry is evaluate_entry
    assert monitor._shared_entry_clause_gaps is entry_clause_gaps
    assert builder.entry_trigger is entry_trigger
    assert monitor.position_pnl is position_pnl
    assert monitor.mark_to_market is mark_to_market


def test_dashboard_reads_the_shared_forward_projection():
    from zuaef_quant.dashboard import render as dashboard

    assert dashboard.forward_evidence_counts is forward_evidence_counts


class TestPositionProjection:
    def test_pnl_uses_position_quantity_by_default(self):
        position = {"entry_price": 10.0, "shares": 500}
        assert position_pnl(position, 10.3) == 150.0

    def test_pnl_uses_explicit_close_quantity_for_settlement(self):
        position = {"entry_price": 10.0, "shares": 500}
        assert position_pnl(position, 10.3, shares=100) == 30.0

    def test_mark_to_market_is_price_plus_shared_pnl(self):
        position = {"entry_price": 76.32, "shares": 100}
        assert mark_to_market(position, 80.1) == {
            "price": 80.1,
            "pnl": position_pnl(position, 80.1),
        }
