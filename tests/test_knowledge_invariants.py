from __future__ import annotations

from pathlib import Path

import pytest

from zuaef_agent.core import FILESYSTEM_PROTECTED_PATTERNS
from zuaef_agent.knowledge_capability import Knowledge
from zuaef_agent.knowledge_store import (
    KNOWN_TYPES,
    MAX_SEARCH_RESULTS,
    REQUIRED_SOURCE_TYPES,
    KnowledgeStore,
)
from zuaef_agent.models import SourceRef


def test_reserved_and_invalid_ids_rejected(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    for bad_id in ("index", "INDEX", "../escape", "bad id", ""):
        with pytest.raises(ValueError):
            store.path_for(bad_id)


def test_source_rules_by_type(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    for doc_type in sorted(REQUIRED_SOURCE_TYPES):
        with pytest.raises(ValueError, match="requires at least one source"):
            store.write_doc(knowledge_id=f"concepts/{doc_type}", doc_type=doc_type, title="t", body="b")
        store.write_doc(
            knowledge_id=f"concepts/{doc_type}",
            doc_type=doc_type,
            title="t",
            body="b",
            sources=[SourceRef(id="s", resource="file:///x")],
            run_id="r1",
        )
    for doc_type in ("project-note", "decision", "user-authored-note"):
        store.write_doc(knowledge_id=f"notes/{doc_type}", doc_type=doc_type, title="t", body="b")
    with pytest.raises(ValueError, match="unknown knowledge type"):
        store.write_doc(knowledge_id="notes/weird", doc_type="rumor", title="t", body="b")


def test_search_limit_bounds(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    store.write_doc(
        knowledge_id="concepts/x",
        doc_type="concept",
        title="x",
        body="needle here",
        sources=[SourceRef(id="s", resource="file:///x")],
    )
    with pytest.raises(ValueError):
        store.search("needle", limit=0)
    with pytest.raises(ValueError):
        store.search("needle", limit=-1)
    with pytest.raises(ValueError):
        store.search("needle", limit=MAX_SEARCH_RESULTS + 1)
    assert store.search("needle", limit=MAX_SEARCH_RESULTS)


def test_symlink_escape_rejected(tmp_path: Path):
    workspace = tmp_path / "workspace"
    knowledge = workspace / "knowledge" / "sub"
    knowledge.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "evil.md").write_text("evil", encoding="utf-8")
    (knowledge / "link").symlink_to(outside)

    store = KnowledgeStore(workspace)
    with pytest.raises(ValueError):
        store.path_for("sub/link/evil")


def test_atomic_write_and_rebuildable_index(tmp_path: Path):
    store = KnowledgeStore(tmp_path)
    store.write_doc(
        knowledge_id="concepts/a",
        doc_type="concept",
        title="a",
        body="body a",
        sources=[SourceRef(id="s", resource="file:///a")],
        run_id="r1",
    )
    (tmp_path / "knowledge" / "index.md").write_text("corrupt garbage", encoding="utf-8")
    store.rebuild_index()
    index = (tmp_path / "knowledge" / "index.md").read_text(encoding="utf-8")
    assert "concepts/a" in index
    assert not list(tmp_path.glob("knowledge/**/*.tmp")), "temp files must not linger after atomic replace"


def test_filesystem_protects_knowledge_area():
    assert "knowledge/*" in FILESYSTEM_PROTECTED_PATTERNS
    capability = Knowledge()
    assert capability is not None  # sole write entry point for knowledge/**
    assert "concept" in REQUIRED_SOURCE_TYPES
    assert REQUIRED_SOURCE_TYPES <= KNOWN_TYPES
