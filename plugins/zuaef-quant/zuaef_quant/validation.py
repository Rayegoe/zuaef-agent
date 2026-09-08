"""Validation accounting for the quant evidence plane — D2 Quant Evidence
Accounting (operator directive after the 2026-09-08 "三周多" review).

Pure derivation over facts the host already has (canonical trading
artifacts); no second state store, no persistence. Core principle:

    strategy maturity metrics are LEDGER facts the model explains —
    never prose estimates a model sums up ("约三周多" is a defect).

Two planes this module keeps explicitly separate (incident 505438f3 review:
"observations=3, settled=2" next to "三笔全部处于 EXIT_ALERT" read as a
contradiction when one natural-language sentence mixed them):

- position lifecycle plane (positions.json): HOLD → EXIT_ALERT → CLOSED;
- forward observation plane (forward.json): d1/d3/d5/d8 windows fill as
  market days pass; an observation is SETTLED only when its full-horizon
  (d8) window is present.

Trading days are measured operating days (distinct in-session soak scan
dates since validation start), never a calendar guess: the system may run
three months yet only see 30 valid market days.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

#: Soak rows with these statuses carried no in-session market observation.
_NON_OBSERVATION_STATUSES = {
    "MARKET_CLOSED",
    "PRE_OPEN",
    "LUNCH_BREAK",
    "SYSTEM_UNAVAILABLE",
}

#: The strategy's full forward horizon is the d8 window: an observation is
#: settled when its d8 forward return exists.
_FULL_HORIZON_FIELD = "d8"


def _obs_day(value: Any) -> str | None:
    day = str(value) if value else None
    return day or None


def compute_validation_accounting(
    *,
    positions: dict[str, Any],
    forward: dict[str, Any],
    soak_rows: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    as_of: _dt.date,
) -> dict[str, Any]:
    """Deterministic strategy-maturity facts from the canonical ledger.

    Absent inputs degrade to nulls/zeroes honestly (absence of a position is
    not zero validation); nothing here re-derives market state."""
    open_pos = positions.get("open") or []
    closed_pos = positions.get("closed") or []
    all_positions = [*open_pos, *closed_pos]
    observations = forward.get("observations") or []
    executed = [o for o in observations if o.get("kind") == "EXECUTED"]
    skipped = [o for o in observations if o.get("kind") == "SKIP"]

    entry_dates = [
        str(p.get("entry_date"))
        for p in all_positions
        if p.get("entry_date")
    ]
    started = min(entry_dates) if entry_dates else None

    calendar_days: int | None = None
    if started:
        calendar_days = (as_of - _dt.date.fromisoformat(started)).days + 1

    trading_days: int | None = None
    if started:
        scan_dates = {
            str(row.get("ts"))[:10]
            for row in soak_rows
            if row.get("status") not in _NON_OBSERVATION_STATUSES
            and started <= str(row.get("ts", ""))[:10] <= as_of.isoformat()
        }
        scan_dates.discard("")
        trading_days = len(scan_dates)

    closed_ids = {str(p.get("id")) for p in closed_pos}
    obs_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for o in observations:
        obs_by_symbol.setdefault(str(o.get("symbol")), []).append(o)

    lifecycle = []
    for p in sorted(all_positions, key=lambda x: str(x.get("entry_date") or "")):
        sym_obs = obs_by_symbol.get(str(p.get("symbol")), [])
        settled_obs = next(
            (o for o in sym_obs if o.get(_FULL_HORIZON_FIELD) is not None), None
        )
        latest_obs = sym_obs[0] if sym_obs else None
        lifecycle.append(
            {
                "symbol": p.get("symbol"),
                "entry_date": p.get("entry_date"),
                "entry_price": p.get("entry_price"),
                "venue": p.get("venue"),
                "state": p.get("state"),
                "exit_trigger": p.get("exit_reason"),
                "position_closed": str(p.get("id")) in closed_ids,
                "forward_observation": {
                    "day": _obs_day(latest_obs.get("day")) if latest_obs else None,
                    "settled": settled_obs is not None,
                    "d1": latest_obs.get("d1") if latest_obs else None,
                    "d5": latest_obs.get("d5") if latest_obs else None,
                    "d8": latest_obs.get("d8") if latest_obs else None,
                },
            }
        )

    settled_full = [o for o in executed if o.get(_FULL_HORIZON_FIELD) is not None]
    accumulating = [o for o in executed if o.get(_FULL_HORIZON_FIELD) is None]
    # Live-verification refinement (2026-09-08: production answered
    # trading_days=2 and the reader could not tell the measurement window is
    # narrower than the validation period): disclose when the soak record
    # itself starts after validation started.
    soak_dates = [
        str(row.get("ts"))[:10] for row in soak_rows if str(row.get("ts", ""))[:10]
    ]
    soak_record_since = min(soak_dates) if soak_dates else None
    limitations = [
        ("settled means the full-horizon (d8) forward window exists; an "
         "EXIT_ALERT position is still open until the human executes and "
         "record_trade_outcome closes it — the two planes are independent"),
        "validation age counts from the earliest paper position entry",
        ("trading days are measured in-session soak scan dates (actual "
         "operating days), never an exchange-holiday calendar"),
    ]
    if started and soak_record_since and soak_record_since > started:
        limitations.append(
            f"the soak record itself only begins {soak_record_since} (the "
            "continuous monitor went live after validation started; earlier "
            "entries were on-demand cycles) — the trading-day count covers "
            "only the recorded window"
        )
    return {
        "as_of": as_of.isoformat(),
        "forward_validation_started_at": started,
        "validation_age_calendar_days": calendar_days,
        "validation_age_trading_days": trading_days,
        "trading_days_basis": (
            "distinct in-session soak scan dates since validation start "
            "(measured operating days, not an exchange calendar)"
        ),
        "operating_days_record_since": soak_record_since,
        "observations": len(observations),
        "observations_executed": len(executed),
        "observations_skipped": len(skipped),
        "observations_settled_full_horizon": len(settled_full),
        "observations_accumulating": len(accumulating),
        "paper_entries": sum(1 for p in all_positions if p.get("venue") == "paper"),
        "real_entries": sum(1 for p in all_positions if p.get("venue") == "real"),
        "completed_exits": len(closed_pos),
        "open_positions": len(open_pos),
        "open_positions_in_exit_alert": sum(
            1 for p in open_pos if p.get("state") == "EXIT_ALERT"
        ),
        "ready_events_observed": sum(
            1 for a in alerts if a.get("type") == "NEW_READY"
        ),
        "near_events_observed": sum(1 for a in alerts if a.get("type") == "NEW_NEAR"),
        "lifecycle": lifecycle,
        "limitations": limitations,
    }
