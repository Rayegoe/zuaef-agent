"""T014A — Capability-owned Result Contract proof (v1.2 SPEC §14), real plugins.

Three REAL business plugins — ace-writing (BudgetedWritingToolset),
zuaef-emtb-budget, zuaef-client-service — each shape a materially different
deliverable through their own toolset instructions + domain tools, and all
three settle through the SAME generic Kernel terminal contract:

- writing      -> article (natural prose terminal; pasted-material rewrite
                  path, no ingest workflow forced)
- budget       -> business analysis (numbers -> variances -> implications)
- client reply -> customer-facing reply (with the policy disclosure frame)

The runtime knows no domain: terminal output stays natural
``str | DeferredToolRequests``; receipts share one schema with zero domain
fields. A structure-only change confined to a domain-owned instructions
constant requires ZERO kernel edits (models.py / runtime.py / plugin_api.py
byte-identical).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from zuaef_ace_writing.writing_toolset import build_writing_toolset
from zuaef_client_service.store import ClientServiceStore
from zuaef_client_service.toolset import build_client_service_toolset
from zuaef_emtb_budget.toolset import build_budget_toolset

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import TerminalRun, execute_run

CLIENT_FIXTURE = REPO / "tests" / "fixtures" / "synthetic_client_service"

BUDGET_CSV = (
    "科目,分类,期初预算,本期变动,期末预算,实际,币种,部门\n"
    "广告投放,revenue,50000,15000,65000,62000,USD,北美\n"
    "物流仓储,cogs,30000,-5000,25000,25500,USD,北美\n"
)

BUDGET_POINTS = [
    {
        "line_item": "广告投放",
        "category": "revenue",
        "period_start_amount": 50000,
        "current_period_change": 15000,
        "period_end_amount": 65000,
        "actual_amount": 62000,
        "currency": "USD",
        "department": "北美",
    }
]

ARTICLE_TERMINAL = (
    "夏天的手不必太热闹。\n\n"
    "李姐把去年的旧文发过来时，附了一句：老板说太像广告。旧文写的是杏仁奶白"
    "和灰调豆沙，今年云朵盘的豆沙奶咖还在同样的位置。见过太多客人做完水钻美甲"
    "两周后来卸，我们做平价彩妆的人，对“热闹”两个字最有体会。"
)

BUDGET_TERMINAL = (
    "实际支出对预算：广告投放实际 62000，期末预算 65000，偏差 -3000（约 4.6%），"
    "在旺季投放口径内属正常波动；物流仓储实际 25500 对预算 25000，超支 500，"
    "金额小可不追因。建议下期只对广告投放设偏差预警线。"
)

CLIENT_TERMINAL = (
    "李姐您好，这版按您老板的意见改了：结论放在了开头，价格没有出现。"
    "场景细节都来自您给的素材，没有加别的话。您看这个方向可以吗？"
)


def _settings(tmp_path: Path) -> AgentSettings:
    return AgentSettings(
        model="test",
        workspace_root=tmp_path / "workspace",
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def _fake_ace_root(tmp_path: Path) -> Path:
    ace = tmp_path / "ace"
    (ace / "tools").mkdir(parents=True, exist_ok=True)
    (ace / "tools" / "ctx.py").write_text("", encoding="utf-8")
    return ace


def _writing_toolset(tmp_path: Path):
    """The REAL BudgetedWritingToolset over a stub ACE checkout."""
    return build_writing_toolset(_fake_ace_root(tmp_path))


def _budget_toolset():
    """The REAL budget analysis toolset (deterministic budget_lib inside)."""
    return build_budget_toolset()


def _client_toolset(tmp_path: Path):
    """The REAL client-service toolset over the synthetic corpus fixture."""
    slice_root = tmp_path / "slice"
    shutil.copytree(CLIENT_FIXTURE, slice_root)
    store = ClientServiceStore(slice_root)
    return build_client_service_toolset(
        store, plugin_id="client-service", plugin_version="0.1.0"
    )


def _steps_script(steps: list[ModelResponse]):
    calls = {"n": 0}

    def fn(messages: list, agent_info: object) -> ModelResponse:
        i = min(calls["n"], len(steps) - 1)
        calls["n"] += 1
        return steps[i]

    return fn


def _run(settings: AgentSettings, toolset, fn) -> TerminalRun:
    run_id = uuid4().hex
    agent = build_agent(settings, run_id=run_id, extra_toolsets=[toolset])
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(
            agent, deps, prompt="do it", settings=settings, run_id=run_id
        )
    assert isinstance(outcome, TerminalRun)
    return outcome


# ── I1: three real domains, one generic terminal ───────────────────────────


def test_three_real_domains_share_one_generic_terminal(tmp_path: Path):
    settings = _settings(tmp_path)

    # writing: the model rewrites pasted material and returns the article as
    # the natural terminal (no forced ingest/artifact workflow)
    article = _run(
        settings,
        _writing_toolset(tmp_path),
        _steps_script([ModelResponse(parts=[TextPart(content=ARTICLE_TERMINAL)])]),
    )

    # budget: the model drives the REAL domain tools first (parse, variance),
    # then returns the business analysis as natural text
    budget = _run(
        settings,
        _budget_toolset(),
        _steps_script(
            [
                ModelResponse(
                    parts=[ToolCallPart("parse_budget_csv", {"csv_text": BUDGET_CSV})]
                ),
                ModelResponse(
                    parts=[ToolCallPart("budget_variance", {"data": BUDGET_POINTS})]
                ),
                ModelResponse(parts=[TextPart(content=BUDGET_TERMINAL)]),
            ]
        ),
    )

    # client service: the model retrieves the REAL business context for the
    # customer, then returns the customer-facing reply
    reply = _run(
        settings,
        _client_toolset(tmp_path),
        _steps_script(
            [
                ModelResponse(
                    parts=[
                        ToolCallPart(
                            "retrieve_client_context",
                            {"customer_id": "CASE-SYN-001", "query": "改稿 开头"},
                        )
                    ]
                ),
                ModelResponse(parts=[TextPart(content=CLIENT_TERMINAL)]),
            ]
        ),
    )

    # One generic terminal: natural str, no domain branch anywhere.
    for outcome in (article, budget, reply):
        assert isinstance(outcome.presentation, str)
        assert outcome.receipt.execution_state == "completed"
    # The three deliverables are materially different because the three
    # capabilities differ — the runtime contributed the same contract to all.
    assert "夏天的手" in article.presentation
    assert "广告投放" in budget.presentation and "偏差" in budget.presentation
    assert "李姐" in reply.presentation and "价格" in reply.presentation
    # The budget/client runs actually exercised their real domain tools.
    budget_tools = {f.tool_name for f in budget.receipt.tool_effect_facts}
    assert {"parse_budget_csv", "budget_variance"} <= budget_tools
    client_tools = {f.tool_name for f in reply.receipt.tool_effect_facts}
    assert "retrieve_client_context" in client_tools
    # Same receipt schema for all domains — and zero domain fields on it.
    schemas = {type(x.receipt) for x in (article, budget, reply)}
    assert len(schemas) == 1, "all domains share one receipt type"
    keys = {frozenset(x.receipt.model_dump()) for x in (article, budget, reply)}
    assert len(keys) == 1
    domain_tokens = ("article", "budget_analysis", "client_reply", "deliverable")
    assert not any(tok in k for k in next(iter(keys)) for tok in domain_tokens)


# ── I2: a structure-only change in ONE domain needs zero kernel edits ──────


KERNEL_FILES = ("models.py", "runtime.py", "plugin_api.py")


def _kernel_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256(
            (REPO / "src" / "zuaef_agent" / name).read_bytes()
        ).hexdigest()
        for name in KERNEL_FILES
    }


def test_structure_only_change_needs_zero_kernel_edits(tmp_path, monkeypatch):
    """Simulate a follow-up structure-only change owned by the budget
    capability: its BUDGET_RULES instructions constant gains a "report
    variance as percentage too" clause. Only the domain module changes —
    the kernel files must be byte-identical and the run must still settle
    through the same generic terminal."""
    import zuaef_emtb_budget.toolset as budget_toolset_module

    before = _kernel_hashes()

    extended = budget_toolset_module.BUDGET_RULES + (
        "报告偏差时同时给出百分比口径。"
    )
    monkeypatch.setattr(budget_toolset_module, "BUDGET_RULES", extended)

    settings = _settings(tmp_path)
    toolset = _budget_toolset()
    instructions = toolset._instructions
    assert "百分比口径" in str(instructions), (
        "the domain-owned instructions change must reach the toolset surface"
    )
    outcome = _run(
        settings,
        toolset,
        _steps_script([ModelResponse(parts=[TextPart(content=BUDGET_TERMINAL)])]),
    )
    assert isinstance(outcome.presentation, str)
    after = _kernel_hashes()
    assert before == after, (
        "a capability-owned structure change must not alter the kernel"
    )


# ── I3: no universal business-result abstraction in the kernel ─────────────


def test_no_universal_business_result_schema_in_kernel():
    import re

    forbidden = (
        "BusinessResult",
        "ResultSchema",
        "ResultRegistry",
        "DeliverableType",
        "ArtifactKind",
    )
    for name in KERNEL_FILES:
        text = (REPO / "src" / "zuaef_agent" / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert not re.search(rf"^class {token}\b", text, re.MULTILINE), (
                f"{name} must not define {token}"
            )
