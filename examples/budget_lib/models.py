"""EMTB 预算域模型 — 从 zesenticai finance_agent/domain/models.py 保真搬移。

保留原文件全部业务模型与校验逻辑；仅去掉框架层冗余（原仓库
"Business logic preserved from finance_agent_v3; framework bloat removed"）。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════

class CurrencyCode(str, Enum):
    USD = "USD"
    EUR = "EUR"
    CNY = "CNY"
    GBP = "GBP"
    JPY = "JPY"


class BudgetDifferenceFlag(str, Enum):
    OVERPERFORM = "OVERPERFORM"
    UNDERPERFORM = "UNDERPERFORM"
    WATCH = "WATCH"
    NORMAL = "NORMAL"


class BudgetConsistencyFlag(str, Enum):
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    INSUFFICIENT = "INSUFFICIENT"


class BudgetRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BudgetHealthState(str, Enum):
    """ADR-008 3-State Model."""
    HEALTHY = "HEALTHY"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════
# Core data points
# ═══════════════════════════════════════════════════════════════════════

class BudgetDifferenceDataPoint(BaseModel):
    """Actual vs budget for a single line item."""
    line_item: str
    actual_amount: float
    budget_amount: float
    currency: CurrencyCode = CurrencyCode.USD
    category: str


class EMTBBudgetDataPoint(BaseModel):
    """EMTB 跨境电商预算数据点 — 支持期初/期末/变动."""
    line_item: str
    category: str
    period_start_amount: float | None = None
    current_period_change: float | None = None
    period_end_amount: float | None = None
    actual_amount: float | None = None
    currency: CurrencyCode = CurrencyCode.USD
    department: str | None = None
    remark: str | None = None

    @model_validator(mode="after")
    def _require_at_least_one_amount(self) -> EMTBBudgetDataPoint:
        if not any([
            self.period_start_amount,
            self.current_period_change,
            self.period_end_amount,
            self.actual_amount,
        ]):
            raise ValueError("至少需要提供一个金额字段")
        return self


# ═══════════════════════════════════════════════════════════════════════
# Command inputs
# ═══════════════════════════════════════════════════════════════════════

class BudgetDifferenceAnalysisParameters(BaseModel):
    difference_threshold_percentage: float = 5.0
    difference_threshold_absolute: float = 10000.0
    include_percentage_analysis: bool = True
    reporting_currency: CurrencyCode = CurrencyCode.USD
    summary_line_keywords: list[str] = Field(
        default_factory=lambda: ["total", "gross profit", "operating income"],
    )


class BudgetDifferenceAnalysisInput(BaseModel):
    analysis_name: str
    reporting_period_start: date
    reporting_period_end: date
    difference_data: list[BudgetDifferenceDataPoint]
    analysis_parameters: BudgetDifferenceAnalysisParameters = Field(
        default_factory=BudgetDifferenceAnalysisParameters,
    )
    business_unit: str | None = None
    cost_center: str | None = None


class BudgetVarianceAnalysisInput(BaseModel):
    budget_data: list[EMTBBudgetDataPoint]


class BudgetConsistencyInput(BaseModel):
    budget_data: list[EMTBBudgetDataPoint]
    tolerance_absolute: float = 1.0
    tolerance_percentage: float = 0.5


class SignificantChangeDetectionInput(BaseModel):
    budget_data: list[EMTBBudgetDataPoint]
    threshold_percentage: float = 20.0
    threshold_absolute: float = 50000.0
    top_n: int = 10


class BudgetSummaryInput(BaseModel):
    budget_data: list[EMTBBudgetDataPoint]
    group_by: list[Literal["category", "department"]] = Field(
        default_factory=lambda: ["category"],
    )
    include_variance: bool = True


class QueryPeriodEndBudgetInput(BaseModel):
    budget_data: list[EMTBBudgetDataPoint]
    query_type: Literal["single_item", "category_summary", "department_summary"]
    filter_line_item: str | None = None
    filter_category: str | None = None
    filter_department: str | None = None


# ═══════════════════════════════════════════════════════════════════════
# Command outputs
# ═══════════════════════════════════════════════════════════════════════

class BudgetDifferenceDetail(BaseModel):
    line_item: str
    category: str
    actual_amount: float
    budget_amount: float
    difference_amount: float
    difference_percentage: float
    difference_flag: BudgetDifferenceFlag = BudgetDifferenceFlag.NORMAL
    currency: str


class BudgetDifferenceSummary(BaseModel):
    total_actual: float
    total_budget: float
    total_difference_amount: float
    total_difference_percentage: float
    favorable_count: int
    unfavorable_count: int
    significant_count: int
    currency: str


class BudgetDifferenceBreakdown(BaseModel):
    revenue: list[BudgetDifferenceDetail] = Field(default_factory=list)
    cogs: list[BudgetDifferenceDetail] = Field(default_factory=list)
    opex: list[BudgetDifferenceDetail] = Field(default_factory=list)
    other: list[BudgetDifferenceDetail] = Field(default_factory=list)


class BudgetDifferenceResult(BaseModel):
    analysis_id: str
    summary: BudgetDifferenceSummary
    details: list[BudgetDifferenceDetail]
    significant: list[BudgetDifferenceDetail]
    breakdown: BudgetDifferenceBreakdown
    insight_notes: list[str]
    reporting_period_start: date
    reporting_period_end: date
    business_unit: str | None = None
    cost_center: str | None = None


class BudgetVarianceDetail(BaseModel):
    line_item: str
    category: str
    department: str | None = None
    period_start_amount: float
    period_end_amount: float
    change_amount: float
    change_percentage: float
    currency: str


class BudgetVarianceResult(BaseModel):
    total_period_start: float
    total_period_end: float
    total_change: float
    change_percentage: float
    details: list[BudgetVarianceDetail]
    skipped_items: list[str]
    currency: str


class BudgetConsistencyItem(BaseModel):
    line_item: str
    category: str
    department: str | None = None
    currency: str
    period_start_amount: float | None = None
    current_period_change: float | None = None
    period_end_amount: float | None = None
    expected_period_end: float | None = None
    absolute_gap: float | None = None
    percentage_gap: float | None = None
    consistency_flag: BudgetConsistencyFlag
    risk_level: BudgetRiskLevel
    explanation: str | None = None
    consistency_score: float = 100.0


class BudgetConsistencySummary(BaseModel):
    total_items: int
    consistent_count: int
    inconsistent_count: int
    insufficient_count: int
    health_score: float
    top_inconsistencies: list[BudgetConsistencyItem] = Field(default_factory=list)


class BudgetConsistencyResult(BaseModel):
    summary: BudgetConsistencySummary
    items: list[BudgetConsistencyItem]


class SignificantChangeItem(BaseModel):
    line_item: str
    category: str
    department: str | None = None
    period_start_amount: float
    period_end_amount: float
    change_amount: float
    change_percentage: float
    currency: str


class SignificantChangeResult(BaseModel):
    significant_increases: list[SignificantChangeItem]
    significant_decreases: list[SignificantChangeItem]
    summary: str


class CategorySummary(BaseModel):
    category: str
    period_start_amount: float
    period_end_amount: float
    change_amount: float
    change_percentage: float


class DepartmentSummary(BaseModel):
    department: str
    period_start_amount: float
    period_end_amount: float
    change_amount: float
    change_percentage: float


class BudgetSummaryResult(BaseModel):
    total_period_start: float
    total_period_end: float
    total_change: float
    change_percentage: float
    by_category: list[CategorySummary] | None = None
    by_department: list[DepartmentSummary] | None = None
    currency: str


class BudgetQueryItem(BaseModel):
    line_item: str | None = None
    category: str | None = None
    department: str | None = None
    period_end_amount: float
    currency: str


class BudgetQueryResult(BaseModel):
    query_type: str
    results: list[BudgetQueryItem]
    total_amount: float
    currency: str


# ═══════════════════════════════════════════════════════════════════════
# Health assessment
# ═══════════════════════════════════════════════════════════════════════

class BudgetHealthFactor(BaseModel):
    factor_name: str
    factor_state: BudgetHealthState
    description: str
    metric_value: float | None = None
    threshold: float | None = None


class BudgetHealthResult(BaseModel):
    overall_health_state: BudgetHealthState
    health_factors: list[BudgetHealthFactor]
    summary: str
    recommendations: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


# ═══════════════════════════════════════════════════════════════════════
# Goal models (skill-level inputs)
# ═══════════════════════════════════════════════════════════════════════

class BudgetHealthGoal(BaseModel):
    """Goal for budget health check."""
    model_config = {"extra": "ignore"}

    goal: str = Field(default="预算健康检查", description="分析目标")
    data_context: str | None = None
    budget_data: list[EMTBBudgetDataPoint] | None = None


def model_dump_json(model: BaseModel) -> str:
    """Explicit JSON serialization helper for tool returns (v1.2 receipt-safe)."""
    return model.model_dump_json()
