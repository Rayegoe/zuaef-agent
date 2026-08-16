"""EMTB 预算 CSV 解析 — 从 zesenticai finance_agent/commands/csv_parser.py 保真搬移。

中英双语列名别名映射，容忍空白/千分位/未知列。
"""

from __future__ import annotations

import csv
from io import StringIO

from .models import CurrencyCode, EMTBBudgetDataPoint

_ALIAS_MAP = {
    # line_item
    "line_item": "line_item", "item": "line_item", "name": "line_item",
    "description": "line_item", "科目": "line_item", "项目": "line_item",
    "项目名称": "line_item", "费用项": "line_item", "明细": "line_item",
    # category
    "category": "category", "cat": "category", "type": "category",
    "分类": "category", "类别": "category",
    # budget amounts
    "period_start_amount": "period_start_amount", "期初预算": "period_start_amount",
    "budget": "period_start_amount", "period_start": "period_start_amount",
    "current_period_change": "current_period_change", "本期变动": "current_period_change",
    "本期增减": "current_period_change", "调整额": "current_period_change",
    "change": "current_period_change", "adjustment": "current_period_change",
    "period_end_amount": "period_end_amount", "期末预算": "period_end_amount",
    "期末余额": "period_end_amount", "调整后预算": "period_end_amount",
    "period_end": "period_end_amount", "ending_budget": "period_end_amount",
    # actual
    "actual_amount": "actual_amount", "actual": "actual_amount",
    "实际": "actual_amount", "实际金额": "actual_amount",
    # metadata
    "currency": "currency", "curr": "currency", "币种": "currency",
    "department": "department", "dept": "department", "部门": "department",
    "division": "department",
    "remark": "remark", "备注": "remark",
}


def _map_headers(headers: list[str]) -> tuple[dict[str, str], list[str]]:
    mapped: dict[str, str] = {}
    observed: list[str] = []
    for h in headers:
        key = (h or "").strip().lower()
        if key and key in _ALIAS_MAP:
            mapped[key] = _ALIAS_MAP[key]
            observed.append(_ALIAS_MAP[key])
    return mapped, observed


def _float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def parse_emtb_budget_csv(
    data_context: str,
) -> tuple[list[EMTBBudgetDataPoint], list[str]]:
    """Parse EMTB budget CSV into structured data points.

    Returns (points, missing_required_columns). Raises ValueError when the
    CSV yields no data points, or on unsupported currency.
    """
    if not data_context or not data_context.strip():
        raise ValueError("data_context must provide CSV content.")

    reader = csv.DictReader(StringIO(data_context.strip()))
    header_map, observed = _map_headers(reader.fieldnames or [])
    missing = sorted({"line_item", "category"} - set(observed))

    points: list[EMTBBudgetDataPoint] = []
    for row in reader:
        norm: dict[str, str | None] = {}
        for h, v in row.items():
            k = (h or "").strip().lower()
            if k in header_map:
                norm[header_map[k]] = v

        cur_raw = (norm.get("currency") or "USD").strip().upper()
        try:
            cur = CurrencyCode(cur_raw)
        except ValueError as exc:
            raise ValueError(f"Unsupported currency: {cur_raw}") from exc

        points.append(EMTBBudgetDataPoint(
            line_item=(norm.get("line_item") or "UNKNOWN").strip(),
            category=(norm.get("category") or "UNKNOWN").strip(),
            period_start_amount=_float(norm.get("period_start_amount")),
            current_period_change=_float(norm.get("current_period_change")),
            period_end_amount=_float(norm.get("period_end_amount")),
            actual_amount=_float(norm.get("actual_amount")),
            currency=cur,
            department=norm.get("department"),
            remark=norm.get("remark"),
        ))

    if not points:
        raise ValueError("CSV did not yield any EMTB budget data points.")
    return points, missing
