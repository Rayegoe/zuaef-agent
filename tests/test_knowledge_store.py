from pathlib import Path

import pytest

from zuaef_agent.knowledge_store import KnowledgeStore
from zuaef_agent.models import SourceRef


def test_write_search_read_index_and_run_provenance(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    rel = store.write_doc(
        knowledge_id="concepts/thin-harness",
        doc_type="Concept",
        title="Thin Harness",
        body="# Thin Harness\n\nKeep the runtime small and capabilities explicit.",
        tags=["agent", "architecture"],
        sources=[SourceRef(id="src-1", resource="https://example.test/source", evidence="12:31-13:46")],
        run_id="run-1",
    )
    assert rel == "knowledge/concepts/thin-harness.md"
    text = store.read_doc("concepts/thin-harness")
    assert "Thin Harness" in text
    assert "https://example.test/source" in text
    assert store.search("capabilities explicit")[0]["path"] == rel
    assert store.list_generated_by_run("run-1") == [rel]
    assert store.list_generated_by_run("other") == []
    assert "thin-harness" in (tmp_path / "knowledge" / "index.md").read_text()


def test_rejects_path_traversal(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    with pytest.raises(ValueError):
        store.write_doc(
            knowledge_id="../escape",
            doc_type="Concept",
            title="Nope",
            body="Nope",
        )
