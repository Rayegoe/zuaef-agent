"""Host fixture adapter contract tests — generic material file + case (no model).

The adapter is a DATA ENTRY: resolve path, exact bytes, sha256, rights
metadata, ACE ingest -> real M ids. It must never decide techniques/structure
and never call an LLM — the pure-path tests run with zero ACE and zero model.
"""

from __future__ import annotations

import hashlib
import json
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

from examples.host_fixture import (
    RightsError,
    build_case_sources,
    load_material_case,
    load_material_file,
    render_case_material,
)

ACE = Path(str(DEFAULT_ACE_ROOT))
ACE_AVAILABLE = (ACE / "tools" / "ctx.py").is_file()

TEXT_A = "采访转录：\n运营负责人：我们现在大概三千个号。\n"
TEXT_B = "会议速记：\n- 客户报数：约3000个号。\n- 禁止写“平台指纹识别”。\n"
SHA_A = hashlib.sha256(TEXT_A.encode("utf-8")).hexdigest()
SHA_B = hashlib.sha256(TEXT_B.encode("utf-8")).hexdigest()


@pytest.fixture
def case_dir(tmp_path: Path) -> Path:
    raw = tmp_path / "01-content-team" / "raw"
    raw.mkdir(parents=True)
    (raw / "interview.txt").write_text(TEXT_A, encoding="utf-8")
    (raw / "meeting-notes.md").write_text(TEXT_B, encoding="utf-8")
    return tmp_path / "01-content-team"


def test_single_file_pure_entry(case_dir: Path):
    f = load_material_file(case_dir / "raw" / "interview.txt", rights="user-provided")
    assert f.text == TEXT_A
    assert f.sha256 == SHA_A
    assert f.source_byte_length == len(TEXT_A.encode("utf-8"))
    assert f.projected_char_length == len(TEXT_A)
    assert f.rights == "user-provided"
    assert f.material_id is None
    assert f.source_ref == str((case_dir / "raw" / "interview.txt").resolve())
    # the hash binds the projected text
    assert hashlib.sha256(f.text.encode("utf-8")).hexdigest() == SHA_A


def test_single_file_invalid_rights(case_dir: Path):
    with pytest.raises(RightsError):
        load_material_file(case_dir / "raw" / "interview.txt", rights="pirated")


def test_case_pure_entry_orders_and_hashes_files(case_dir: Path):
    case = load_material_case(case_dir, rights="user-provided")
    assert case.case_name == "01-content-team"
    assert [f.source_ref for f in case.files] == [
        "cases/01-content-team/raw/interview.txt",
        "cases/01-content-team/raw/meeting-notes.md",
    ]
    assert [f.sha256 for f in case.files] == [SHA_A, SHA_B]
    assert [f.material_id for f in case.files] == [None, None]
    assert all(f.rights == "user-provided" for f in case.files)
    # record shape: identity only, no text
    record = case.to_record()
    assert record["files"][0]["source_sha256"] == SHA_A
    assert "text" not in record["files"][0]


def test_case_missing_raw_dir_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_material_case(tmp_path / "nope")


def test_render_case_material_carries_per_file_hash_separators(case_dir: Path):
    case = load_material_case(case_dir, rights="user-provided")
    rendered = render_case_material(case)
    assert (
        f"<file cases/01-content-team/raw/interview.txt> (sha256: {SHA_A})" in rendered
    )
    assert (
        f"<file cases/01-content-team/raw/meeting-notes.md> (sha256: {SHA_B})"
        in rendered
    )
    assert TEXT_A in rendered and TEXT_B in rendered
    # deterministic: exact text is reproducible byte for byte
    assert render_case_material(case) == rendered


def test_build_case_sources_ledger(case_dir: Path):
    case = load_material_case(case_dir, rights="user-provided")
    sources = build_case_sources(case)
    assert [s["id"] for s in sources] == ["S1", "S2"]
    assert [s["material_ids"] for s in sources] == [["M001"], ["M002"]]
    assert [s["sha256"] for s in sources] == [SHA_A, SHA_B]
    assert all(
        s["kind"] == "material" and s["rights"] == "user-provided" for s in sources
    )
    assert [s["source_ref"] for s in sources] == [
        "cases/01-content-team/raw/interview.txt",
        "cases/01-content-team/raw/meeting-notes.md",
    ]


@pytest.mark.skipif(not ACE_AVAILABLE, reason=f"ACE repo not found at {ACE}")
def test_case_ace_ingest_binds_real_m_ids(case_dir: Path):
    """All files ingest in one call -> M001/M002, idempotent on reload."""
    article_id = f"hf-test-{uuid.uuid4().hex[:12]}"
    ws = ACE / "workspaces" / article_id
    try:
        case = load_material_case(
            case_dir, rights="user-provided", article_id=article_id, title="case"
        )
        assert [f.material_id for f in case.files] == ["M001", "M002"]
        index = ws / "materials.jsonl"
        rows = [
            json.loads(line)
            for line in index.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(rows) == 2
        assert {r["sha256"] for r in rows} == {SHA_A, SHA_B}
        again = load_material_case(
            case_dir, rights="user-provided", article_id=article_id, title="case"
        )
        assert [f.material_id for f in again.files] == ["M001", "M002"]
        assert (
            len(
                [
                    line
                    for line in index.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            )
            == 2
        )  # dedupe by sha256, no growth
    finally:
        shutil.rmtree(ws, ignore_errors=True)
