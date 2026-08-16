"""Generate EMTB budget summary aggregates — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from collections import defaultdict

from .models import (
    BudgetSummaryInput,
    BudgetSummaryResult,
    CategorySummary,
    DepartmentSummary,
)
from .utils import normalize_key, resolve_budget_amounts


def generate_budget_summary(
    params: BudgetSummaryInput,
) -> BudgetSummaryResult:
    """Aggregate EMTB budget data by category/department."""
    if not params.budget_data:
        raise ValueError("budget_data must contain at least one data point")

    currency: str | None = None
    total_start = 0.0
    total_end = 0.0
    cat_totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    dept_totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])

    for point in params.budget_data:
        start, end, _ = resolve_budget_amounts(point)
        if start is None or end is None:
            continue
        if currency is None:
            currency = point.currency.value
        elif point.currency.value != currency:
            raise ValueError("Mixed currencies not supported")
        total_start += start
        total_end += end

        if "category" in params.group_by:
            key = normalize_key(point.category) or "uncategorized"
            cat_totals[key][0] += start
            cat_totals[key][1] += end

        if "department" in params.group_by:
            key = normalize_key(point.department) or "unassigned"
            dept_totals[key][0] += start
            dept_totals[key][1] += end

    if currency is None:
        raise ValueError("No valid budget rows with start/end values")

    total_change = total_end - total_start if params.include_variance else 0.0
    total_pct = (0.0 if total_start == 0 else (total_change / total_start) * 100.0) if params.include_variance else 0.0

    by_category = None
    if "category" in params.group_by:
        by_category = []
        for key, (s, e) in cat_totals.items():
            chg = (e - s) if params.include_variance else 0.0
            pct = (0.0 if s == 0 else (chg / s) * 100.0) if params.include_variance else 0.0
            by_category.append(CategorySummary(
                category=key, period_start_amount=s, period_end_amount=e,
                change_amount=chg, change_percentage=pct,
            ))

    by_department = None
    if "department" in params.group_by:
        by_department = []
        for key, (s, e) in dept_totals.items():
            chg = (e - s) if params.include_variance else 0.0
            pct = (0.0 if s == 0 else (chg / s) * 100.0) if params.include_variance else 0.0
            by_department.append(DepartmentSummary(
                department=key, period_start_amount=s, period_end_amount=e,
                change_amount=chg, change_percentage=pct,
            ))

    return BudgetSummaryResult(
        total_period_start=total_start,
        total_period_end=total_end,
        total_change=total_change,
        change_percentage=total_pct,
        by_category=by_category,
        by_department=by_department,
        currency=currency,
    )
