"""Detect significant EMTB budget changes — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from .models import (
    SignificantChangeDetectionInput,
    SignificantChangeItem,
    SignificantChangeResult,
)
from .utils import resolve_budget_amounts


def detect_significant_changes(
    params: SignificantChangeDetectionInput,
) -> SignificantChangeResult:
    """Detect significant increases/decreases based on thresholds."""
    if not params.budget_data:
        raise ValueError("budget_data must contain at least one data point")

    increases: list[SignificantChangeItem] = []
    decreases: list[SignificantChangeItem] = []
    currency: str | None = None

    for point in params.budget_data:
        start, end, change = resolve_budget_amounts(point)
        if start is None or end is None or change is None:
            continue
        if currency is None:
            currency = point.currency.value
        elif point.currency.value != currency:
            raise ValueError("Mixed currencies not supported")

        change_pct = 0.0 if start == 0 else (change / start) * 100.0
        item = SignificantChangeItem(
            line_item=point.line_item,
            category=point.category,
            department=point.department,
            period_start_amount=start,
            period_end_amount=end,
            change_amount=change,
            change_percentage=change_pct,
            currency=point.currency.value,
        )
        is_significant = (
            abs(change) >= params.threshold_absolute
            or abs(change_pct) >= params.threshold_percentage
        )
        if is_significant:
            if change >= 0:
                increases.append(item)
            else:
                decreases.append(item)

    increases.sort(key=lambda i: abs(i.change_amount), reverse=True)
    decreases.sort(key=lambda i: abs(i.change_amount), reverse=True)
    increases = increases[: params.top_n]
    decreases = decreases[: params.top_n]

    summary = (
        f"显著增加 {len(increases)} 项，显著减少 {len(decreases)} 项"
        f"（阈值: {params.threshold_absolute:,.0f} 或 {params.threshold_percentage:.0f}%）"
    )
    return SignificantChangeResult(
        significant_increases=increases,
        significant_decreases=decreases,
        summary=summary,
    )
