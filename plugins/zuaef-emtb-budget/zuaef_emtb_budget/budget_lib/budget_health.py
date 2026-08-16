"""Budget health check (ADR-008 3-State Model) — 从 zesenticai 保真搬移。"""

from __future__ import annotations

from .budget_consistency import validate_budget_consistency
from .csv_parser import parse_emtb_budget_csv
from .models import (
    BudgetConsistencyInput,
    BudgetHealthFactor,
    BudgetHealthGoal,
    BudgetHealthResult,
    BudgetHealthState,
    EMTBBudgetDataPoint,
)


def _assess_completeness(data: list[EMTBBudgetDataPoint]) -> BudgetHealthFactor:
    total = len(data)
    complete = sum(
        1 for d in data
        if d.period_end_amount and (d.period_start_amount or d.current_period_change)
    )
    rate = complete / total if total else 0.0
    if rate >= 0.95:
        state = BudgetHealthState.HEALTHY
    elif rate >= 0.80:
        state = BudgetHealthState.AT_RISK
    else:
        state = BudgetHealthState.CRITICAL

    return BudgetHealthFactor(
        factor_name="data_completeness",
        factor_state=state,
        description=f"数据完整性: {complete}/{total} 项完整 ({rate:.1%})",
        metric_value=rate,
        threshold=0.95,
    )


def _assess_consistency(data: list[EMTBBudgetDataPoint]) -> BudgetHealthFactor:
    try:
        result = validate_budget_consistency(BudgetConsistencyInput(budget_data=data))
        score = result.summary.health_score
        if score >= 90:
            state = BudgetHealthState.HEALTHY
        elif score >= 70:
            state = BudgetHealthState.AT_RISK
        else:
            state = BudgetHealthState.CRITICAL
        return BudgetHealthFactor(
            factor_name="budget_consistency",
            factor_state=state,
            description=f"预算一致性: {score:.0f}/100, {result.summary.inconsistent_count}/{result.summary.total_items} 项不一致",
            metric_value=score,
            threshold=90.0,
        )
    except Exception as exc:  # noqa: BLE001 — 保真搬移：源库对一致性评估失败同样降级为 CRITICAL
        return BudgetHealthFactor(
            factor_name="budget_consistency",
            factor_state=BudgetHealthState.CRITICAL,
            description=f"预算一致性评估失败: {exc}",
            metric_value=0.0,
            threshold=90.0,
        )


def _assess_variance_magnitude(data: list[EMTBBudgetDataPoint]) -> BudgetHealthFactor:
    threshold_pct = 20.0
    large = 0
    total_with = 0
    for d in data:
        if d.period_start_amount and d.current_period_change and d.period_start_amount != 0:
            total_with += 1
            if abs(d.current_period_change / d.period_start_amount) * 100 > threshold_pct:
                large += 1

    if total_with == 0:
        return BudgetHealthFactor(
            factor_name="variance_magnitude",
            factor_state=BudgetHealthState.AT_RISK,
            description="无有效变动数据",
            metric_value=0.0,
            threshold=threshold_pct,
        )

    ratio = large / total_with
    if ratio <= 0.1:
        state = BudgetHealthState.HEALTHY
    elif ratio <= 0.3:
        state = BudgetHealthState.AT_RISK
    else:
        state = BudgetHealthState.CRITICAL

    return BudgetHealthFactor(
        factor_name="variance_magnitude",
        factor_state=state,
        description=f"变动幅度: {large}/{total_with} 项超过 {threshold_pct}% 阈值 ({ratio:.1%})",
        metric_value=ratio * 100,
        threshold=10.0,
    )


def _overall(factors: list[BudgetHealthFactor]) -> BudgetHealthState:
    if any(f.factor_state == BudgetHealthState.CRITICAL for f in factors):
        return BudgetHealthState.CRITICAL
    if any(f.factor_state == BudgetHealthState.AT_RISK for f in factors):
        return BudgetHealthState.AT_RISK
    return BudgetHealthState.HEALTHY


_STATE_LABEL = {
    BudgetHealthState.HEALTHY: "健康",
    BudgetHealthState.AT_RISK: "风险",
    BudgetHealthState.CRITICAL: "严重",
}
_STATE_ICON = {
    BudgetHealthState.HEALTHY: "✓",
    BudgetHealthState.AT_RISK: "⚠",
    BudgetHealthState.CRITICAL: "✗",
}

_RECOMMENDATIONS = {
    ("data_completeness", BudgetHealthState.CRITICAL): "紧急: 补充缺失的预算数据字段，特别是 period_end_amount",
    ("data_completeness", BudgetHealthState.AT_RISK): "建议: 完善部分预算数据以提高分析准确性",
    ("budget_consistency", BudgetHealthState.CRITICAL): "紧急: 检查并修复预算数据不一致问题 (期初 + 变动 ≠ 期末)",
    ("budget_consistency", BudgetHealthState.AT_RISK): "建议: 检查并修正轻微的预算不一致问题",
    ("variance_magnitude", BudgetHealthState.CRITICAL): "紧急: 审查大幅预算变动的合理性，可能需要更新预算假设",
    ("variance_magnitude", BudgetHealthState.AT_RISK): "建议: 关注预算变动较大的项目，确认业务合理性",
}


def budget_health_check(goal: BudgetHealthGoal) -> BudgetHealthResult:
    """Compute budget health using ADR-008 3-State Model."""
    if goal.budget_data:
        data = goal.budget_data
    elif goal.data_context:
        data, _ = parse_emtb_budget_csv(goal.data_context)
    else:
        raise ValueError("需要 budget_data 或 data_context")

    factors = [
        _assess_completeness(data),
        _assess_consistency(data),
        _assess_variance_magnitude(data),
    ]
    state = _overall(factors)

    summary = f"预算健康状态: {_STATE_LABEL[state]}\n\n"
    for f in factors:
        summary += f"{_STATE_ICON[f.factor_state]} {f.description}\n"

    recs = [
        msg for (fname, fstate), msg in _RECOMMENDATIONS.items()
        if any(f.factor_name == fname and f.factor_state == fstate for f in factors)
    ]
    if state == BudgetHealthState.HEALTHY:
        recs.append("预算数据质量良好，可继续进行深入分析")

    return BudgetHealthResult(
        overall_health_state=state,
        health_factors=factors,
        summary=summary,
        recommendations=recs,
    )
