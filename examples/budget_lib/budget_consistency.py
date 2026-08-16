"""EMTB budget lifecycle consistency validation — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from .models import (
    BudgetConsistencyFlag,
    BudgetConsistencyInput,
    BudgetConsistencyItem,
    BudgetConsistencyResult,
    BudgetConsistencySummary,
    BudgetRiskLevel,
)
from .utils import resolve_budget_amounts


def _compute_tolerance(base: float, abs_tol: float, pct_tol: float) -> float:
    return max(abs_tol, abs(base) * (pct_tol / 100.0))


def _explanation(flag: BudgetConsistencyFlag, gap: float | None, tolerance: float | None) -> str:
    if flag == BudgetConsistencyFlag.INSUFFICIENT:
        return "字段不足，无法验证预算一致性。"
    if flag == BudgetConsistencyFlag.CONSISTENT:
        return "预算生命周期计算一致。"
    if gap is None or tolerance is None:
        return "预算一致性异常，需复核。"
    return f"预算一致性异常：差异 {gap:,.2f} 超出容差 {tolerance:,.2f}。"


def _score(gap: float | None, tolerance: float) -> float:
    if gap is None:
        return 70.0
    normalized = abs(gap) / max(tolerance, 1.0)
    return max(0.0, min(100.0, 100.0 - min(100.0, normalized * 10.0)))


def validate_budget_consistency(
    params: BudgetConsistencyInput,
) -> BudgetConsistencyResult:
    """Validate EMTB budget lifecycle arithmetic with tolerance rules."""
    if not params.budget_data:
        raise ValueError("budget_data must contain at least one data point")

    items: list[BudgetConsistencyItem] = []

    for point in params.budget_data:
        start = point.period_start_amount
        change = point.current_period_change
        end = point.period_end_amount
        available = [v for v in (start, change, end) if v is not None]

        gap: float | None = None
        pct_gap: float | None = None
        tol = params.tolerance_absolute

        if len(available) < 2:
            flag = BudgetConsistencyFlag.INSUFFICIENT
            risk = BudgetRiskLevel.MEDIUM
        else:
            start_r, end_r, change_r = resolve_budget_amounts(point)
            if start_r is None or end_r is None or change_r is None:
                flag = BudgetConsistencyFlag.INSUFFICIENT
                risk = BudgetRiskLevel.MEDIUM
            elif start is not None and change is not None and end is not None:
                gap = (start + change) - end
                base = end if end != 0 else start + change
                tol = _compute_tolerance(base, params.tolerance_absolute, params.tolerance_percentage)
                pct_gap = 0.0 if base == 0 else (gap / base) * 100.0

                if abs(gap) <= tol:
                    flag = BudgetConsistencyFlag.CONSISTENT
                    risk = BudgetRiskLevel.LOW
                elif change == 0 or abs(gap) > tol * 2:
                    flag = BudgetConsistencyFlag.INCONSISTENT
                    risk = BudgetRiskLevel.HIGH
                else:
                    flag = BudgetConsistencyFlag.INCONSISTENT
                    risk = BudgetRiskLevel.MEDIUM
            else:
                flag = BudgetConsistencyFlag.CONSISTENT
                risk = BudgetRiskLevel.LOW

        items.append(BudgetConsistencyItem(
            line_item=point.line_item,
            category=point.category,
            department=point.department,
            currency=point.currency.value,
            period_start_amount=start,
            current_period_change=change,
            period_end_amount=end,
            expected_period_end=end,
            absolute_gap=gap,
            percentage_gap=pct_gap,
            consistency_flag=flag,
            risk_level=risk,
            explanation=_explanation(flag, gap, tol),
            consistency_score=_score(gap, tol),
        ))

    consistent = sum(1 for i in items if i.consistency_flag == BudgetConsistencyFlag.CONSISTENT)
    inconsistent = sum(1 for i in items if i.consistency_flag == BudgetConsistencyFlag.INCONSISTENT)
    insufficient = sum(1 for i in items if i.consistency_flag == BudgetConsistencyFlag.INSUFFICIENT)

    ranked = sorted(
        [i for i in items if i.consistency_flag == BudgetConsistencyFlag.INCONSISTENT],
        key=lambda i: abs(i.absolute_gap or 0.0),
        reverse=True,
    )

    scores = [i.consistency_score for i in items]
    health = sum(scores) / len(scores) if scores else 0.0

    return BudgetConsistencyResult(
        summary=BudgetConsistencySummary(
            total_items=len(items),
            consistent_count=consistent,
            inconsistent_count=inconsistent,
            insufficient_count=insufficient,
            health_score=health,
            top_inconsistencies=ranked[:5],
        ),
        items=items,
    )
