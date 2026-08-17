"""Sanlian Host Fixture adapter contract tests (no model calls).

The adapter is a DATA ENTRY: resolve path, exact bytes, sha256, rights
metadata, ACE ingest -> real M id. It must never decide techniques/structure
and never call an LLM — the pure-path tests run with zero ACE and zero model.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
sys.path[:0] = [
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from zuaef_ace_writing.writing_toolset import DEFAULT_ACE_ROOT

from examples.sanlian_fixture import (
    RIGHTS_STATUSES,
    RightsError,
    SanlianFixture,
    load_sanlian_fixture,
)

ACE = Path(str(DEFAULT_ACE_ROOT))
ACE_AVAILABLE = (ACE / "tools" / "ctx.py").is_file()

FIXTURE_TEXT = (
    '---\ntitle: "便利店奇妙夜-三联生活网"\ntype: book-source\n---\n\n'
    "# 便利店奇妙夜\n\n"
    "周五晚上，我刷到一条公众号消息，“便利店被搬空了”。\n"
    "不足50平方米的小店，如今每个角落都挤满了人。\n"
    "下一篇：天下（1399）\n"
)
FIXTURE_BYTES = FIXTURE_TEXT.encode("utf-8")
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()


@pytest.fixture
def fixture_file(tmp_path: Path) -> Path:
    path = tmp_path / "22-便利店奇妙夜.md"
    path.write_bytes(FIXTURE_BYTES)
    return path


def test_pure_entry_resolves_reads_hashes_and_rights(fixture_file: Path):
    fixture = load_sanlian_fixture(fixture_file, rights="study-only")
    assert isinstance(fixture, SanlianFixture)
    assert fixture.text == FIXTURE_TEXT  # exact decoded bytes, nothing else
    assert fixture.sha256 == FIXTURE_SHA256
    assert fixture.source_byte_length == len(FIXTURE_BYTES)
    assert fixture.projected_char_length == len(FIXTURE_TEXT)
    assert fixture.rights == "study-only"
    assert fixture.material_id is None  # no article_id -> no ACE ingest
    assert fixture.source_path == fixture_file.resolve()
    assert (
        fixture.source_ref
        == f"wiki-sanlian-life-weekly-2026-30/sources/{fixture_file.name}"
    )
    # the hash binds the projected text: recomputing over fixture.text must
    # reproduce the recorded sha256 exactly
    assert hashlib.sha256(fixture.text.encode("utf-8")).hexdigest() == FIXTURE_SHA256


def test_to_record_is_the_receipt_line(fixture_file: Path):
    fixture = load_sanlian_fixture(fixture_file, rights="study-only")
    record = fixture.to_record()
    assert record["source_sha256"] == FIXTURE_SHA256
    assert record["source_byte_length"] == len(FIXTURE_BYTES)
    assert record["projected_char_length"] == len(FIXTURE_TEXT)
    assert record["rights"] == "study-only"
    assert record["material_id"] is None
    assert "text" not in record  # receipt line carries identity, not content


def test_custom_source_ref_and_rights_are_caller_owned(fixture_file: Path):
    fixture = load_sanlian_fixture(
        fixture_file,
        rights="user-provided",
        source_ref="customer-upload/22-便利店奇妙夜.md",
    )
    assert fixture.rights == "user-provided"
    assert fixture.source_ref == "customer-upload/22-便利店奇妙夜.md"


@pytest.mark.parametrize("rights", RIGHTS_STATUSES)
def test_all_rights_statuses_accepted(fixture_file: Path, rights: str):
    assert load_sanlian_fixture(fixture_file, rights=rights).rights == rights


def test_invalid_rights_rejected(fixture_file: Path):
    with pytest.raises(RightsError):
        load_sanlian_fixture(fixture_file, rights="pirated")


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_sanlian_fixture(tmp_path / "nope.md")


@pytest.mark.skipif(not ACE_AVAILABLE, reason=f"ACE repo not found at {ACE}")
def test_ace_ingest_binds_real_material_id(fixture_file: Path):
    """Step 5 of the contract: ingest -> the REAL M id from the ACE index,
    idempotent on reload (ACE dedupes by sha256)."""
    article_id = f"slc-test-{uuid.uuid4().hex[:12]}"
    ws = ACE / "workspaces" / article_id
    try:
        fixture = load_sanlian_fixture(
            fixture_file,
            rights="study-only",
            article_id=article_id,
            title="便利店奇妙夜",
        )
        assert fixture.material_id == "M001"
        # the ACE index row must carry our exact sha256
        index = ws / "materials.jsonl"
        assert index.is_file()
        rows = [
            line
            for line in index.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(rows) == 1
        import json

        row = json.loads(rows[0])
        assert row["sha256"] == FIXTURE_SHA256
        assert row["bytes"] == len(FIXTURE_BYTES)
        # reloading the same fixture into the same workspace is idempotent
        again = load_sanlian_fixture(
            fixture_file,
            rights="study-only",
            article_id=article_id,
            title="便利店奇妙夜",
        )
        assert again.material_id == "M001"
    finally:
        shutil.rmtree(ws, ignore_errors=True)
