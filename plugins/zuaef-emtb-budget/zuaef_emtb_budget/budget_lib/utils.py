"""Shared helpers for EMTB budget commands — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from .models import EMTBBudgetDataPoint


def resolve_budget_amounts(
    point: EMTBBudgetDataPoint,
) -> tuple[float | None, float | None, float | None]:
    """Resolve period start/end/change using available fields."""
    start = point.period_start_amount
    end = point.period_end_amount
    change = point.current_period_change

    if start is None and end is not None and change is not None:
        start = end - change
    if end is None and start is not None and change is not None:
        end = start + change
    if change is None and start is not None and end is not None:
        change = end - start

    return start, end, change


def normalize_key(value: str | None) -> str:
    """Normalize grouping/filter keys."""
    return (value or "").strip().lower()
