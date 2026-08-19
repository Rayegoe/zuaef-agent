"""Deterministic branches of the EMTB budget slice (Stage 6A plugin).

budget_lib is a faithful extraction of zesenticai finance_agent commands; these
tests pin the extraction to the original behavior on the real sample CSV
(Chinese + English headers). Real-model execution is exercised by
``examples/budget_case.py`` itself, never faked with TestModel — but the plugin
composition seam IS driven here with FunctionModel so the shared execution
path stays covered in CI without network or credentials.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Any, cast

from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zuaef_emtb_budget import create_plugin
from zuaef_emtb_budget import plugin as plugin_module
from zuaef_emtb_budget.budget_lib import (
    EMTBBudgetDataPoint,
    analyze_budget_variance,
    budget_health_check,
    detect_significant_changes,
    generate_budget_summary,
    parse_emtb_budget_csv,
    query_period_end_budget,
    validate_budget_consistency,
)
from zuaef_emtb_budget.budget_lib.models import (
    BudgetConsistencyInput,
    BudgetHealthGoal,
    BudgetSummaryInput,
    BudgetVarianceAnalysisInput,
    QueryPeriodEndBudgetInput,
    SignificantChangeDetectionInput,
)
from zuaef_emtb_budget.toolset import build_budget_toolset

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import PluginBundle, PluginEnv
from zuaef_agent.runtime import TerminalRun, execute_run
from zuaef_agent.verification import sha256_file

SAMPLE = (
    PROJECT_ROOT
    / "plugins"
    / "zuaef-emtb-budget"
    / "zuaef_emtb_budget"
    / "data"
    / "emtb_budget_sample.csv"
)

ENGLISH_CSV = """\
line_item,category,period_start_amount,current_period_change,period_end_amount,actual_amount,currency,department
ad spend,revenue,50000,15000,65000,62000,USD,NA
warehousing,cogs,30000,-5000,25000,25500,USD,NA
"""


def _points() -> list[EMTBBudgetDataPoint]:
    text = SAMPLE.read_text(encoding="utf-8")
    points, missing = parse_emtb_budget_csv(text)
    assert not missing, f"required columns missing: {missing}"
    return points


def _json_points() -> list[dict]:
    return [p.model_dump(mode="json") for p in _points()]


def _invoke_tool(tool: object, args: dict[str, Any], ctx: Any) -> Any:
    fn = cast(Any, tool).function
    return fn(ctx, **args)


class TestBudgetLib(unittest.TestCase):
    """Pinned extraction behavior over the real sample CSV."""

    def setUp(self) -> None:
        self.points = _points()

    def test_bilingual_csv_parses_all_rows(self) -> None:
        self.assertEqual(len(self.points), 10)
        first = self.points[0]
        self.assertEqual(first.line_item, "广告投放")
        self.assertEqual(first.category, "revenue")
        self.assertEqual(first.period_start_amount, 50000.0)
        self.assertEqual(first.period_end_amount, 65000.0)
        self.assertEqual(first.actual_amount, 62000.0)
        self.assertEqual(first.currency.value, "USD")
        self.assertEqual(first.department, "北美")

    def test_english_headers_parse(self) -> None:
        points, missing = parse_emtb_budget_csv(ENGLISH_CSV)
        self.assertEqual(len(points), 2)
        self.assertEqual(missing, [])
        self.assertEqual(points[1].line_item, "warehousing")
        self.assertEqual(points[1].current_period_change, -5000.0)

    def test_empty_amount_row_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EMTBBudgetDataPoint(
                line_item="x", category="y", currency="USD",
            )

    def test_missing_required_columns_reported(self) -> None:
        points, missing = parse_emtb_budget_csv(
            "科目,期初预算,本期变动\n广告,100,20\n"
        )
        self.assertEqual(missing, ["category"])
        self.assertEqual(points[0].line_item, "广告")
        self.assertEqual(points[0].category, "UNKNOWN")

    def test_unsupported_currency_rejected(self) -> None:
        bad = "科目,分类,期初预算,币种\n广告,revenue,100,XXX\n"
        with self.assertRaises(ValueError):
            parse_emtb_budget_csv(bad)

    def test_summary_totals(self) -> None:
        result = generate_budget_summary(BudgetSummaryInput(budget_data=self.points))
        self.assertAlmostEqual(result.total_period_start, 161000.0, places=2)
        self.assertAlmostEqual(result.total_period_end, 175800.0, places=2)
        self.assertAlmostEqual(result.total_change, 14800.0, places=2)
        cats = {c.category: c for c in result.by_category or []}
        self.assertAlmostEqual(cats["revenue"].period_end_amount, 83000.0, places=2)
        self.assertAlmostEqual(cats["opex"].period_end_amount, 48500.0, places=2)

    def test_variance_skips_nothing_and_totals(self) -> None:
        result = analyze_budget_variance(BudgetVarianceAnalysisInput(budget_data=self.points))
        self.assertEqual(result.skipped_items, [])
        # variance sums the change FIELD (14300), so the inconsistent row's
        # 500 gap (8000+4000=12000 vs declared 12500) is NOT swept in —
        # summary (end-start, 14800) is the number that exposes it.
        self.assertAlmostEqual(result.total_change, 14300.0, places=2)
        self.assertAlmostEqual(
            result.total_change + 500.0, 14800.0, places=2
        )

    def test_consistency_flags_software_subscription(self) -> None:
        result = validate_budget_consistency(BudgetConsistencyInput(budget_data=self.points))
        inconsistent = [
            i.line_item
            for i in result.items
            if i.consistency_flag.value == "INCONSISTENT"
        ]
        self.assertEqual(inconsistent, ["软件订阅"])
        self.assertEqual(result.summary.consistent_count, 9)
        self.assertEqual(result.summary.inconsistent_count, 1)

    def test_query_single_item(self) -> None:
        result = query_period_end_budget(QueryPeriodEndBudgetInput(
            budget_data=self.points,
            query_type="single_item",
            filter_line_item="广告投放",
        ))
        self.assertAlmostEqual(result.total_amount, 65000.0, places=2)

    def test_query_category_summary(self) -> None:
        result = query_period_end_budget(QueryPeriodEndBudgetInput(
            budget_data=self.points,
            query_type="category_summary",
        ))
        by_cat = {r.category: r.period_end_amount for r in result.results}
        self.assertAlmostEqual(by_cat["revenue"], 83000.0, places=2)
        self.assertAlmostEqual(by_cat["cogs"], 37000.0, places=2)

    def test_significant_changes(self) -> None:
        result = detect_significant_changes(SignificantChangeDetectionInput(
            budget_data=self.points,
            threshold_percentage=20.0,
            threshold_absolute=50000.0,
        ))
        self.assertEqual(len(result.significant_increases), 4)
        self.assertEqual(len(result.significant_decreases), 1)
        names = {i.line_item for i in result.significant_increases}
        self.assertEqual(names, {"广告投放", "平台佣金", "软件订阅", "样品采购"})
        self.assertEqual(result.significant_decreases[0].line_item, "市场调研")

    def test_health_is_critical(self) -> None:
        result = budget_health_check(BudgetHealthGoal(budget_data=self.points))
        self.assertEqual(result.overall_health_state.value, "CRITICAL")
        factors = {f.factor_name: f.factor_state.value for f in result.health_factors}
        self.assertEqual(factors["data_completeness"], "HEALTHY")
        self.assertEqual(factors["budget_consistency"], "HEALTHY")
        self.assertEqual(factors["variance_magnitude"], "CRITICAL")


class TestBudgetToolset(unittest.TestCase):
    """Toolset functions called directly through a TestModel context."""

    def setUp(self) -> None:
        self.toolset = build_budget_toolset()
        self.by_name = self.toolset.tools
        self.run_id = uuid.uuid4().hex
        self.tmp = Path(tempfile.mkdtemp(prefix="budget-toolset-"))
        self.workspace = self.tmp / "workspace"
        self.workspace.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ctx(self) -> RunContext[CoreDeps]:
        deps = CoreDeps(workspace_root=self.workspace, run_id=self.run_id)
        return RunContext[CoreDeps](
            deps=deps, model=TestModel(), usage=RunUsage(),
        )

    def test_parse_tool_returns_points(self) -> None:
        out = _invoke_tool(
            self.by_name["parse_budget_csv"],
            {"csv_text": SAMPLE.read_text(encoding="utf-8")},
            self._ctx(),
        )
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 10)
        self.assertEqual(payload["points"][0]["line_item"], "广告投放")

    def test_health_tool_reports_critical(self) -> None:
        out = _invoke_tool(
            self.by_name["budget_health"],
            {"data": _json_points()},
            self._ctx(),
        )
        payload = json.loads(out)
        self.assertEqual(payload["overall_health_state"], "CRITICAL")

    def test_consistency_tool_flags_item(self) -> None:
        out = _invoke_tool(
            self.by_name["budget_consistency"],
            {"data": _json_points()},
            self._ctx(),
        )
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["inconsistent_count"], 1)

    def test_save_report_writes_artifact(self) -> None:
        ctx = self._ctx()
        out = _invoke_tool(
            self.by_name["save_budget_report"],
            {"report_markdown": "# 报告\n\n健康度 CRITICAL", "csv_name": "emtb_budget"},
            ctx,
        )
        rel = out["snapshot_rel_path"]
        self.assertEqual(rel, f"artifacts/{self.run_id}/emtb_budget-report.md")
        target = self.workspace / rel
        self.assertTrue(target.is_file())
        self.assertEqual(out["sha256"], sha256_file(target))

    def test_invalid_data_returns_ok_false(self) -> None:
        out = _invoke_tool(
            self.by_name["budget_summary"],
            {"data": "not-json"},
            self._ctx(),
        )
        payload = json.loads(out)
        self.assertFalse(payload["ok"])


class TestCompositionSeam(unittest.TestCase):
    """build_agent(extra_toolsets=[...]) driven through execute_run with FunctionModel."""

    def test_budget_toolset_runs_through_shared_seam(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            workspace = tmp / "workspace"
            workspace.mkdir(exist_ok=True)
            settings = AgentSettings(
                model="test",
                workspace_root=workspace,
                runtime_state_root=tmp / ".zuaef-state",
                enable_planning=False,
                enable_skills=False,
            )
            run_id = uuid.uuid4().hex
            agent = build_agent(
                settings, run_id=run_id, extra_toolsets=[build_budget_toolset()]
            )
            deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

            calls: list[str] = []

            def fn(messages, info):
                has_return = any(
                    getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
                    for message in messages
                    for part in getattr(message, "parts", [])
                )
                if not has_return:
                    calls.append("parse")
                    return ModelResponse(parts=[
                        ToolCallPart("parse_budget_csv", {"csv_text": SAMPLE.read_text(encoding="utf-8")})
                    ])
                if "health" not in calls:
                    calls.append("health")
                    return ModelResponse(parts=[
                        ToolCallPart("budget_health", {"data": _json_points()})
                    ])
                if "save" not in calls:
                    calls.append("save")
                    return ModelResponse(parts=[
                        ToolCallPart("save_budget_report", {
                            "report_markdown": "# EMTB 预算报告\n\n健康度: CRITICAL",
                            "csv_name": "emtb_budget",
                        })
                    ])
                return ModelResponse(parts=[TextPart(content="预算分析完成，健康度 CRITICAL")])

            with agent.override(model=FunctionModel(fn)):
                outcome = execute_run(
                    agent, deps,
                    prompt="分析预算 CSV",
                    settings=settings,
                    run_id=run_id,
                )

            self.assertIsInstance(outcome, TerminalRun)
            self.assertEqual(outcome.summary.status, "completed")
            self.assertEqual(calls, ["parse", "health", "save"])
            report = workspace / "artifacts" / run_id / "emtb_budget-report.md"
            self.assertTrue(report.is_file())
            self.assertEqual(
                outcome.receipt.verified_artifacts[0].path,
                f"artifacts/{run_id}/emtb_budget-report.md",
            )
            self.assertEqual(
                outcome.receipt.verified_artifacts[0].sha256,
                sha256_file(report),
            )
            effect_names = [e.tool_name for e in outcome.receipt.verified_tool_effects]
            self.assertIn("parse_budget_csv", effect_names)
            self.assertIn("save_budget_report", effect_names)


EXPECTED_PLUGIN_TOOLS = {
    "parse_budget_csv",
    "budget_summary",
    "budget_variance",
    "budget_consistency",
    "budget_health",
    "budget_query",
    "significant_changes",
    "save_budget_report",
}


def _tool_names(bundle: PluginBundle, tmp: Path) -> set[str]:
    deps = CoreDeps(workspace_root=tmp, run_id="r1")
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    return set(asyncio.run(bundle.toolsets[0].get_tools(ctx)))


class TestPluginContract(unittest.TestCase):
    """Pin the Stage 6A plugin factory contract (mirrors test_ace_writing_plugin)."""

    def _env(self, tmp: Path) -> PluginEnv:
        return PluginEnv(
            plugin_id="zuaef-emtb-budget",
            plugin_version="0.1.0",
            workspace_root=tmp / "workspace",
            state_root=tmp / "state",
        )

    def test_bundle_is_one_toolset_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bundle = create_plugin(self._env(tmp), {})
            self.assertIsInstance(bundle, PluginBundle)
            self.assertEqual(len(bundle.toolsets), 1)
            self.assertEqual(bundle.skill_dirs, ())
            self.assertEqual(bundle.capabilities, ())

    def test_expected_tool_names(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bundle = create_plugin(self._env(tmp), {})
            self.assertEqual(_tool_names(bundle, tmp), EXPECTED_PLUGIN_TOOLS)

    def test_factory_records_env_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            create_plugin(self._env(tmp), {"a": 1})
            self.assertIsNotNone(plugin_module.last_env)
            self.assertEqual(plugin_module.last_env.plugin_id, "zuaef-emtb-budget")
            self.assertEqual(plugin_module.last_env.workspace_root, tmp / "workspace")
            self.assertEqual(plugin_module.last_config, {"a": 1})

    def test_toolset_parity_with_direct_assembly(self) -> None:
        """Plugin toolset exposes exactly the direct-assembly tool surface
        (Stage 6A must not reduce the example2 proof)."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin_ts = create_plugin(self._env(tmp), {}).toolsets[0]
            direct_ts = build_budget_toolset()
            deps = CoreDeps(workspace_root=tmp, run_id="r1")
            ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
            self.assertEqual(
                set(asyncio.run(plugin_ts.get_tools(ctx))),
                set(asyncio.run(direct_ts.get_tools(ctx))),
            )


if __name__ == "__main__":
    unittest.main()
