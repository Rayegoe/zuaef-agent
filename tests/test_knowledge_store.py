from pathlib import Path

import pytest

from zuaef_agent.knowledge_store import KnowledgeStore


def test_write_search_read_index_and_run_provenance(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    rel = store.write_doc(
        knowledge_id="concepts/thin-harness",
        title="Thin Harness",
        body=(
            "# Thin Harness\n\nKeep the runtime small and capabilities "
            "explicit.\n\n## Sources\n- [PydanticAI docs](https://ai.pydantic.dev/)"
        ),
        tags=["agent", "architecture"],
        run_id="run-1",
    )
    assert rel == "knowledge/concepts/thin-harness.md"
    text = store.read_doc("concepts/thin-harness")
    assert "Thin Harness" in text
    # Real source URLs live in the document body, where a reader can follow
    # them — not in a frontmatter field pretending to prove support.
    assert "https://ai.pydantic.dev/" in text
    assert store.search("capabilities explicit")[0]["path"] == rel
    assert store.list_generated_by_run("run-1") == [rel]
    assert store.list_generated_by_run("other") == []
    assert "thin-harness" in (tmp_path / "knowledge" / "index.md").read_text()


def test_write_without_sources_is_allowed(tmp_path: Path):
    """v1.2 T007: no semantic type or source-requirement gate — a plain
    document stores fine; no kernel code claims a source field proves
    content."""
    store = KnowledgeStore(tmp_path)
    rel = store.write_doc(
        knowledge_id="notes/quick-observation",
        title="Observation",
        body="A plain note with no sources at all.",
        run_id="run-9",
    )
    assert rel == "knowledge/notes/quick-observation.md"
    assert store.list_generated_by_run("run-9") == [rel]


def test_rejects_path_traversal(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    with pytest.raises(ValueError):
        store.write_doc(
            knowledge_id="../escape",
            title="Nope",
            body="Nope",
        )
