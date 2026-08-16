"""EMTB period end budget query — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from collections import defaultdict

from .models import (
    BudgetQueryItem,
    BudgetQueryResult,
    QueryPeriodEndBudgetInput,
)
from .utils import normalize_key, resolve_budget_amounts


def _resolve_period_end(params: QueryPeriodEndBudgetInput) -> list[BudgetQueryItem]:
    results: list[BudgetQueryItem] = []
    currency: str | None = None
    for point in params.budget_data:
        _, end, _ = resolve_budget_amounts(point)
        if end is None:
            continue
        if currency is None:
            currency = point.currency.value
        elif point.currency.value != currency:
            raise ValueError("Mixed currencies not supported")
        results.append(BudgetQueryItem(
            line_item=point.line_item,
            category=point.category,
            department=point.department,
            period_end_amount=end,
            currency=point.currency.value,
        ))
    if not results:
        raise ValueError("No period end budget values available")
    return results


def query_period_end_budget(
    params: QueryPeriodEndBudgetInput,
) -> BudgetQueryResult:
    """Query period end budget by line item, category, or department."""
    if not params.budget_data:
        raise ValueError("budget_data must contain at least one data point")

    raw = _resolve_period_end(params)
    qt = params.query_type

    if qt == "single_item":
        if not params.filter_line_item:
            raise ValueError("filter_line_item is required for single_item query")
        target = normalize_key(params.filter_line_item)
        matched = [r for r in raw if normalize_key(r.line_item) == target]
        if not matched:
            raise ValueError("No matching line_item found")
        total = sum(r.period_end_amount for r in matched)
        return BudgetQueryResult(query_type=qt, results=matched, total_amount=total, currency=matched[0].currency)

    if qt == "category_summary":
        target = normalize_key(params.filter_category)
        agg: dict[str, float] = defaultdict(float)
        cur = raw[0].currency
        for r in raw:
            key = normalize_key(r.category) or "uncategorized"
            if target and key != target:
                continue
            agg[key] += r.period_end_amount
        items = [BudgetQueryItem(category=k, period_end_amount=v, currency=cur) for k, v in agg.items()]
        return BudgetQueryResult(query_type=qt, results=items, total_amount=sum(i.period_end_amount for i in items), currency=cur)

    if qt == "department_summary":
        target = normalize_key(params.filter_department)
        agg = defaultdict(float)
        cur = raw[0].currency
        for r in raw:
            key = normalize_key(r.department) or "unassigned"
            if target and key != target:
                continue
            agg[key] += r.period_end_amount
        items = [BudgetQueryItem(department=k, period_end_amount=v, currency=cur) for k, v in agg.items()]
        return BudgetQueryResult(query_type=qt, results=items, total_amount=sum(i.period_end_amount for i in items), currency=cur)

    raise ValueError(f"Unsupported query_type: {qt}")
