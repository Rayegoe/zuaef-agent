"""Deterministic budget difference analysis (actual vs budget) — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from datetime import UTC, datetime

from .models import (
    BudgetDifferenceAnalysisInput,
    BudgetDifferenceBreakdown,
    BudgetDifferenceDataPoint,
    BudgetDifferenceDetail,
    BudgetDifferenceFlag,
    BudgetDifferenceResult,
    BudgetDifferenceSummary,
)


def _to_detail(point: BudgetDifferenceDataPoint) -> BudgetDifferenceDetail:
    diff = point.actual_amount - point.budget_amount
    pct = 0.0 if point.budget_amount == 0 else (diff / point.budget_amount) * 100.0
    return BudgetDifferenceDetail(
        line_item=point.line_item,
        category=point.category,
        actual_amount=point.actual_amount,
        budget_amount=point.budget_amount,
        difference_amount=diff,
        difference_percentage=pct,
        currency=point.currency.value,
    )


def _categorize(details: list[BudgetDifferenceDetail]) -> BudgetDifferenceBreakdown:
    breakdown = BudgetDifferenceBreakdown()
    for d in details:
        cat = (d.category or "").strip().lower()
        if cat == "revenue":
            breakdown.revenue.append(d)
        elif cat in {"cogs", "cost of goods sold"}:
            breakdown.cogs.append(d)
        elif cat in {"operating expenses", "opex", "operating expense"}:
            breakdown.opex.append(d)
        else:
            breakdown.other.append(d)
    return breakdown


def _flag_significant(
    details: list[BudgetDifferenceDetail],
    threshold_pct: float,
    threshold_abs: float,
) -> tuple[list[BudgetDifferenceDetail], list[BudgetDifferenceDetail]]:
    significant: list[BudgetDifferenceDetail] = []
    watchlist: list[BudgetDifferenceDetail] = []
    for d in details:
        abs_pct = abs(d.difference_percentage)
        abs_amt = abs(d.difference_amount)
        if abs_pct >= threshold_pct or abs_amt >= threshold_abs:
            d.difference_flag = (
                BudgetDifferenceFlag.OVERPERFORM
                if d.difference_amount >= 0
                else BudgetDifferenceFlag.UNDERPERFORM
            )
            significant.append(d)
        elif abs_pct >= threshold_pct * 0.5 or abs_amt >= threshold_abs * 0.5:
            d.difference_flag = BudgetDifferenceFlag.WATCH
            watchlist.append(d)
    return significant, watchlist


def budget_difference_analysis(
    params: BudgetDifferenceAnalysisInput,
) -> BudgetDifferenceResult:
    """Deterministic budget difference analysis pipeline."""
    if params.reporting_period_start > params.reporting_period_end:
        raise ValueError("reporting_period_start must be <= reporting_period_end")
    if not params.difference_data:
        raise ValueError("difference_data must contain at least one data point")

    # Filter out summary roll-up rows
    keywords = [k.strip().lower() for k in (params.analysis_parameters.summary_line_keywords or []) if k.strip()]
    filtered = [
        p for p in params.difference_data
        if not any(k in (p.line_item or "").strip().lower() for k in keywords)
    ] if keywords else list(params.difference_data)
    if not filtered:
        raise ValueError("All rows classified as summary lines; provide detail rows.")

    details = [_to_detail(p) for p in filtered]
    breakdown = _categorize(details)

    # Summarize
    total_actual = sum(d.actual_amount for d in details)
    total_budget = sum(d.budget_amount for d in details)
    total_diff = total_actual - total_budget
    total_pct = 0.0 if total_budget == 0 else (total_diff / total_budget) * 100.0
    favorable = sum(1 for d in details if d.difference_amount >= 0)

    # Flag significance
    significant, _ = _flag_significant(
        details,
        params.analysis_parameters.difference_threshold_percentage,
        params.analysis_parameters.difference_threshold_absolute,
    )

    currency = params.analysis_parameters.reporting_currency.value
    summary = BudgetDifferenceSummary(
        total_actual=total_actual,
        total_budget=total_budget,
        total_difference_amount=total_diff,
        total_difference_percentage=total_pct,
        favorable_count=favorable,
        unfavorable_count=len(details) - favorable,
        significant_count=len(significant),
        currency=currency,
    )

    # Insights
    insight_notes = [
        f"Total budget difference is {total_diff:.2f} {currency} ({total_pct:.2f}%)."
    ]
    if significant:
        top = max(significant, key=lambda d: abs(d.difference_amount))
        insight_notes.append(
            f"Top driver: {top.category} - {top.line_item} "
            f"{top.difference_amount:.2f} {top.currency} ({top.difference_percentage:.2f}%)."
        )
    else:
        insight_notes.append("No significant differences under current thresholds.")

    return BudgetDifferenceResult(
        analysis_id=f"budget-diff-{int(datetime.now(UTC).timestamp())}",
        summary=summary,
        details=details,
        significant=significant,
        breakdown=breakdown,
        insight_notes=insight_notes,
        reporting_period_start=params.reporting_period_start,
        reporting_period_end=params.reporting_period_end,
        business_unit=params.business_unit,
        cost_center=params.cost_center,
    )
