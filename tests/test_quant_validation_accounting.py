"""D2 Quant Evidence Accounting — ledger-computed strategy maturity.

Operator directive after the 2026-09-08 review: maturity metrics are
ledger facts the model explains, never prose estimates; the position
lifecycle plane and the forward-observation plane stay explicitly
separate. Fixtures mirror the real production ledger (incidents
9c1c9abb / 505438f3 review).
"""

from __future__ import annotations

import datetime as _dt

from zuaef_quant.validation import compute_validation_accounting

AS_OF = _dt.date(2026, 9, 8)


def _positions() -> dict:
    return {
        "open": [
            {
                "id": "p-0003", "symbol": "600519", "venue": "paper",
                "entry_date": "2026-08-15", "entry_price": 1690.5,
                "state": "EXIT_ALERT",
                "exit_reason": "stop_loss 3% (entry 1690.5, now 1324.0)",
            },
            {
                "id": "p-0001", "symbol": "601799", "venue": "paper",
                "entry_date": "2026-08-20", "entry_price": 76.32,
                "state": "EXIT_ALERT",
                "exit_reason": "close_below_ma5 (76.32 < 77.10)",
            },
            {
                "id": "p-0002", "symbol": "000807", "venue": "paper",
                "entry_date": "2026-09-02", "entry_price": 12.1,
                "state": "EXIT_ALERT",
                "exit_reason": "take_profit 6% (entry 12.1, now 26.82)",
            },
        ],
        "closed": [
            {
                "id": "p-0004", "symbol": "600015", "venue": "paper",
                "entry_date": "2026-08-18", "entry_price": 9.9,
                "state": "CLOSED", "exit_reason": "manual",
            }
        ],
    }


def _forward() -> dict:
    return {
        "observations": [
            {"kind": "EXECUTED", "symbol": "601799", "day": "2026-08-20",
             "d1": 0.133, "d5": 0.072, "d8": 0.024},
            {"kind": "EXECUTED", "symbol": "600519", "day": "2026-08-15",
             "d1": -0.235, "d5": -0.247, "d8": -0.229},
            {"kind": "EXECUTED", "symbol": "000807", "day": "2026-09-02",
             "d1": 1.262},
            {"kind": "SKIP", "symbol": "600015", "day": "2026-08-21", "d8": 0.01},
        ]
    }


def _soak() -> list[dict]:
    """21 calendar days of soak rows: 8 in-session observation days plus
    closed/lunch/system rows that must not count as operating days."""
    rows = []
    for day, status in [
        ("2026-08-15", "ALERTS"), ("2026-08-18", "ALERTS"), ("2026-08-19", "MARKET_CLOSED"),
        ("2026-08-20", "ALERTS"), ("2026-08-21", "NO_TRADE"), ("2026-08-22", "MARKET_CLOSED"),
        ("2026-08-25", "ALERTS"), ("2026-08-26", "SYSTEM_UNAVAILABLE"), ("2026-08-27", "ALERTS"),
        ("2026-09-02", "ALERTS"), ("2026-09-03", "LUNCH_BREAK"), ("2026-09-04", "ALERTS"),
    ]:
        rows.append({"ts": f"{day}T09:47:00+08:00", "status": status, "symbols": 50})
    return rows


def _alerts() -> list[dict]:
    return [
        {"type": "NEW_READY", "symbol": "601799", "ts": "2026-08-20T09:35:00+08:00"},
        {"type": "NEW_READY", "symbol": "600519", "ts": "2026-08-15T09:35:00+08:00"},
        {"type": "NEW_NEAR", "symbol": "002415", "ts": "2026-09-08T11:06:00+08:00"},
    ]


def test_validation_age_both_bases_from_ledger():
    a = compute_validation_accounting(
        positions=_positions(), forward=_forward(), soak_rows=_soak(),
        alerts=_alerts(), as_of=AS_OF,
    )
    # 2026-08-15 → 2026-09-08 inclusive = 25 calendar days
    assert a["forward_validation_started_at"] == "2026-08-15"
    assert a["validation_age_calendar_days"] == 25
    # only distinct in-session scan dates count: 8 (10 candidates minus
    # MARKET_CLOSED×2, LUNCH_BREAK, SYSTEM_UNAVAILABLE)
    assert a["validation_age_trading_days"] == 8


def test_observations_settled_vs_accumulating_split():
    a = compute_validation_accounting(
        positions=_positions(), forward=_forward(), soak_rows=_soak(),
        alerts=_alerts(), as_of=AS_OF,
    )
    assert a["observations"] == 4
    assert a["observations_executed"] == 3
    assert a["observations_skipped"] == 1
    assert a["observations_settled_full_horizon"] == 2
    assert a["observations_accumulating"] == 1


def test_position_lifecycle_separates_exit_alert_from_settled():
    """The 505438f3 contradiction: 3× EXIT_ALERT ≠ settled, ≠ closed."""
    a = compute_validation_accounting(
        positions=_positions(), forward=_forward(), soak_rows=_soak(),
        alerts=_alerts(), as_of=AS_OF,
    )
    assert a["open_positions"] == 3
    assert a["open_positions_in_exit_alert"] == 3
    assert a["completed_exits"] == 1
    assert a["paper_entries"] == 4 and a["real_entries"] == 0
    by_symbol = {row["symbol"]: row for row in a["lifecycle"]}
    p3 = by_symbol["600519"]
    assert p3["state"] == "EXIT_ALERT"
    assert p3["position_closed"] is False
    assert p3["exit_trigger"] == "stop_loss 3% (entry 1690.5, now 1324.0)"
    assert p3["forward_observation"]["settled"] is True  # d8 present
    p2 = by_symbol["000807"]
    assert p2["forward_observation"]["settled"] is False  # only d1 so far
    assert p2["position_closed"] is False
    p4 = by_symbol["600015"]
    assert p4["position_closed"] is True
    assert p4["forward_observation"]["settled"] is True


def test_ready_and_near_event_counts():
    a = compute_validation_accounting(
        positions=_positions(), forward=_forward(), soak_rows=_soak(),
        alerts=_alerts(), as_of=AS_OF,
    )
    assert a["ready_events_observed"] == 2
    assert a["near_events_observed"] == 1


def test_absent_ledger_is_honest_nulls_not_zero_age():
    a = compute_validation_accounting(
        positions={"open": [], "closed": []},
        forward={"observations": []},
        soak_rows=[], alerts=[], as_of=AS_OF,
    )
    assert a["forward_validation_started_at"] is None
    assert a["validation_age_calendar_days"] is None
    assert a["validation_age_trading_days"] is None
    assert a["observations"] == 0
    assert a["completed_exits"] == 0
    assert a["lifecycle"] == []


def test_no_soak_rows_leaves_trading_days_unknown_but_keeps_calendar():
    a = compute_validation_accounting(
        positions=_positions(), forward=_forward(), soak_rows=[],
        alerts=_alerts(), as_of=AS_OF,
    )
    assert a["validation_age_calendar_days"] == 25
    assert a["validation_age_trading_days"] == 0
