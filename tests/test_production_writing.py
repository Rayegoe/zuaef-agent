"""Production writing v0.2 contract tests — zero model calls.

Covers the thin production driver (examples/production_writing.py), SPEC
§6 (input contract), §21 (one production composition path), §22 (host
projection retired) and §31 (anti-cheating):

  1. WritingTask rejects host-authored plan fields (extra="forbid")
  2. the first-request prompt carries ONLY the task + mechanical facts:
     no angle/questions/outline, no selected techniques/memory/examples,
     no material text
  3. mechanical_prepare: bytes -> sha256 -> rights -> ACE ingest -> real
     M-id binding (skipUnless ACE checkout present)
  4. production composition goes through build_profile_agent("ace-writing")
     -> the two-tool WritingEnvironmentToolset + host-only persistence
  6. metric/artifact helpers and re-runnable reset
  7. CLI args map onto WritingTask

No model call happens in this module (the composition test builds the agent,
it never runs it).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, ToolCallPart

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import (
    DEFAULT_ACE_ROOT,
    WritingEnvironmentToolset,
)

from examples.production_writing import (
    PreparedFile,
    WritingTask,
    mechanical_prepare,
    parse_args,
    render_agent_prompt,
    resolve_ace_root,
    run_production_task,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps

_ACE_ROOT = Path(os.environ.get("ACE_ROOT", str(DEFAULT_ACE_ROOT))).expanduser().resolve()
ACE_ROOT = _ACE_ROOT if (_ACE_ROOT / "tools" / "ctx.py").is_file() else None
# The real entry point is only present when the plugin distribution is
# installed; the checked-out module is importable via sys.path above.
PLUGIN_INSTALLED = "ace-writing" in {
    ep.name for ep in __import__("importlib.metadata", fromlist=["entry_points"]).entry_points(group="zuaef.plugins")
}
PROFILE_EXISTS = (REPO / "profiles" / "ace-writing.toml").is_file()
NEEDS_ACE = pytest.mark.skipif(
    ACE_ROOT is None, reason="ACE checkout (tools/ctx.py) not available"
)
NEEDS_PLUGIN = pytest.mark.skipif(
    not (PLUGIN_INSTALLED and PROFILE_EXISTS),
    reason="ace-writing plugin entry point and/or profiles/ace-writing.toml missing",
)

MATERIAL_A = "# 素材甲\n\n客户说大概三千个号。\n编辑提到同质化。\n"
MATERIAL_B = "# 素材乙\n\n产品发布会照片显示现场约两百人。\n"


def _settings(tmp_path: Path) -> AgentSettings:
    return AgentSettings(
        model="test",
        workspace_root=tmp_path / "ws",
        runtime_state_root=tmp_path / "state",
        request_limit=8,
    )


# --- 1. input contract ----------------------------------------------------------


def test_writing_task_accepts_only_the_thin_contract():
    task = WritingTask(
        article_id="beauty-20260818-001",
        assignment="根据客户提供的采访和产品资料写一篇公众号文章。",
        audience="普通消费者",
        constraints=["约1800字", "不虚构采访现场", "产品事实必须来自原始材料"],
    )
    assert task.article_id == "beauty-20260818-001"
    assert task.audience == "普通消费者"
    assert len(task.constraints) == 3
    assert WritingTask(article_id="a", assignment="写").constraints == []


@pytest.mark.parametrize(
    "field",
    [
        "writing_plan",
        "angle",
        "questions",
        "outline",
        "selected_techniques",
        "selected_editorial_memory",
        "selected_examples",
        "selected_material_ids",
        "material",
    ],
)
def test_writing_task_rejects_host_plan_fields(field):
    """SPEC §6/WRITE-2: the production contract must refuse host decisions."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        WritingTask(
            article_id="a",
            assignment="写一篇短文。",
            **{field: "anything"},
        )


# --- 2. thin first-request prompt -----------------------------------------------


def test_prompt_has_no_host_plan(tmp_path):
    task = WritingTask(
        article_id="wc-1",
        assignment="根据素材写一篇800字左右的观察短文。",
        audience="普通读者",
        constraints=["不虚构", "只用素材里的内容"],
    )
    from examples.production_writing import PrepResult

    prep = PrepResult(
        task=task,
        run_id="wc-1",
        ace_root=Path("/tmp/ace"),
        title="wc-1",
        files=[
            PreparedFile(
                source_ref="a.md",
                path=Path("a.md"),
                sha256="x" * 64,
                byte_length=10,
                rights="user-provided",
                material_id="M001",
            )
        ],
    )
    desk_pack = "# 当前可用材料\n\n[M001]\n真实素材正文。"
    prompt = render_agent_prompt(prep, desk_pack)
    assert task.article_id in prompt
    assert task.assignment in prompt
    assert "普通读者" in prompt
    assert "- 不虚构" in prompt
    assert "- 只用素材里的内容" in prompt
    assert desk_pack in prompt
    assert "pull_context" in prompt
    assert "save_article" in prompt
    assert "list_materials" not in prompt
    assert "save_artifact" not in prompt
    assert "RunSummary" not in prompt
    assert "receipt fields" in prompt
    for banned in (
        "writing plan",
        "### angle",
        "## WritingContext",
        "questions:",
        "outline",
        "T001",
        "corpus.T001",
        "relevant techniques",
        "editorial memory",
        "examples (language",
        "<example",
        "### material",
        "source_sha256",
    ):
        assert banned not in prompt, f"host plan marker {banned!r} leaked into prompt"


def test_prompt_carries_natural_language_feedback(tmp_path):
    from examples.production_writing import PrepResult

    task = WritingTask(article_id="wc-4", assignment="写一篇文章。")
    prep = PrepResult(
        task=task,
        run_id="wc-4",
        ace_root=Path("/tmp/ace"),
        title="wc-4",
        files=[],
    )
    feedback = "判断句太多，人物没有出来，开头太像背景说明。"
    previous = "# 上一稿\n\n这是上一稿正文。"
    prompt = render_agent_prompt(
        prep,
        "# 当前可用材料\n\n原始片段。",
        feedback=feedback,
        previous_article=previous,
    )
    assert feedback in prompt
    assert previous in prompt
    assert "Revise the article" in prompt


# --- 3. mechanical preparation (ACE-gated) --------------------------------------


@NEEDS_ACE
def test_mechanical_prepare_binds_sha256_and_material_ids(tmp_path):
    a = tmp_path / "raw-a.md"
    b = tmp_path / "raw-b.md"
    a.write_text(MATERIAL_A, encoding="utf-8")
    b.write_text(MATERIAL_B, encoding="utf-8")
    task = WritingTask(article_id="mprep-1", assignment="写一篇短文。")
    prep = mechanical_prepare(
        task,
        material_paths=[a, b],
        rights="study-only",
        ace_root=ACE_ROOT,
        run_id="mprep-1",
    )
    assert prep.run_id == "mprep-1"
    assert [f.material_id for f in prep.files] == ["M001", "M002"]
    assert prep.files[0].sha256 == hashlib.sha256(MATERIAL_A.encode("utf-8")).hexdigest()
    assert prep.files[1].sha256 == hashlib.sha256(MATERIAL_B.encode("utf-8")).hexdigest()
    assert prep.files[0].byte_length == len(MATERIAL_A.encode("utf-8"))
    assert prep.files[0].rights == "study-only"
    # prep record is mechanical metadata only — no content
    assert "素材" not in json.dumps(prep.record(), ensure_ascii=False)


@NEEDS_ACE
def test_mechanical_prepare_rejects_bad_rights_and_missing_file(tmp_path):
    a = tmp_path / "raw.md"
    a.write_text("x", encoding="utf-8")
    task = WritingTask(article_id="mprep-2", assignment="写。")
    with pytest.raises(ValueError, match="rights"):
        mechanical_prepare(task, material_paths=[a], rights="pirated", ace_root=ACE_ROOT)
    with pytest.raises(FileNotFoundError, match="missing"):
        mechanical_prepare(
            task, material_paths=[tmp_path / "nope.md"], ace_root=ACE_ROOT
        )


def test_resolve_ace_root_errors_on_missing_ctx(tmp_path):
    with pytest.raises(FileNotFoundError, match="tools/ctx.py"):
        resolve_ace_root(tmp_path / "no-ace")


# --- 4. production composition through the profile -------------------------------


@NEEDS_PLUGIN
def test_production_composition_through_ace_writing_profile(tmp_path):
    """WRITE-1: build_profile_agent("ace-writing") composes the writing surface.

    Only StepPersistence remains, and it is host execution evidence rather
    than model-visible working memory."""
    from examples.production_writing import composition_settings

    settings = composition_settings(_settings(tmp_path))
    from zuaef_agent.composition import build_profile_agent

    agent, snapshot = build_profile_agent(
        settings,
        run_id="wc-probe",
        profile="ace-writing",
        config_root=REPO,
    )
    assert snapshot is not None
    assert snapshot.profile == "ace-writing"
    assert [p.id for p in snapshot.plugins] == ["ace-writing"]

    caps = agent.root_capability.capabilities
    cap_names = {type(c).__name__ for c in caps}
    assert "StepPersistence" in cap_names
    assert cap_names.isdisjoint(
        {"ToolOutputLimits", "Planning", "FileSystem", "Knowledge", "Skills"}
    )

    toolsets = list(agent.toolsets)
    assert any(isinstance(t, WritingEnvironmentToolset) for t in toolsets)


@NEEDS_PLUGIN
def test_profile_toolset_exposes_exact_ace_surface(tmp_path):
    settings = _settings(tmp_path)
    from zuaef_agent.composition import build_profile_agent

    agent, _ = build_profile_agent(
        settings,
        run_id="wc-probe2",
        profile="ace-writing",
        config_root=REPO,
    )
    toolset = next(
        t for t in agent.toolsets if isinstance(t, WritingEnvironmentToolset)
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id="wc-probe2")
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    names = set(__import__("asyncio").run(toolset.get_tools(ctx)))
    assert names == {"pull_context", "save_article"}


def test_profile_composition_with_injected_discovery(tmp_path):
    """Hermetic variant for environments where the plugin dist is not installed.

    The checked-out module is on sys.path; we synthesize the entry point the
    way the composition layer would see it after ``pip install``."""
    from zuaef_agent.composition import build_profile_agent

    ep = EntryPoint(
        name="ace-writing",
        value="zuaef_ace_writing:create_plugin",
        group="zuaef.plugins",
    )
    settings = _settings(tmp_path)
    agent, snapshot = build_profile_agent(
        settings,
        run_id="wc-hermetic",
        profile="ace-writing",
        config_root=REPO,
        discover=lambda: {"ace-writing": ep},
        version_for=lambda ep: "0.2.0",
    )
    assert [p.id for p in snapshot.plugins] == ["ace-writing"]
    assert any(isinstance(t, WritingEnvironmentToolset) for t in agent.toolsets)


# --- 6. mechanical helpers -------------------------------------------------------


def test_metrics_counts_model_responses_and_tool_calls():
    from examples.production_writing import metrics_from_messages

    messages = [
        ModelRequest(parts=[]),
        ModelResponse(
            parts=[
                TextPart(content="plan"),
                ToolCallPart(tool_name="pull_context", args="{}"),
            ]
        ),
        ModelRequest(parts=[]),
        ModelResponse(parts=[ToolCallPart(tool_name="save_article", args="{}")]),
        ModelRequest(parts=[]),
        ModelResponse(parts=[TextPart(content="done")]),
    ]
    m = metrics_from_messages(messages)
    assert m["model_requests"] == 3
    assert m["tool_calls"] == 2
    assert m["tool_names"] == ["pull_context", "save_article"]


def test_final_artifact_text_reads_snapshot_not_summary(tmp_path):
    from examples.production_writing import final_artifact_text

    run_id = "prod-t01"
    snapshot = tmp_path / "artifacts" / run_id / "final.md"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("# The real article\n\nBody.", encoding="utf-8")
    text, path = final_artifact_text(tmp_path, run_id)
    assert text.startswith("# The real article")
    assert path.endswith("final.md")
    text2, _ = final_artifact_text(tmp_path, "prod-nosuch")
    assert text2 == ""


def test_reset_run_state_is_rerunnable(tmp_path):
    from examples.production_writing import reset_run_state

    settings = _settings(tmp_path)
    (settings.receipt_dir / "run-x.json").parent.mkdir(parents=True, exist_ok=True)
    (settings.receipt_dir / "run-x.json").write_text("{}", encoding="utf-8")
    reset_run_state(settings, "run-x", ace_root=ACE_ROOT, clean_ace=False)
    assert not (settings.receipt_dir / "run-x.json").exists()
    # no crash on a second run
    reset_run_state(settings, "run-x", ace_root=ACE_ROOT, clean_ace=False)


def test_composition_settings_leave_only_host_persistence_for_writing(tmp_path):
    from examples.production_writing import composition_settings

    s = _settings(tmp_path)
    composed = composition_settings(s, request_limit=21)
    assert composed.enable_filesystem is False
    assert composed.enable_knowledge is False
    assert composed.enable_planning is False
    assert composed.enable_skills is False
    assert composed.enable_tool_output_limits is False
    assert composed.enable_step_persistence is True
    assert composed.enable_shell is False
    assert composed.enable_repo_context is False
    assert composed.enable_tool_search is False
    assert composed.enable_memory is False
    assert composed.enable_conversation_search is False
    assert composed.enable_subagents is False
    assert composed.request_limit == 21


# --- 7. CLI ----------------------------------------------------------------------


def test_cli_args_map_to_writing_task(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("x", encoding="utf-8")
    args = parse_args(
        [
            "--task",
            "beauty-20260818-001",
            "--assignment",
            "根据素材写一篇公众号文章。",
            "--audience",
            "普通消费者",
            "--material",
            str(a),
            "--constraints",
            "约1800字",
            "--constraints",
            "不虚构",
            "--run-id",
            "run-1",
            "--rights",
            "user-provided",
        ]
    )
    task = WritingTask(
        article_id=args.task,
        assignment=args.assignment,
        audience=args.audience,
        constraints=list(args.constraints),
    )
    assert task.article_id == "beauty-20260818-001"
    assert task.constraints == ["约1800字", "不虚构"]
    assert task.audience == "普通消费者"
    assert args.material == [str(a)]


def test_run_production_task_requires_material_paths(tmp_path):
    settings = _settings(tmp_path)
    task = WritingTask(article_id="x", assignment="写。")
    with pytest.raises(ValueError, match="at least one material"):
        run_production_task(settings, task=task, material_paths=[])
