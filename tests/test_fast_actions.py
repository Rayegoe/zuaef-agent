"""Deterministic Fast Action Gate tests (Task Boundary Repair v0.1).

The gate exists to keep a mechanical "record this text" request from becoming
an expensive reasoning run.  These tests pin both sides: high-confidence
persist forms are handled with verbatim provenance, while ambiguous references
and compound requests fall through untouched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from zuaef_agent.fast_actions import (
    extract_explicit_persist_content,
    try_fast_action,
)
from zuaef_agent.knowledge_store import KnowledgeStore

NOW = datetime(2026, 9, 11, 8, 30, 15, tzinfo=UTC)
CASE_B = (
    "中东冲突 / 能源供应风险 → 原油暴涨 → 全球通胀预期重新抬头 → "
    "美债收益率飙升 / 加息预期增强 → 全球股票估值承压 → "
    "亚洲股市普跌 → A股在自身缩量、存量博弈状态下放大下跌。"
)


def _note_text(tmp_path: Path) -> str:
    docs = KnowledgeStore(tmp_path).list_docs()
    assert len(docs) == 1
    return KnowledgeStore(tmp_path).read_doc(
        docs[0].removeprefix("knowledge/").removesuffix(".md")
    )


def test_trailing_dash_marker_is_handled_and_preserves_verbatim(tmp_path):
    result = try_fast_action(
        text=f"{CASE_B}————记录下来",
        workspace_root=tmp_path,
        now=NOW,
    )
    assert result.handled is True
    assert result.reply is not None
    assert "已记录" in result.reply
    text = _note_text(tmp_path)
    assert "来源：用户原文" in text
    assert "验证状态：not_requested" in text
    assert f"原文：\n\n{CASE_B}\n" in text
    # No unsolicited analysis or enrichment.
    assert "金融券商领跌" not in text
    assert "与今天截面吻合" not in text
    assert "因此方向得到了验证" not in text


def test_trailing_newline_marker_is_handled(tmp_path):
    content = "用户提供的一段完整结论。"
    result = try_fast_action(
        text=f"{content}\n记录下来",
        workspace_root=tmp_path,
        now=NOW,
    )
    assert result.handled is True
    assert extract_explicit_persist_content(f"{content}\n记录下来") == content
    assert content in _note_text(tmp_path)


def test_embedded_prefix_forms_are_handled(tmp_path):
    content = "把下面这段保存下来：完整内容会原样保留。"
    extracted = extract_explicit_persist_content(content)
    # "把下面这段保存下来：" is itself the prefix; the remainder is content.
    assert extracted == "完整内容会原样保留。"
    result = try_fast_action(text=content, workspace_root=tmp_path, now=NOW)
    assert result.handled is True
    assert "完整内容会原样保留。" in _note_text(tmp_path)


def test_record_the_following_prefix_form_is_handled(tmp_path):
    result = try_fast_action(
        text="记录以下内容：\n第一条\n第二条",
        workspace_root=tmp_path,
        now=NOW,
    )
    assert result.handled is True
    text = _note_text(tmp_path)
    assert "第一条\n第二条" in text


def test_ambiguous_reference_is_rejected():
    for text in (
        "把刚才那个记下来",
        "记录这个",
        "这个存一下",
        "把上面的结论记下来",
        "刚才那个————记录下来",
        "刚才那个内容————记录下来",
        "上面————记录下来",
    ):
        assert extract_explicit_persist_content(text) is None, text


def test_compound_request_is_rejected():
    for text in (
        "记录并验证一下",
        "记录下来并分析",
        "记录后告诉我是否正确",
        "把上面的结论作为研究假设保存",
        "把这段记录下来，然后帮我验证这条因果链是否成立。",
        "记录以下内容：\n然后帮我验证这条因果链是否成立。",
        "记录以下内容：\n核查这条因果链",
    ):
        assert extract_explicit_persist_content(text) is None, text


def test_document_id_is_under_notes_and_never_hypotheses(tmp_path):
    result = try_fast_action(
        text="这只是一个记录，不是研究假设。————记录下来",
        workspace_root=tmp_path,
        now=NOW,
    )
    assert result.handled is True
    docs = KnowledgeStore(tmp_path).list_docs()
    assert len(docs) == 1
    assert docs[0].startswith("knowledge/notes/2026-09-11/")
    assert "hypotheses/" not in docs[0]
    assert "facts/" not in docs[0]
    assert "verified/" not in docs[0]
