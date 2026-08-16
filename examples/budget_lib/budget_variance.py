"""EMTB budget variance analysis (period start → period end) — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from .models import (
    BudgetVarianceAnalysisInput,
    BudgetVarianceDetail,
    BudgetVarianceResult,
)
from .utils import resolve_budget_amounts


def analyze_budget_variance(
    params: BudgetVarianceAnalysisInput,
) -> BudgetVarianceResult:
    """Compute period start/end variance for EMTB budget data."""
    if not params.budget_data:
        raise ValueError("budget_data must contain at least one data point")

    details: list[BudgetVarianceDetail] = []
    skipped: list[str] = []
    currency: str | None = None

    for point in params.budget_data:
        start, end, change = resolve_budget_amounts(point)
        if start is None or end is None or change is None:
            skipped.append(point.line_item)
            continue
        if currency is None:
            currency = point.currency.value
        elif point.currency.value != currency:
            raise ValueError("Mixed currencies not supported")

        change_pct = 0.0 if start == 0 else (change / start) * 100.0
        details.append(BudgetVarianceDetail(
            line_item=point.line_item,
            category=point.category,
            department=point.department,
            period_start_amount=start,
            period_end_amount=end,
            change_amount=change,
            change_percentage=change_pct,
            currency=point.currency.value,
        ))

    if not details:
        raise ValueError("No valid EMTB budget rows with start/end/change values")

    total_start = sum(d.period_start_amount for d in details)
    total_end = sum(d.period_end_amount for d in details)
    total_change = sum(d.change_amount for d in details)
    total_pct = 0.0 if total_start == 0 else (total_change / total_start) * 100.0

    return BudgetVarianceResult(
        total_period_start=total_start,
        total_period_end=total_end,
        total_change=total_change,
        change_percentage=total_pct,
        details=details,
        skipped_items=skipped,
        currency=currency or "USD",
    )
