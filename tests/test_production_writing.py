"""Production writing path contract tests (SPEC review 2026-08-17, round 2).

Covers the host-projected WritingContext machinery WITHOUT any model call:

  1. bundle assembly     — task/material/sources/techniques/editorial_memory/
                           examples/constraints present; ALL selection is
                           caller-provided — a non-benchmark task id (e.g. a
                           real customer article) must not crash and must not
                           silently pull benchmark assets;
  2. render              — the projected prompt carries material, technique
                           ids, evidence ids, examples and constraints;
  3. toolset surface     — save_artifact only by default; escape hatch is
                           opt-in; no budget/withdrawal machinery;
  4. composition         — build_production_agent goes through the SHARED
                           seam (core.build_agent) with the generic surfaces
                           OFF (filesystem/knowledge/planning/skills) and
                           receipts + editorial capability ON;
  5. evidence wiring     — evidence_path is honored by the composition
                           (the --evidence CLI arg is not a dead knob);
  6. artifact read       — final_artifact_text reads the run snapshot, never
                           the run summary;
  7. metrics             — ModelResponse/ToolCallPart counting over a
                           synthetic message history.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
BENCH = REPO / "benchmarks" / "editorial-learning"
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from zuaef_ace_writing.editorial import (
    EditorialControlCapability,
)

from examples.production_writing import (
    ProductionWritingToolset,
    build_production_toolset,
    final_artifact_text,
    metrics_from_messages,
    prepare_writing_context,
    render_writing_context,
)

MATERIAL = (
    "# Material for test\n\n"
    "The iterater study describes 100 revision intents across 8,302 edits. "
    "Human revisers labelled each intent; 105134 is one annotated document. "
    "The paper reports that clarity edits dominate at 34.6%."
)

TECHNIQUE = {
    "id": "T001",
    "action": "return_to_observation",
    "instruction": "回到材料的具体观察。",
    "preserve": ["claims"],
    "anti_pattern": ["fabricate_scene"],
    "rationale": "curator rationale",
}
EVIDENCE = {
    "id": "corpus.T001",
    "action": "return_to_observation",
    "directive": "回到材料的具体观察。",
    "rationale": "r",
    "weight": 0.75,
    "approved_by": "pack-curation:v0.1",
    "source_ref": "pack:sanlian-172807#technique:T001",
}


def test_bundle_shape_with_caller_provided_selection():
    bundle = prepare_writing_context(
        task_id="beauty-wechat-20260818-001",
        material=MATERIAL,
        title="某客户公众号文章",
        audience="都市女性读者",
        techniques=[TECHNIQUE],
        editorial_memory=[EVIDENCE],
        examples=["<一段示范开头>"],
    )
    assert bundle["task"] == {
        "id": "beauty-wechat-20260818-001",
        "title": "某客户公众号文章",
        "audience": "都市女性读者",
    }
    assert bundle["material"] == MATERIAL
    assert bundle["sources"] == [
        {"id": "S1", "kind": "material", "label": "某客户公众号文章", "material_ids": ["M001"]}
    ]
    assert [t["id"] for t in bundle["techniques"]] == ["T001"]
    assert [e["id"] for e in bundle["editorial_memory"]] == ["corpus.T001"]
    assert bundle["examples"] == ["<一段示范开头>"]
    assert bundle["constraints"]


def test_non_benchmark_task_gets_no_implicit_selection():
    """Production must NOT depend on benchmark task ids / sequential_inputs:
    an unknown customer task id yields a clean bundle with no techniques or
    memory sections — the caller decides what to include."""
    bundle = prepare_writing_context(
        task_id="wordpress-post-52", material=MATERIAL, title="WP post"
    )
    assert bundle["techniques"] == []
    assert bundle["editorial_memory"] == []
    assert bundle["examples"] == []
    prompt = render_writing_context(bundle)
    assert "### relevant techniques" not in prompt
    assert "### relevant editorial memory" not in prompt
    assert "### examples" not in prompt
    assert "### material" in prompt


def test_render_carries_material_techniques_memory_examples_constraints():
    bundle = prepare_writing_context(
        task_id="T01",
        material=MATERIAL,
        title="T01",
        techniques=[TECHNIQUE],
        editorial_memory=[EVIDENCE],
        examples=["<example one>"],
    )
    prompt = render_writing_context(bundle)
    assert "## WritingContext" in prompt
    assert MATERIAL.splitlines()[1] in prompt
    assert "### relevant techniques" in prompt
    assert "T001" in prompt and "return_to_observation" in prompt
    assert "corpus.T001" in prompt
    assert "<example one>" in prompt
    assert "### constraints" in prompt
    assert "save_artifact once" in prompt


def test_production_toolset_surface_is_minimal():
    toolset = build_production_toolset()
    assert isinstance(toolset, ProductionWritingToolset)
    # default surface: save_artifact ONLY (escape hatch is opt-in; a model
    # offered a fetch tool used it ~10x instead of writing — measured)
    assert set(toolset.tools.keys()) == {"save_artifact"}
    assert not hasattr(toolset, "_BUDGETED")
    assert not hasattr(toolset, "_remaining")


def test_escape_hatch_is_opt_in():
    toolset = build_production_toolset(escape_hatch=True)
    assert set(toolset.tools.keys()) == {"save_artifact", "retrieve_more_context"}


def test_composition_through_shared_seam_with_minimal_surface():
    from examples.production_writing import build_production_agent
    from zuaef_agent.config import AgentSettings

    settings = AgentSettings(
        model="test",
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    agent = build_production_agent(settings, run_id="prod-test")
    caps = agent.root_capability.capabilities
    editorial = [c for c in caps if isinstance(c, EditorialControlCapability)]
    assert len(editorial) == 1
    store = editorial[0]._store if hasattr(editorial[0], "_store") else editorial[0].store
    corpus = [e for e in store._entries if e.source_type == "corpus_observation"]
    assert len(corpus) == 20  # compiled corpus, not just the 6 seeds
    assert all(e.weight == 0.75 for e in corpus)
    assert any(isinstance(t, ProductionWritingToolset) for t in agent.toolsets)
    # shared seam: receipts stay ON; generic model-visible surfaces are OFF
    # (measured: a model given list_directory/find_files wasted 12 requests
    # wandering instead of writing)
    assert any("StepPersistence" in type(c).__name__ for c in caps)
    assert not any("FileSystem" in type(c).__name__ for c in caps)
    assert not any("Knowledge" in type(c).__name__ for c in caps)
    assert not any("Planning" in type(c).__name__ for c in caps)
    assert not any("Skills" in type(c).__name__ for c in caps)
    assert not any("ToolOutputLimits" in type(c).__name__ for c in caps)


def test_evidence_path_is_honored(tmp_path):
    """The --evidence knob must reach the composition (was a dead parameter)."""
    from examples.production_writing import build_production_agent
    from zuaef_agent.config import AgentSettings

    custom = tmp_path / "custom_evidence.jsonl"
    custom.write_text(
        '{"id":"corpus.X001","source_type":"corpus_observation",'
        '"source_ref":"pack:x#technique:X001","situation_tags":["drafting"],'
        '"trigger_signals":[],"action":"delay_interpretation",'
        '"directive":"custom directive","rationale":"r","weight":0.75,'
        '"approved_by":"pack-curation:v0.1","before_excerpt":"","after_excerpt":""}\n',
        encoding="utf-8",
    )
    settings = AgentSettings(
        model="test",
        workspace_root=REPO / "workspace",
        runtime_state_root=REPO / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    agent = build_production_agent(settings, run_id="prod-ev", evidence_path=custom)
    caps = agent.root_capability.capabilities
    editorial = next(c for c in caps if isinstance(c, EditorialControlCapability))
    store = editorial._store if hasattr(editorial, "_store") else editorial.store
    ids = [e.id for e in store._entries]
    assert "corpus.X001" in ids  # custom file loaded
    assert "corpus.T001" not in ids  # default compiled corpus NOT loaded


def test_cli_evidence_default_is_compiled_corpus():
    """CLI without --evidence must keep seeds + compiled corpus (regression:
    a None pass-through silently downgraded the store to builtin seeds)."""
    from examples.production_writing import COMPILED_EVIDENCE, resolve_evidence_arg

    assert resolve_evidence_arg(None) == COMPILED_EVIDENCE
    assert resolve_evidence_arg("") == COMPILED_EVIDENCE
    assert resolve_evidence_arg("/tmp/custom.jsonl") == Path("/tmp/custom.jsonl")


def test_final_artifact_text_reads_snapshot_not_summary(tmp_path):
    run_id = "prod-t01"
    snapshot = tmp_path / "artifacts" / run_id / "final.md"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("# The real article\n\nBody with 42 anchors.", encoding="utf-8")
    text, path = final_artifact_text(tmp_path, run_id)
    assert text.startswith("# The real article")
    assert path.endswith("final.md")
    # missing snapshot -> empty text, honest path
    text2, _ = final_artifact_text(tmp_path, "prod-nosuch")
    assert text2 == ""


def test_metrics_counts_model_responses_and_tool_calls():
    messages = [
        ModelRequest(parts=[]),
        ModelResponse(parts=[TextPart(content="plan"), ToolCallPart(tool_name="save_artifact", args="{}")]),
        ModelRequest(parts=[]),
        ModelResponse(parts=[ToolCallPart(tool_name="save_artifact", args="{}")]),
        ModelRequest(parts=[]),
        ModelResponse(parts=[TextPart(content="done")]),
    ]
    m = metrics_from_messages(messages)
    assert m["model_requests"] == 3
    assert m["tool_calls"] == 2
    assert m["tool_names"] == ["save_artifact", "save_artifact"]
