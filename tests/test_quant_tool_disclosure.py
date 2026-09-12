"""Tool disclosure for the quant research surface (research service v0.2, T007).

Low-frequency research/delivery tools (market intelligence, research packets,
customer evidence, business-artifact rendering) are marked ``defer_loading``
so their schemas stay out of every prompt; the released ToolSearch capability
(the CJK keywords strategy) reveals them on demand. Core evidence tools stay
resident (spec 06 §2). Chinese discovery queries must work; a plain quote
request must not light up the research/delivery domain.
"""

from __future__ import annotations

import asyncio
import sys
from importlib.metadata import EntryPoint
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.tools import ToolDefinition

from zuaef_agent.composition import build_agent_from_snapshot, resolve_profile
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import cjk_keywords_search_fn
from zuaef_agent.models import CoreDeps

sys.path.insert(0, str(Path(__file__).parents[1] / "plugins" / "zuaef-quant"))
from zuaef_quant.toolset import make_toolset

PROFILE = """\
schema = 1
name = "quant-research-surface"

[generalist]
web_search = true
web_fetch = true
tool_search = true
conversation_search = true
context_controls = true

[[plugins]]
id = "quant"
allow_capabilities = true

[plugins.config]
code_mode = false
"""

# P2.1-B: legacy broad/alias tools are implementation-compatible but must not
# retain a resident model-visibility advantage over the narrow surface.
# P7.1 retired the watchlist aliases and P7.2 retired get_live_signals;
# get_trading_context retires in P7.3.
LEGACY_DEFERRED = {
    "get_trading_context",
}
NARROW_DEFERRED = {
    "get_market_context",
    "get_market_intelligence",
    "get_signal_board",
    "get_positions",
    "get_validation_status",
    "run_live_scan",
    "manage_watchlist",
    "save_research_packet",
    "get_research_packet",
    "record_customer_evidence",
    "render_quant_business_artifact",
}
DEFERRED = LEGACY_DEFERRED | NARROW_DEFERRED
RESIDENT_CORE = {
    "get_symbol_context",
    "evaluate_strategy",
    "record_decision_brief",
    "record_trade_outcome",
}


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
        # host ceiling: the deployment authorizes tool_search (OPi5 .env has
        # ZUAEF_ENABLE_TOOL_SEARCH); the profile requests it too.
        enable_tool_search=True,
    )


def _compose(tmp_path: Path, monkeypatch) -> Agent:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / "quant-research-surface.toml").write_text(
        PROFILE, encoding="utf-8"
    )
    ep = EntryPoint(name="quant", value="zuaef_quant:create_plugin", group="zuaef.plugins")
    monkeypatch.setenv("ZUAEF_QUANT_PYTHON", sys.executable)
    snapshot = resolve_profile(
        "quant-research-surface",
        _settings(tmp_path),
        config_root=config_root,
        discover=lambda: {"quant": ep},
        version_for=lambda _ep: "0.1.0",
    )
    return build_agent_from_snapshot(
        _settings(tmp_path),
        run_id="r-disclosure",
        snapshot=snapshot,
        discover=lambda: {"quant": ep},
        version_for=lambda _ep: "0.1.0",
    )


def test_effective_policy_is_intersection_of_host_ceiling_and_request(tmp_path, monkeypatch):
    """T001/T009 pin: the quant profile's frozen generalist policy grants the
    research resources (host ceiling permitting) and never memory/subagents —
    market truth has durable artifacts, quant production stays one agent."""
    from zuaef_agent.composition import resolve_profile as _rp

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / "quant-research-surface.toml").write_text(
        PROFILE, encoding="utf-8"
    )
    ep = EntryPoint(name="quant", value="zuaef_quant:create_plugin", group="zuaef.plugins")
    monkeypatch.setenv("ZUAEF_QUANT_PYTHON", sys.executable)
    # host ceiling mirroring the OPi5 deployment .env: tool_search,
    # conversation_search, context_controls on; web flags off (to be added
    # at deployment); memory/subagents off.
    settings = _settings(tmp_path).with_overrides(
        enable_conversation_search=True,
        enable_context_controls=True,
    )
    snapshot = _rp(
        "quant-research-surface",
        settings,
        config_root=config_root,
        discover=lambda: {"quant": ep},
        version_for=lambda _ep: "0.1.0",
    )
    effective = snapshot.generalist
    assert effective["enable_tool_search"] is True
    assert effective["enable_context_controls"] is True
    assert effective["enable_conversation_search"] is True
    # web resources: requested by the profile, granted only under a host
    # ceiling that allows them (this fixture's ceiling is off — the OPi5
    # deployment adds ZUAEF_ENABLE_WEB_SEARCH/FETCH).
    assert effective["enable_web_search"] is False
    assert effective["enable_web_fetch"] is False
    # never granted, no matter what the profile or host say
    assert effective["enable_memory"] is False
    assert effective["enable_subagents"] is False
    assert effective["enable_shell"] is False
    assert effective["enable_repo_context"] is False

    # with the ceiling raised (deployment step), the same profile grants web
    web_settings = settings.with_overrides(
        enable_web_search=True, enable_web_fetch=True
    )
    snapshot_web = _rp(
        "quant-research-surface",
        web_settings,
        config_root=config_root,
        discover=lambda: {"quant": ep},
        version_for=lambda _ep: "0.1.0",
    )
    assert snapshot_web.generalist["enable_web_search"] is True
    assert snapshot_web.generalist["enable_web_fetch"] is True


def _surface_steps(agent: Agent, sequence: list[tuple[str, dict]], tmp_path: Path) -> list[list[str]]:
    steps: list[list[str]] = []
    seq = list(sequence)

    async def handler(messages, info):
        names = sorted(getattr(t, "name", "") for t in (info.function_tools or []))
        steps.append(names)
        if seq:
            name, args = seq.pop(0)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart(content="done")])

    settings = _settings(tmp_path)
    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id="r-disclosure",
        bindings={"analysis_scope": "oc_test"},
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("probe", deps=deps))
    return steps


def test_initial_surface_keeps_core_resident_and_research_deferred(tmp_path, monkeypatch):
    agent = _compose(tmp_path, monkeypatch)
    steps = _surface_steps(agent, [], tmp_path)
    first = steps[0]
    for name in RESIDENT_CORE:
        assert name in first, f"semantic core tool {name} must stay resident"
    for name in DEFERRED:
        assert name not in first, f"deferred tool {name} leaked into the initial surface"
    assert "search_tools" in first, "ToolSearch discovery must be available"


def test_legacy_broad_tools_lose_runtime_visibility_not_call_compatibility(
    tmp_path, monkeypatch
):
    """P2.1-B: the legacy broad/alias tools remain callable and tested, but
    they must not beat the narrow surface through resident visibility."""
    toolset = make_toolset(quant_python=Path("nonexistent"), workspace_root=tmp_path)
    for name in LEGACY_DEFERRED:
        assert toolset.tools[name].defer_loading is True, name
        assert callable(toolset.tools[name].function), name
    for name in RESIDENT_CORE:
        assert toolset.tools[name].defer_loading is not True, name


def test_chinese_query_reveals_deferred_research_tools(tmp_path, monkeypatch):
    agent = _compose(tmp_path, monkeypatch)
    steps = _surface_steps(
        agent, [("search_tools", {"queries": ["600550 公告 新闻"]})], tmp_path
    )
    second = steps[1]
    assert "get_market_intelligence" in second, f"公告/新闻 query revealed: {second}"
    # resident tools stay visible after discovery
    assert "get_symbol_context" in second


def test_market_wide_query_reveals_market_context(tmp_path, monkeypatch):
    agent = _compose(tmp_path, monkeypatch)
    steps = _surface_steps(
        agent, [("search_tools", {"queries": ["今天为什么跌 A股 外盘 原油"]})], tmp_path
    )
    assert "get_market_context" in steps[1]


def test_customer_evidence_discoverable_in_chinese(tmp_path, monkeypatch):
    agent = _compose(tmp_path, monkeypatch)
    steps = _surface_steps(
        agent, [("search_tools", {"queries": ["客户说 供应商订单很满"]})], tmp_path
    )
    assert "record_customer_evidence" in steps[1]


def test_plain_quote_request_does_not_load_research_or_delivery_tools(tmp_path, monkeypatch):
    agent = _compose(tmp_path, monkeypatch)
    steps = _surface_steps(
        agent,
        [("search_tools", {"queries": ["普通股票报价请求"]})],
        tmp_path,
    )
    second = steps[1]
    for name in ("render_quant_business_artifact", "save_research_packet",
                 "record_customer_evidence", "get_research_packet"):
        assert name not in second, f"plain quote query revealed {name}"


def test_cjk_search_scores_against_real_tool_definitions(tmp_path):
    """Unit-level pin of spec 06 §6: the discovery matrix over the real
    toolset schemas."""
    toolset = make_toolset(quant_python=Path("nonexistent"), workspace_root=tmp_path)
    defs = [
        ToolDefinition(name=name, description=tool.description or "")
        for name, tool in toolset.tools.items()
    ]
    ctx = None  # the CJK search fn never touches ctx

    def discover_ranked(query: str) -> list[str]:
        return list(cjk_keywords_search_fn(ctx, [query], defs))

    def discover(query: str) -> set[str]:
        return set(discover_ranked(query))

    assert discover("公告 新闻") == {"get_market_intelligence"}
    assert "save_research_packet" in discover("全面分析 研究报告")
    assert "record_customer_evidence" in discover("客户说")
    # resident domains stay discoverable through their own descriptions
    assert "manage_watchlist" in discover("加入自选")
    assert "get_trading_context" in discover("持仓建议")

    # P2 narrow semantic tools: the expected tool must be the top discovery
    # result for the intent it owns.  ToolSearch is keyword overlap over the
    # real descriptions, so this pins the user vocabulary as tool contract.
    expected_top = {
        "今天有什么机会 ready near": "get_signal_board",
        "策略现在验证到什么程度": "get_validation_status",
        "我现在持有什么": "get_positions",
        "重新扫描今天": "run_live_scan",
        "把海康威视加入观察": "manage_watchlist",
    }
    for query, tool_name in expected_top.items():
        ranked = discover_ranked(query)
        assert ranked, f"no tool discovered for {query!r}"
        assert ranked[0] == tool_name, f"{query!r} ranked {ranked[:4]!r}"

    # plain quote vocabulary must not light up research/delivery tools
    plain = discover("普通股票报价请求")
    assert not plain & DEFERRED
