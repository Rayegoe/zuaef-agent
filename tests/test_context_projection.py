"""Case context projection — P3B-2 T004/T006.

A bound Case contributes a bounded natural-language brief (context, not
workflow): the bridge injects it before the model request, the brief is
bounded, unknown cases inject nothing, and the stillevo-fde profile marks the
Case plugin deferred so its mutation/delivery tools never appear in the
initial model surface.
"""

from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.config import AgentSettings
from zuaef_agent.context_projection import MAX_BRIEF_CHARS, project_case_context
from zuaef_agent.gateway import bridge

REPO = Path(__file__).resolve().parents[1]


def _make_case(root: Path, case_id: str = "stillevo-beauty") -> None:
    case_dir = root / "cases" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "case.md").write_text(
        "---\n"
        f"case_id: {case_id}\n"
        "goal: 把客户从方案讨论推进到 Pilot：完成一次 bounded live demo。\n"
        "status: active\n"
        "---\n\n客户背景见 materials/chat-history.md。\n",
        encoding="utf-8",
    )
    (case_dir / "situation.json").write_text(
        """{
  "schema_version": 1,
  "case_id": "stillevo-beauty",
  "state": {
    "customer": {"company": "云朵美妆", "contact": "李姐", "stage": "方案讨论"},
    "budget": {"monthly_range": "unknown"},
    "demo": {"status": "sample_rewrite_delivered_awaiting_approval"}
  },
  "open_questions": ["demo 用途公众号/朋友圈，待客户回复"]
}""",
        encoding="utf-8",
    )
    (case_dir / "trajectory.jsonl").write_text(
        '{"seq":1,"kind":"decision","summary":"对客户样本文进行现场改写：结论前置、场景保留。"}\n',
        encoding="utf-8",
    )


def test_bound_case_projects_bounded_brief(tmp_path: Path):
    _make_case(tmp_path)
    brief = project_case_context("stillevo-beauty", workspace_root=tmp_path)

    assert brief is not None
    assert brief.startswith("Customer context (bound case: stillevo-beauty):")
    assert "把客户从方案讨论推进到 Pilot" in brief
    assert "customer.company: 云朵美妆" in brief
    assert "demo.status: sample_rewrite_delivered_awaiting_approval" in brief
    assert "[decision]" in brief
    assert "Open questions:" in brief
    assert "not an instruction sequence" in brief
    # unknown leaves carry no background and stay out of the projection
    assert "unknown" not in brief.split("Open questions")[0].split("Current situation")[
        1
    ]
    assert len(brief) <= MAX_BRIEF_CHARS


def test_unknown_or_malformed_case_projects_nothing(tmp_path: Path):
    _make_case(tmp_path)
    assert project_case_context(None, workspace_root=tmp_path) is None
    assert project_case_context("../escape", workspace_root=tmp_path) is None
    assert project_case_context("no-such-case", workspace_root=tmp_path) is None


def test_empty_case_directory_projects_nothing(tmp_path: Path):
    (tmp_path / "cases" / "hollow").mkdir(parents=True)
    assert project_case_context("hollow", workspace_root=tmp_path) is None


def test_projection_is_hard_bounded(tmp_path: Path):
    _make_case(tmp_path)
    target = tmp_path / "cases" / "stillevo-beauty" / "trajectory.jsonl"
    fat = "\n".join(
        f'{{"seq":{i},"kind":"event","summary":"{"很长的一句话" * 60}"}}'
        for i in range(60)
    )
    target.write_text(fat, encoding="utf-8")
    brief = project_case_context("stillevo-beauty", workspace_root=tmp_path)
    assert brief is not None
    assert len(brief) <= MAX_BRIEF_CHARS


def _capture_settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def test_bridge_injects_brief_for_bound_case_and_not_unbound(
    tmp_path: Path, monkeypatch
):

    settings = _capture_settings(tmp_path)
    _make_case(settings.workspace_root)
    captured: dict[str, str] = {}

    def fake_execute_run(agent, deps, *, prompt, **kwargs):
        captured["prompt"] = prompt
        captured["case_id"] = deps.case_id
        from zuaef_agent.runtime import TerminalRun

        return TerminalRun(
            presentation="ok",
            receipt=None,  # type: ignore[arg-type] — prompt capture only
        )

    monkeypatch.setattr(bridge, "execute_run", fake_execute_run)

    bridge.start_profile_run(
        settings=settings,
        profile=None,
        prompt="改写这篇文章",
        conversation_id="c1",
        case_id="stillevo-beauty",
    )
    prompt = captured["prompt"]
    assert prompt.startswith("Customer context (bound case: stillevo-beauty):")
    assert prompt.endswith("改写这篇文章")
    assert "\n\n---\n\n" in prompt

    bridge.start_profile_run(
        settings=settings,
        profile=None,
        prompt="改写这篇文章",
        conversation_id="c2",
        case_id=None,
    )
    assert captured["prompt"] == "改写这篇文章"
    assert captured["case_id"] is None


def test_stillevo_profile_defers_case_tools():
    profile = tomllib.loads(
        (REPO / "profiles" / "stillevo-fde.toml").read_text(encoding="utf-8")
    )
    plugins = {plugin["id"]: plugin for plugin in profile["plugins"]}
    assert plugins["case"].get("defer_tools") is True, (
        "stillevo-fde must defer the Case toolset (P3B-2 INV-8): the initial "
        "model surface must not expose Case mutation/delivery tools"
    )


def test_deferred_case_plugin_absent_from_initial_surface(tmp_path: Path):
    """Behavioral INV-8 proof through the fixture case plugin: with
    defer_tools the Case tool schemas are not in the first request."""
    import sys

    sys.path[:0] = [str(REPO), str(REPO / "tests")]
    from zuaef_agent.composition import build_profile_agent
    from zuaef_agent.gateway.bridge import project_prompt
    from zuaef_agent.gateway.models import InboundEnvelope

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "case-deferred.toml").write_text(
        'schema = 1\nname = "case-deferred"\n\n[generalist]\ntool_search = true\n\n'
        '[[plugins]]\nid = "case-probe"\ndefer_tools = true\n',
        encoding="utf-8",
    )
    settings = _capture_settings(tmp_path)
    settings = settings.with_overrides(enable_tool_search=True)

    def _entry_points():
        from importlib.metadata import EntryPoint

        ep = EntryPoint(
            name="case-probe",
            value="fixture_plugins.case_probe:create_plugin",
            group="zuaef.plugins",
        )
        return {"case-probe": ep}

    run_id = "r-proj-deferred"
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="case-deferred",
        config_root=config_root,
        discover=_entry_points,
        version_for=lambda ep: "0.0.1",
    )
    assert snapshot.plugins[0].defer_tools is True

    from zuaef_agent.models import CoreDeps

    envelope = InboundEnvelope(
        surface="telegram",
        user_id="42",
        channel_id="42",
        message_id="m-1",
        text="改写这篇文章",
    )
    visible: list[str] = []

    async def handler(messages, info):
        visible.extend(t.name for t in (info.function_tools or []))
        return ModelResponse(parts=[TextPart(content="done")])

    deps = CoreDeps(
        workspace_root=settings.workspace_root.resolve(), run_id=run_id
    )
    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run(project_prompt(envelope), deps=deps))

    assert visible, "the model must have seen some tools"
    assert "load_case_context" not in visible, (
        "deferred Case tools must be absent from the initial model surface"
    )
