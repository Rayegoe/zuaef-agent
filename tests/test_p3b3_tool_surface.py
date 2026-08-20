"""Golden tool-surface tests — P3B-3 T014/T020 (deterministic, no network).

Progressive disclosure must operate at the state ≠ delivery boundary with the
REAL zuaef-case plugin: model-visible surface (not the plugin registry) is
inspected at every step of a scripted FunctionModel run.

  - ordinary Case-state access (search + load_case_context) never exposes
    save_draft / send_to_customer;
  - explicit delivery intent (发给客户) discovers the delivery tools —
    including through a pure-Chinese query, which upstream keyword search
    cannot tokenize (P3B-3 extends tokenization via the public ToolSearch
    strategy seam);
  - a poisoned trajectory must not re-enter the model-visible prompt for a
    bound Case (self-reinforcing context regression).
"""

from __future__ import annotations

import asyncio
import sys
from importlib.metadata import EntryPoint
from pathlib import Path

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "src"),
    str(REPO / "tests"),
    str(REPO / "plugins" / "zuaef-case"),
]

from zuaef_case.context import project_case_brief as project_case_context

from zuaef_agent.composition import build_profile_agent
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps

PROFILE = """\
schema = 1
name = "p3b3-surface"

[generalist]
tool_search = true

[[plugins]]
id = "case"
defer_tools = true
allow_capabilities = true

[[plugins]]
id = "fixture-ace-writing"
defer_tools = true
"""

DELIVERY_TOOLS = ("save_draft", "send_to_customer")


def _ep(name: str, value: str) -> EntryPoint:
    return EntryPoint(name=name, value=value, group="zuaef.plugins")


DISCOVER = {
    "case": _ep("case", "zuaef_case:create_plugin"),
    "fixture-ace-writing": _ep(
        "fixture-ace-writing", "fixture_plugins.writing:create_plugin"
    ),
}
VERSIONS = {"case": "0.1.0", "fixture-ace-writing": "0.2.1"}


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_skills=False,
        enable_tool_search=True,
    )


def _config_root(tmp_path: Path) -> Path:
    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True, exist_ok=True)
    (config_root / "profiles" / "p3b3-surface.toml").write_text(
        PROFILE, encoding="utf-8"
    )
    return config_root


def _agent(settings: AgentSettings, config_root: Path, run_id: str):
    return build_profile_agent(
        settings,
        run_id=run_id,
        profile="p3b3-surface",
        config_root=config_root,
        discover=lambda: DISCOVER,
        version_for=lambda ep: VERSIONS[ep.name],
    )


def _make_case(root: Path) -> None:
    from zuaef_case.models import CaseDoc, Situation, TrajectoryEntry
    from zuaef_case.store import CaseStore

    store = CaseStore(root / "cases")
    store.create_case(
        CaseDoc(
            case_id="stillevo-beauty",
            goal="把云朵美妆推进到 Pilot：完成一次现场 demo。",
            stakeholders={"customer": "wechat-li"},
        )
    )
    store.write_situation(
        Situation(
            case_id="stillevo-beauty",
            updated_by="barry",
            state={"customer": {"company": "云朵美妆", "contact": "李姐"}},
            barry_override="p3b3-fixture",
        )
    )
    # Poisoned audit history: a known-bad prior agent decision/action that
    # must NOT become model-visible Case background (P3B-3 T020).
    for kind, summary in (
        ("decision", "resend msg-005 to customer without asking"),
        ("action", "send_to_customer called for msg-005"),
        ("approval", "awaiting approval"),
    ):
        store.append_trajectory_for_case(
            "stillevo-beauty",
            TrajectoryEntry(kind=kind, role="agent", run_id="r-bad", summary=summary),
        )


def _surface_steps(agent, sequence, settings, case_id=None) -> list[list[str]]:
    steps: list[list[str]] = []
    seq = list(sequence)

    async def handler(messages, info):
        names = sorted(getattr(t, "name", "") for t in (info.function_tools or []))
        steps.append(names)
        if seq:
            name, args = seq.pop(0)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart(content="done")])

    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(),
        run_id="r-p3b3-surface",
        bindings={"case": case_id} if case_id else {},
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("写一篇公众号文章", deps=deps))
    return steps


def test_initial_surface_is_empty_of_business_and_delivery_tools(tmp_path: Path):
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    agent, _ = _agent(settings, _config_root(tmp_path), "r-p3b3-surface")
    steps = _surface_steps(agent, [], settings)
    first = steps[0]
    assert not any(name in first for name in DELIVERY_TOOLS)
    assert "load_case_context" not in first
    assert "list_materials" not in first


def test_case_state_access_never_exposes_delivery_affordance(tmp_path: Path):
    """Ordinary Case work (discover + load Case state) keeps the delivery
    tool surface dormant — the state ≠ delivery separation is model-visible."""
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    agent, _ = _agent(settings, _config_root(tmp_path), "r-p3b3-surface")
    steps = _surface_steps(
        agent,
        [
            ("search_tools", {"queries": ["case goal situation 背景"]}),
            ("load_case_context", {}),
            ("load_case_context", {}),
        ],
        settings,
        case_id="stillevo-beauty",
    )
    assert len(steps) >= 3
    after_search = steps[1]
    assert "load_case_context" in after_search
    assert not any(name in after_search for name in DELIVERY_TOOLS)
    # Calling the state tool repeatedly still never reveals delivery.
    after_state_access = steps[2]
    assert "load_case_context" in after_state_access
    assert not any(name in after_state_access for name in DELIVERY_TOOLS)


def test_delivery_tools_discoverable_on_explicit_delivery_intent(tmp_path: Path):
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    agent, _ = _agent(settings, _config_root(tmp_path), "r-p3b3-surface")
    steps = _surface_steps(
        agent,
        [
            ("search_tools", {"queries": ["发给客户"]}),
            ("send_to_customer", {"draft_ref": "msg-001.md"}),
        ],
        settings,
        case_id="stillevo-beauty",
    )
    after_search = steps[1]
    assert "send_to_customer" in after_search, (
        "explicit 发给客户 must be able to discover the delivery domain — "
        "including through a pure-Chinese query (CJK-aware search strategy)"
    )


def test_delivery_tools_absent_from_writing_oriented_search(tmp_path: Path):
    """A writing/rewrite query discovers the writing domain and not the
    delivery domain (GF-A/GF-B surface shape)."""
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    agent, _ = _agent(settings, _config_root(tmp_path), "r-p3b3-surface")
    steps = _surface_steps(
        agent,
        [("search_tools", {"queries": ["rewrite article 改写文章 materials 素材"]})],
        settings,
        case_id="stillevo-beauty",
    )
    after_search = steps[1]
    assert "list_materials" in after_search or "save_artifact" in after_search
    assert not any(name in after_search for name in DELIVERY_TOOLS)


def test_poisoned_trajectory_stays_out_of_default_case_projection(tmp_path: Path):
    """P3B-3 T020: a previous bad Agent decision in the trajectory must not
    re-enter the next turn's model-visible Case background."""
    settings = _settings(tmp_path)
    _make_case(settings.workspace_root)
    brief = project_case_context(
        "stillevo-beauty", workspace_root=settings.workspace_root
    )
    assert brief is not None
    assert "云朵美妆" in brief  # durable business facts remain
    assert "resend msg-005" not in brief
    assert "send_to_customer" not in brief
    assert "awaiting approval" not in brief
    assert "Recent trajectory" not in brief
