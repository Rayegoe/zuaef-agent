"""Freshness derivation for the Quant trading context — Quant Freshness &
Natural Response Spec v0.1 §3–§5.

Pure derivation over facts the host already has (canonical trading
artifacts); no second state store, no persistence. Core principle:

    absence of observation != observed zero

The model never derives freshness itself: ``get_trading_context`` provides
``freshness_status`` / ``freshness_reason`` (plus the requested/data/scan
dates) as tool facts, and the plugin instructions forbid interpreting a
stale READY/NEAR count as a current-day result unless the status is FRESH.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

# China market wall clock: UTC+8, no DST.
MARKET_TZ = _dt.timezone(_dt.timedelta(hours=8))

#: The monitor's first daily scan window (live sessions start 09:30 local).
SCAN_WINDOW_START = _dt.time(9, 30)

# The only v0.1 statuses (spec §4).
FRESH = "FRESH"
NOT_SCANNED = "NOT_SCANNED"
STALE = "STALE"
MARKET_NOT_OPEN = "MARKET_NOT_OPEN"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

FRESHNESS_STATUSES = (
    FRESH,
    NOT_SCANNED,
    STALE,
    MARKET_NOT_OPEN,
    INSUFFICIENT_EVIDENCE,
)


def now_market() -> _dt.datetime:
    """Current wall clock in the market timezone (tests monkeypatch this)."""
    return _dt.datetime.now(MARKET_TZ)


def market_date_of(value: Any) -> _dt.date | None:
    """Market-local calendar date of an ISO timestamp or a plain date string.

    Naive datetimes are read as market-local wall clock (artifact ``ts``
    values carry ``+08:00``, but tolerate writers that dropped the offset).
    Anything unparseable stays ``None`` — the caller fails closed to
    INSUFFICIENT_EVIDENCE instead of guessing.
    """
    if isinstance(value, _dt.datetime):
        parsed = value
    elif isinstance(value, _dt.date):
        return value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return _dt.date.fromisoformat(text[:10])
        except ValueError:
            pass
        try:
            parsed = _dt.datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MARKET_TZ)
    return parsed.astimezone(MARKET_TZ).date()


# Backwards-compatible internal alias.
_market_date = market_date_of


def _is_weekday(day: _dt.date) -> bool:
    """Plausible A-share trading day by weekday only (no holiday calendar in
    v0.1: on a holiday the honest reading is "no same-day scan result yet",
    which the STALE/NOT_OPEN wording already conveys)."""
    return day.weekday() < 5


def derive_freshness(
    *,
    now: _dt.datetime,
    latest_market_data_date: Any,
    last_scan_at: Any,
) -> dict[str, str]:
    """Derive the freshness facts from host-owned dates (spec §4 precedence).

    Unparseable or contradictory dates fail closed to INSUFFICIENT_EVIDENCE.
    FRESH requires both the latest market-data day AND the last completed
    scan to equal the requested market date. MARKET_NOT_OPEN applies only on
    a weekday before the first scan window. ``latest_market_data_date`` is
    the canonical ``state.day``; ``last_scan_at`` is the timestamp of the
    last completed scan (a soak record that actually scanned symbols).
    """
    requested = now.astimezone(MARKET_TZ).date()
    latest = _market_date(latest_market_data_date)
    scanned = _market_date(last_scan_at)

    def result(status: str, reason: str) -> dict[str, str]:
        return {
            "requested_market_date": requested.isoformat(),
            "freshness_status": status,
            "freshness_reason": reason,
        }

    if latest is None or scanned is None:
        return result(
            INSUFFICIENT_EVIDENCE,
            "the data day or the last completed scan cannot be determined "
            "from the canonical artifacts; READY/NEAR must not be read as a "
            "current-day result",
        )
    if latest > requested or scanned > requested:
        return result(
            INSUFFICIENT_EVIDENCE,
            "artifact dates are ahead of the request date and contradict it; "
            "these artifacts cannot describe the requested day",
        )
    if latest == requested and scanned == requested:
        return result(
            FRESH,
            "latest market data and the last completed scan are both from "
            "today; READY/NEAR are today's scan results",
        )
    if latest < requested:
        if (
            now.astimezone(MARKET_TZ).time() < SCAN_WINDOW_START
            and _is_weekday(requested)
        ):
            return result(
                MARKET_NOT_OPEN,
                "today has not reached the strategy's first scan window, so "
                "no same-day scan result can exist yet",
            )
        return result(
            STALE,
            f"latest market data is from {latest.isoformat()}, before the "
            "requested day; the current READY/NEAR records are not today's "
            f"scan results (last completed scan: {scanned.isoformat()})",
        )
    return result(
        NOT_SCANNED,
        "today's market data is available, but the last completed scan is "
        f"from {scanned.isoformat()}; today's candidate state is not yet "
        "determined",
    )
