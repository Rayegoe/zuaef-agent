"""Deterministic EPUB conversion and contiguous writing-corpus retrieval."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from zuaef_ace_writing import writing_toolset
from zuaef_ace_writing.epub_corpus import (
    CorpusError,
    render_corpus_search,
    search_corpus,
)

from tools.epub_to_corpus import CorpusConversionError, convert_epub


def _make_epub(path: Path) -> None:
    toc = """<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx">
  <navMap>
    <navPoint id="menu"><navLabel><text>总目录</text></navLabel><content src="menu.html"/></navPoint>
    <navPoint id="source"><navLabel><text>来源甲</text></navLabel><content src="source.html"/>
      <navPoint id="one"><navLabel><text>文章甲</text></navLabel><content src="one.html"/></navPoint>
      <navPoint id="two"><navLabel><text>文章乙</text></navLabel><content src="two.html"/></navPoint>
    </navPoint>
    <navPoint id="donation"><navLabel><text>如果喜欢，欢迎捐赠</text></navLabel><content src="donation.html"/></navPoint>
  </navMap>
</ncx>
"""
    one = """<html><head><title>ignored</title></head><body><div>
      <h2>文章甲</h2><section><p>第一段：保留顺序。</p><p>第二段：具体场景。<a href="https://example.com/article">原文链接</a></p><p>第三段：仍然属于同一篇文章。</p></section>
    </div></body></html>"""
    two = """<html><body><div><h2>文章乙</h2><p>乙文第一段。</p><p>乙文第二段。</p></div></body></html>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("toc.ncx", toc)
        archive.writestr("menu.html", "<p>menu</p>")
        archive.writestr("source.html", "<p>source</p>")
        archive.writestr("donation.html", "<p>donation</p>")
        archive.writestr("one.html", one)
        archive.writestr("two.html", two)


def _body(article_path: Path) -> str:
    return article_path.read_text(encoding="utf-8").split("\n---\n", 1)[1].strip()


def test_converter_preserves_articles_and_external_url(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    output = tmp_path / "corpus" / "2026-08-20"

    receipt = convert_epub(epub, output)
    rows = [json.loads(line) for line in (output / "manifest.jsonl").read_text().splitlines()]

    assert receipt["article_count"] == 2
    assert receipt["source_count"] == 1
    assert len(rows) == 2
    assert rows[0]["title"] == "文章甲"
    assert rows[0]["source"] == "来源甲"
    assert rows[0]["url"] == "https://example.com/article"
    assert rows[1]["url"] is None

    first_body = _body(output / rows[0]["article_path"])
    assert first_body.split("\n\n") == [
        "第一段：保留顺序。",
        "第二段：具体场景。原文链接",
        "第三段：仍然属于同一篇文章。",
    ]
    assert "hash" not in rows[0]
    assert "epub_sha256" not in rows[0]
    assert len(list((output / "articles").glob("*.md"))) == 2
    receipt_json = json.loads((output / "receipt.json").read_text())
    assert "epub_sha256" not in receipt_json
    assert "manifest_sha256" not in receipt_json


def test_converter_is_deterministic_across_fresh_batches(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    first = tmp_path / "first"
    second = tmp_path / "second"

    convert_epub(epub, first)
    convert_epub(epub, second)

    for relative in (
        "manifest.jsonl",
        "receipt.json",
        "articles/WML-20260820-01-001.md",
        "articles/WML-20260820-01-002.md",
    ):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_converter_rejects_nonempty_output_and_bad_epub(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    output = tmp_path / "output"
    output.mkdir()
    (output / "existing").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="not empty"):
        convert_epub(epub, output)

    bad = tmp_path / "bad.epub"
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("content.html", "<p>not an NCX</p>")
    with pytest.raises(CorpusConversionError, match="no NCX"):
        convert_epub(bad, tmp_path / "bad-output")


def test_search_returns_contiguous_windows_with_provenance(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    output = tmp_path / "corpus"
    convert_epub(epub, output)

    windows = search_corpus(output, "具体场景", max_windows=2)
    assert windows
    window = windows[0]
    assert window.article_id == "WML-20260820-01-001"
    assert window.start_paragraph == 0
    assert window.end_paragraph == 3
    assert window.text.index("第一段") < window.text.index("第二段") < window.text.index("第三段")

    rendered = render_corpus_search(windows)
    assert "source_entry: one.html" in rendered
    assert "hash:" not in rendered
    assert "contiguous_paragraphs: 1-3" in rendered
    assert "具体场景" in rendered


def test_search_fails_on_missing_article(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    output = tmp_path / "corpus"
    convert_epub(epub, output)
    article = output / "articles/WML-20260820-01-001.md"
    article.unlink()

    with pytest.raises(CorpusError, match="article_path escapes batch or is missing"):
        search_corpus(output, "具体场景")


def test_search_fails_on_unsafe_article_path(tmp_path: Path) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    output = tmp_path / "corpus"
    convert_epub(epub, output)
    manifest = output / "manifest.jsonl"
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    rows[0]["article_path"] = "../outside.md"
    manifest.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(CorpusError, match="article_path escapes batch or is missing"):
        search_corpus(output, "具体场景")


def test_build_writer_context_projects_corpus_windows(tmp_path: Path, monkeypatch) -> None:
    epub = tmp_path / "WhereMyLife__2026_08_20.epub"
    _make_epub(epub)
    corpus = tmp_path / "corpus"
    convert_epub(epub, corpus)
    monkeypatch.setattr(writing_toolset, "list_materials_impl", lambda *args, **kwargs: "")

    context = writing_toolset.build_writer_context(
        "article",
        "具体场景",
        ace_root=tmp_path / "ace",
        corpus_root=corpus,
        include_technique_guidance=False,
    )

    assert "Writing Corpus" in context
    assert "文章甲" in context
    assert "source_entry: one.html" in context
    assert "第一段：保留顺序。" in context
