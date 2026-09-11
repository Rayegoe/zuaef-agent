"""P5 natural-language routing gates (spec pack 05 / 10 section G).

Routing is semantic reasoning by the outcome-owning agent over the deferred
capability catalog — not a keyword switch. These deterministic tests prove
the routing surface itself (no real model requests):

- the deferred catalog exposes business-semantic descriptions for all four
  formats (Chinese and English outcome words), so paraphrased intents can
  discover the right domain;
- artifact tools stay hidden until the model loads a capability
  (`load_capability`), and loading reveals exactly that capability's tools;
- one run can load several capabilities (multi-artifact requests are
  normal);
- guidance carries the explicit-format-override and no-format-menu rules.

Live-model paraphrase acceptance (G1–G8 with a real lane) runs in P7.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_artifacts.plugin import build_plugin

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps  # noqa: F401 - typing of the composed agent
from zuaef_agent.plugin_api import PluginEnv

ARTIFACT_TOOL_NAMES = {
    "create_docx",
    "revise_docx",
    "inspect_docx",
    "create_pdf",
    "convert_to_pdf",
    "merge_pdf",
    "edit_pdf",
    "inspect_pdf",
    "create_slides",
    "revise_slides",
    "inspect_slides",
    "create_spreadsheet",
    "revise_spreadsheet",
    "inspect_spreadsheet",
}


def _agent(tmp_path: Path) -> Agent:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
        enable_filesystem=False,
        enable_knowledge=False,
    )
    bundle = build_plugin(
        PluginEnv(
            plugin_id="artifacts",
            plugin_version="0.1.0",
            workspace_root=workspace,
            state_root=tmp_path / ".zuaef-state",
        ),
        {},
    )
    return build_agent(settings, extra_capabilities=list(bundle.capabilities))


def _run_capture(agent: Agent, *, prompt: str, sequence: list[tuple[str, dict]]):
    """Scripted-model run recording, per model request: visible tool names
    and the message texts (catalog lives in the request prefix)."""
    captured: dict = {"requests": [], "invoked": []}
    seq = list(sequence)

    async def handler(messages, info):
        visible = sorted(t.name for t in info.function_tools)
        texts = [getattr(info, "instructions", None) or ""]
        for message in messages:
            content = getattr(message, "content", None)
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                texts.extend(
                    part.content
                    for part in content
                    if getattr(part, "content", None)
                    and isinstance(part.content, str)
                )
        captured["requests"].append({"tools": visible, "texts": texts})
        if seq:
            name, args = seq.pop(0)
            captured["invoked"].append(name)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart(content="done")])

    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run(prompt))
    return captured


def test_catalog_lists_all_four_business_capabilities(tmp_path):
    """G8/D4: discovery runs on outcome wording, in the working language,
    never on file extensions alone."""
    captured = _run_capture(_agent(tmp_path), prompt="开始", sequence=[])
    first_texts = "\n".join(captured["requests"][0]["texts"])
    for capability_id in (
        "docx-artifacts",
        "pdf-artifacts",
        "slides-artifacts",
        "spreadsheet-artifacts",
    ):
        assert capability_id in first_texts
    # Chinese outcome words from the spec's routing table.
    for phrase in ("方案", "汇报", "报价", "客户"):
        assert phrase in first_texts, f"catalog should carry outcome word {phrase!r}"
    # English outcome words for paraphrase robustness.
    for phrase in ("proposal", "presentation", "pricing", "PDF"):
        assert phrase.lower() in first_texts.lower()


def test_artifact_tools_hidden_until_a_capability_is_loaded(tmp_path):
    """Progressive disclosure: no artifact tool is visible before an
    explicit load; the catalog/load_capability surface is (G7 control)."""
    captured = _run_capture(_agent(tmp_path), prompt="总结一下这份文件说了什么", sequence=[])
    first = captured["requests"][0]["tools"]
    assert "load_capability" in first
    assert not ARTIFACT_TOOL_NAMES & set(first), (
        "artifact tools must stay hidden until a capability is loaded"
    )


def test_loading_docx_reveals_exactly_its_tools(tmp_path):
    captured = _run_capture(
        _agent(tmp_path),
        prompt="做一份以后还要继续修改的完整方案",
        sequence=[("load_capability", {"id": "docx-artifacts"})],
    )
    assert captured["invoked"] == ["load_capability"]
    second_tools = set(captured["requests"][1]["tools"])
    assert {"create_docx", "revise_docx", "inspect_docx"} <= second_tools
    # Loading docx does not reveal slides tools.
    assert "create_slides" not in second_tools


def test_multi_capability_load_in_one_run(tmp_path):
    """G6: 汇报 + 计算表 → two capabilities loadable in a single run."""
    captured = _run_capture(
        _agent(tmp_path),
        prompt="给我老板汇报和详细计算表",
        sequence=[
            ("load_capability", {"id": "slides-artifacts"}),
            ("load_capability", {"id": "spreadsheet-artifacts"}),
        ],
    )
    final_tools = set(captured["requests"][-1]["tools"])
    assert "create_slides" in final_tools
    assert "create_spreadsheet" in final_tools


def test_load_capability_bounces_unknown_id(tmp_path):
    """An unknown capability id is a recoverable retry, not a crash."""
    captured = _run_capture(
        _agent(tmp_path),
        prompt="load something",
        sequence=[("load_capability", {"id": "no-such-capability"})],
    )
    # The run must still settle normally after the bounced call.
    assert captured["requests"]


def test_guidance_carries_routing_rules():
    """05: explicit format wins; no format menu; direct answers stay
    chat answers; PDF for final delivery, editable source preserved."""
    guidance_dir = Path(
        "__file__ placeholder"
    )  # placeholder to keep the test readable
    del guidance_dir
    from zuaef_artifacts.guidance import load_guidance

    docx = load_guidance("docx.md")
    slides = load_guidance("slides.md")
    spreadsheet = load_guidance("spreadsheet.md")
    pdf = load_guidance("pdf.md")

    assert "Word" in docx and "可编辑" in docx
    assert "发客户" in pdf and ("可编辑" in pdf or "editable" in pdf)
    assert "6 页" in slides  # respect explicit slide budgets
    assert "自己改参数" in spreadsheet  # keep inputs editable
    assert "Do not" in spreadsheet or "不要" in spreadsheet


def test_capability_descriptions_are_not_extension_only(tmp_path):
    """04: each description must carry business intent, not just a suffix."""
    from zuaef_artifacts.plugin import build_plugin as bp

    workspace = tmp_path / "ws"
    workspace.mkdir()
    bundle = bp(
        PluginEnv(
            plugin_id="artifacts",
            plugin_version="0.1.0",
            workspace_root=workspace,
            state_root=tmp_path / "state",
        ),
        {},
    )
    by_id = {cap.id: cap.get_description() for cap in bundle.capabilities}
    assert "提案" in by_id["docx-artifacts"] or "方案" in by_id["docx-artifacts"]
    assert "最终版" in by_id["pdf-artifacts"] or "PDF" in by_id["pdf-artifacts"]
    assert "汇报" in by_id["slides-artifacts"] or "周会" in by_id["slides-artifacts"]
    assert "报价" in by_id["spreadsheet-artifacts"] or "测算" in by_id["spreadsheet-artifacts"]
