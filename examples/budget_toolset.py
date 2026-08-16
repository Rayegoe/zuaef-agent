"""Thin ZUAEF adapter over the EMTB budget analysis library.

``budget_lib`` owns all deterministic computation (bilingual CSV parsing,
summary/variance/consistency/health/query/significant-change). This module
only adapts it to a PydanticAI ``FunctionToolset`` so one core agent can
exercise the business domain through the shared ``build_agent`` seam.

Effect classes:
  parse_budget_csv / summary / variance / consistency / health / query /
  significant_changes   observe (automatic)
  save_budget_report    local_write (automatic) — writes only under the
                        ZUAEF workspace artifacts dir for THIS run.

Run isolation: no durable ledger is needed here — all analysis is derived
from the run's own CSV input and output is bounded. The host verifies
artifact ownership by SHA-256 snapshot, exactly like the writing slice.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic_ai import FunctionToolset, RunContext

from examples.budget_lib import (
    EMTBBudgetDataPoint,
    analyze_budget_variance,
    budget_health_check,
    detect_significant_changes,
    generate_budget_summary,
    parse_emtb_budget_csv,
    query_period_end_budget,
    validate_budget_consistency,
)
from examples.budget_lib.models import (
    BudgetConsistencyInput,
    BudgetHealthGoal,
    BudgetSummaryInput,
    BudgetVarianceAnalysisInput,
    QueryPeriodEndBudgetInput,
    SignificantChangeDetectionInput,
)
from zuaef_agent.models import CoreDeps

BUDGET_RULES = (
    "EMTB 预算分析工具集。先用 parse_budget_csv 把 CSV 解析为结构化数据点，"
    "再用 summary/variance/consistency/health/query/significant_changes 做确定性分析。"
    "所有金额计算由库内确定性算法完成，不要手算或估算。"
    "预算健康检查基于 ADR-008 三态模型（健康/风险/严重）。"
    "最终用 save_budget_report 把报告写入 artifact，并在 RunSummary.artifacts "
    "中声明 artifact:<相对路径>。"
)


def _points(data: Any) -> list[EMTBBudgetDataPoint]:
    """Coerce tool-inbound JSON list to EMTB data points."""
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, list) or not data:
        raise ValueError("budget data must be a non-empty JSON array")
    return [EMTBBudgetDataPoint.model_validate(row) for row in data]


def _bounded(payload: dict | list, limit: int = 40000) -> str:
    """Serialize JSON, hard-truncated so oversized analysis never floods context."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def build_budget_toolset() -> FunctionToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(instructions=BUDGET_RULES)

    @toolset.tool
    def parse_budget_csv(ctx: RunContext[CoreDeps], csv_text: str) -> str:
        """Parse an EMTB budget CSV (English or Chinese column headers) into data points.

        Returns JSON: {count, currency, missing_columns, points}. Use the returned
        points array as the `data` argument of the analysis tools.
        """
        try:
            points, missing = parse_emtb_budget_csv(csv_text)
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        currencies = {p.currency.value for p in points}
        return _bounded({
            "ok": True,
            "count": len(points),
            "currency": sorted(currencies),
            "missing_required_columns": missing,
            "points": [p.model_dump(mode="json") for p in points],
        })

    @toolset.tool
    def budget_summary(
        ctx: RunContext[CoreDeps],
        data: Any,
        group_by: list[str] | None = None,
    ) -> str:
        """Aggregate budget data by category and/or department (period start→end)."""
        try:
            result = generate_budget_summary(BudgetSummaryInput(
                budget_data=_points(data),
                group_by=group_by or ["category"],
            ))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def budget_variance(ctx: RunContext[CoreDeps], data: Any) -> str:
        """Compute period start→end variance for every line item."""
        try:
            result = analyze_budget_variance(BudgetVarianceAnalysisInput(
                budget_data=_points(data),
            ))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def budget_consistency(
        ctx: RunContext[CoreDeps],
        data: Any,
        tolerance_absolute: float = 1.0,
        tolerance_percentage: float = 0.5,
    ) -> str:
        """Validate lifecycle arithmetic (period_start + change ≈ period_end) per item."""
        try:
            result = validate_budget_consistency(BudgetConsistencyInput(
                budget_data=_points(data),
                tolerance_absolute=tolerance_absolute,
                tolerance_percentage=tolerance_percentage,
            ))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def budget_query(
        ctx: RunContext[CoreDeps],
        data: Any,
        query_type: str,
        filter_line_item: str | None = None,
        filter_category: str | None = None,
        filter_department: str | None = None,
    ) -> str:
        """Query period-end budget: single_item | category_summary | department_summary."""
        try:
            result = query_period_end_budget(QueryPeriodEndBudgetInput(
                budget_data=_points(data),
                query_type=query_type,
                filter_line_item=filter_line_item,
                filter_category=filter_category,
                filter_department=filter_department,
            ))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def budget_health(ctx: RunContext[CoreDeps], data: Any) -> str:
        """ADR-008 three-state budget health check (HEALTHY / AT_RISK / CRITICAL)."""
        try:
            result = budget_health_check(BudgetHealthGoal(budget_data=_points(data)))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def significant_changes(
        ctx: RunContext[CoreDeps],
        data: Any,
        threshold_percentage: float = 20.0,
        threshold_absolute: float = 50000.0,
        top_n: int = 10,
    ) -> str:
        """Detect line items whose change exceeds percentage or absolute thresholds."""
        try:
            result = detect_significant_changes(SignificantChangeDetectionInput(
                budget_data=_points(data),
                threshold_percentage=threshold_percentage,
                threshold_absolute=threshold_absolute,
                top_n=top_n,
            ))
        except ValueError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        return _bounded(result.model_dump(mode="json"))

    @toolset.tool
    def save_budget_report(
        ctx: RunContext[CoreDeps],
        report_markdown: str,
        csv_name: str = "emtb_budget",
    ) -> dict:
        """Write the final budget analysis report as a run artifact (local write).

        Returns {snapshot_rel_path, sha256}. Declare the same
        artifact:<rel_path> in RunSummary.artifacts; the host verifies it."""
        snapshot_dir = ctx.deps.workspace_root / "artifacts" / ctx.deps.run_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c for c in csv_name if c.isalnum() or c in "._-") or "report"
        snapshot = snapshot_dir / f"{safe_name}-report.md"
        snapshot.write_text(report_markdown, encoding="utf-8")
        return {
            "snapshot_rel_path": snapshot.relative_to(ctx.deps.workspace_root).as_posix(),
            "sha256": hashlib.sha256(
                report_markdown.encode("utf-8")
            ).hexdigest(),
        }

    return toolset
