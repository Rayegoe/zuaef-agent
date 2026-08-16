"""EMTB 跨境电商预算分析库 — 从 zesenticai finance_agent 拆解的业务资产。

纯确定性计算，零 agent / LLM 依赖，可独立测试。
来源: zesenticai_final/backend/src/agents/finance_agent
（domain/models.py + commands/*，逻辑保真搬移，仅改导入路径）

对外入口:
    parse_emtb_budget_csv       — 中英双语列名 CSV 解析
    generate_budget_summary     — 按 category/department 汇总
    analyze_budget_variance     — 期初→期末变动分析
    validate_budget_consistency — 预算生命周期一致性校验
    query_period_end_budget     — 期末预算查询
    budget_health_check         — ADR-008 三态健康检查
    detect_significant_changes  — 显著变动检测
"""

from __future__ import annotations

from .budget_consistency import validate_budget_consistency
from .budget_health import budget_health_check
from .budget_query import query_period_end_budget
from .budget_summary import generate_budget_summary
from .budget_variance import analyze_budget_variance
from .csv_parser import parse_emtb_budget_csv
from .models import (
    BudgetConsistencyFlag,
    BudgetDifferenceFlag,
    BudgetHealthState,
    BudgetRiskLevel,
    CurrencyCode,
    EMTBBudgetDataPoint,
)
from .significant_changes import detect_significant_changes

__all__ = [
    "BudgetConsistencyFlag",
    "BudgetDifferenceFlag",
    "BudgetHealthState",
    "BudgetRiskLevel",
    "CurrencyCode",
    "EMTBBudgetDataPoint",
    "analyze_budget_variance",
    "budget_health_check",
    "detect_significant_changes",
    "generate_budget_summary",
    "parse_emtb_budget_csv",
    "query_period_end_budget",
    "validate_budget_consistency",
]
