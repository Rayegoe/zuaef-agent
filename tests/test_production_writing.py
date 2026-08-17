"""Production writing path contract tests (SPEC review 2026-08-17).

Covers the host-projected WritingContext machinery WITHOUT any model call:

  1. bundle assembly     — task/material/sources/techniques/editorial_memory/
                           constraints present; candidates come from the
                           compiled sequential inputs (exact join);
  2. render              — the projected prompt carries material, technique
                           ids and evidence ids, and the constraints;
  3. toolset surface     — exactly {save_artifact, retrieve_more_context};
                           no budget/withdrawal machinery on the production
                           toolset;
  4. composition         — the production agent carries EditorialControl
                           Capability wired to the compiled corpus store
                           (seeds + 20 corpus_observation);
  5. artifact read       — final_artifact_text reads the run snapshot, never
                           the run summary;
  6. metrics             — ModelResponse/ToolCallPart counting over a
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
    candidate_technique_ids_for,
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


def test_bundle_shape_and_candidates_from_compiled():
    bundle = prepare_writing_context(task_id="T01", material=MATERIAL, title="T01")
    assert bundle["task"] == {"id": "T01", "title": "T01", "audience": ""}
    assert bundle["material"] == MATERIAL
    assert bundle["sources"] == [
        {"id": "S1", "kind": "material", "label": "T01", "material_ids": ["M001"]}
    ]
    # T01's candidates come from the compiled sequential inputs exact join
    expected = candidate_technique_ids_for("T01")
    assert expected, "compiled sequential inputs must list candidates for T01"
    assert [t["id"] for t in bundle["techniques"]] == expected
    # every technique record carries the action/instruction core
    assert all(t["action"] and t["instruction"] for t in bundle["techniques"])
    # editorial memory = corpus evidence for the same candidates
    memory_ids = [e["id"] for e in bundle["editorial_memory"]]
    assert memory_ids == [f"corpus.{tid}" for tid in expected]
    assert all(e["weight"] == 0.75 for e in bundle["editorial_memory"])
    assert all(e["approved_by"] == "pack-curation:v0.1" for e in bundle["editorial_memory"])
    assert bundle["constraints"]


def test_render_carries_material_techniques_memory_constraints():
    bundle = prepare_writing_context(task_id="T01", material=MATERIAL, title="T01")
    prompt = render_writing_context(bundle)
    assert "## WritingContext" in prompt
    assert MATERIAL.splitlines()[1] in prompt  # material body projected
    assert "### relevant techniques" in prompt
    for t in bundle["techniques"][:2]:
        assert t["id"] in prompt
    assert "corpus.T011" in prompt  # T01 candidate evidence projected
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


def test_composition_wires_editorial_capability_with_corpus_store():
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
    # production surface must NOT carry generic filesystem/knowledge machinery
    # (measured: a model given list_directory/find_files wasted 12 requests
    # wandering instead of writing)
    assert not any("FileSystem" in type(c).__name__ for c in caps)
    assert not any("Knowledge" in type(c).__name__ for c in caps)
    assert not any("Planning" in type(c).__name__ for c in caps)
    assert not any("Skills" in type(c).__name__ for c in caps)


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
        ModelResponse(parts=[ToolCallPart(tool_name="retrieve_more_context", args="{}")]),
        ModelRequest(parts=[]),
        ModelResponse(parts=[TextPart(content="done")]),
    ]
    m = metrics_from_messages(messages)
    assert m["model_requests"] == 3
    assert m["tool_calls"] == 2
    assert m["tool_names"] == ["save_artifact", "retrieve_more_context"]


def test_unknown_task_yields_empty_candidates():
    assert candidate_technique_ids_for("T999") == []
