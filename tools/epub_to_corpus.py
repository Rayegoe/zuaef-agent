"""Convert a WhereMyLife EPUB into a deterministic writing corpus.

The converter is deliberately mechanical.  The NCX supplies the source and
article boundaries, the XHTML supplies the paragraph order, and the manifest
keeps the provenance needed by the writer.  No summaries, labels, embeddings,
or model calls happen here.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

SKIP_TOP_LEVEL = frozenset({"总目录", "如果喜欢，欢迎捐赠"})
BLOCK_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "pre", "li", "td", "th", "blockquote"}
)
SKIP_TAGS = frozenset({"head", "script", "style", "noscript", "template", "svg"})


class CorpusConversionError(RuntimeError):
    """Raised when an EPUB cannot be converted without losing provenance."""


@dataclass(frozen=True)
class TocEntry:
    depth: int
    label: str
    href: str


@dataclass(frozen=True)
class Article:
    article_id: str
    source_order: int
    article_order: int
    source: str
    title: str
    source_entry: str
    body: str
    url: str | None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _normalise_text(value: str) -> str:
    # NFC keeps source punctuation and compatibility characters intact.  The
    # converter may collapse whitespace, but it must not silently rewrite the
    # author's glyphs as a side effect of slugging or indexing.
    value = unicodedata.normalize("NFC", value)
    return re.sub(r"\s+", " ", value).strip()


def _first_text(element: ElementTree.Element | None, name: str) -> str:
    if element is None:
        return ""
    for child in element.iter():
        if _local_name(child.tag) == name:
            return _normalise_text("".join(child.itertext()))
    return ""


def parse_toc_ncx(ncx_bytes: bytes) -> list[TocEntry]:
    """Flatten NCX navPoints in document order while preserving depth."""
    try:
        root = ElementTree.fromstring(ncx_bytes)
    except ElementTree.ParseError as exc:
        raise CorpusConversionError(f"invalid NCX XML: {exc}") from exc

    nav_map = next(
        (element for element in root.iter() if _local_name(element.tag) == "navmap"),
        None,
    )
    if nav_map is None:
        raise CorpusConversionError("EPUB NCX has no navMap")

    entries: list[TocEntry] = []

    def visit(parent: ElementTree.Element, depth: int) -> None:
        for child in list(parent):
            if _local_name(child.tag) != "navpoint":
                continue
            label = _first_text(child, "text")
            content = next(
                (
                    element
                    for element in child.iter()
                    if _local_name(element.tag) == "content"
                ),
                None,
            )
            href = _normalise_text(content.attrib.get("src", "") if content is not None else "")
            if not label or not href:
                raise CorpusConversionError(
                    f"NCX navPoint missing label or href at depth {depth}"
                )
            entries.append(TocEntry(depth=depth, label=label, href=href))
            visit(child, depth + 1)

    visit(nav_map, 0)
    if not entries:
        raise CorpusConversionError("EPUB NCX has no navPoint entries")
    return entries


class _XhtmlParser(HTMLParser):
    """Extract leaf-like blocks without selecting nested containers twice."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.external_url: str | None = None
        self._active_tag: str | None = None
        self._active_text: list[str] = []
        self._skip_depth = 0
        self._fallback_text: list[str] = []

    def _finish_block(self) -> None:
        if self._active_tag is None:
            return
        text = _normalise_text("".join(self._active_text))
        if text and (not self.blocks or self.blocks[-1] != text):
            self.blocks.append(text)
        self._active_tag = None
        self._active_text = []

    def _record_url(self, attrs: list[tuple[str, str | None]]) -> None:
        if self.external_url is not None:
            return
        href = next((value for key, value in attrs if key.lower() == "href"), None)
        if not href:
            return
        parsed = urlsplit(href.strip())
        if parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
            self.external_url = href.strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._record_url(attrs)
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in BLOCK_TAGS:
            self._finish_block()
            self._active_tag = tag
            self._active_text = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if self._active_tag == tag:
            self._finish_block()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._active_tag is None:
            self._fallback_text.append(data)
        else:
            self._active_text.append(data)

    def finish(self) -> tuple[list[str], str | None]:
        self._finish_block()
        blocks = list(self.blocks)
        if not blocks:
            fallback = _normalise_text("".join(self._fallback_text))
            if fallback:
                blocks = [fallback]
        return blocks, self.external_url


def extract_xhtml(html_bytes: bytes, title: str) -> tuple[str, str | None]:
    parser = _XhtmlParser()
    try:
        parser.feed(html_bytes.decode("utf-8"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as exc:
        raise CorpusConversionError(f"XHTML cannot be decoded: {exc}") from exc
    blocks, url = parser.finish()
    if blocks and _normalise_text(blocks[0]) == _normalise_text(title):
        blocks = blocks[1:]
    body = "\n\n".join(blocks).strip()
    return body, url


def _safe_zip_entry(href: str, *, base_dir: str, names: set[str]) -> str:
    raw = unquote(href.split("#", 1)[0]).replace("\\", "/")
    candidate = posixpath.normpath(posixpath.join(base_dir, raw))
    if candidate.startswith("../") or candidate == ".." or candidate not in names:
        raise CorpusConversionError(f"NCX href does not resolve inside EPUB: {href}")
    return candidate


def _find_ncx(names: Iterable[str]) -> str:
    candidates = sorted(name for name in names if name.lower().endswith(".ncx"))
    if not candidates:
        raise CorpusConversionError("EPUB has no NCX navigation document")
    return candidates[0]


def _infer_date(epub_name: str) -> str:
    match = re.search(r"(20\d{2})[_-](\d{2})[_-](\d{2})", epub_name)
    return "".join(match.groups()) if match else "00000000"


def _json_scalar(value: str | None) -> str:
    return "null" if value is None else json.dumps(value, ensure_ascii=False)


def _render_article(article: Article, *, epub_filename: str) -> str:
    frontmatter = [
        "---",
        f"article_id: {_json_scalar(article.article_id)}",
        f"title: {_json_scalar(article.title)}",
        f"source: {_json_scalar(article.source)}",
        f"url: {_json_scalar(article.url)}",
        f"source_entry: {_json_scalar(article.source_entry)}",
        f"epub_filename: {_json_scalar(epub_filename)}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + article.body + "\n"


def _manifest_row(article: Article, *, article_path: str, epub_filename: str) -> dict:
    return {
        "article_id": article.article_id,
        "article_order": article.article_order,
        "article_path": article_path,
        "epub_filename": epub_filename,
        "source": article.source,
        "source_entry": article.source_entry,
        "source_order": article.source_order,
        "title": article.title,
        "url": article.url,
    }


def _write_jsonl(rows: Iterable[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def convert_epub(epub: str | Path, output_dir: str | Path) -> dict:
    """Convert one EPUB and return the deterministic receipt."""
    epub_path = Path(epub).expanduser().resolve()
    if not epub_path.is_file():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")
    output_path = Path(output_dir).expanduser().resolve()
    if output_path.exists() and not output_path.is_dir():
        raise FileExistsError(f"output path is not a directory: {output_path}")
    if output_path.is_dir() and any(output_path.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    epub_filename = epub_path.name
    day = _infer_date(epub_filename)
    articles: list[Article] = []
    toc_count = 0
    source_count = 0

    try:
        with zipfile.ZipFile(epub_path) as archive:
            names = set(archive.namelist())
            ncx_name = _find_ncx(names)
            toc = parse_toc_ncx(archive.read(ncx_name))
            toc_count = len(toc)
            base_dir = posixpath.dirname(ncx_name)
            current_source: tuple[int, str] | None = None
            article_order = 0
            seen_entries: set[str] = set()
            for entry in toc:
                if entry.depth == 0:
                    if entry.label in SKIP_TOP_LEVEL:
                        current_source = None
                        continue
                    source_count += 1
                    current_source = (source_count, entry.label)
                    article_order = 0
                    continue
                if entry.depth != 1 or current_source is None:
                    continue
                article_order += 1
                source_order, source_name = current_source
                source_entry = entry.href.split("#", 1)[0]
                resolved = _safe_zip_entry(source_entry, base_dir=base_dir, names=names)
                if resolved in seen_entries:
                    raise CorpusConversionError(
                        f"duplicate XHTML source entry for article {entry.label}: {source_entry}"
                    )
                seen_entries.add(resolved)
                body, url = extract_xhtml(archive.read(resolved), entry.label)
                article_id = f"WML-{day}-{source_order:02d}-{article_order:03d}"
                articles.append(
                    Article(
                        article_id=article_id,
                        source_order=source_order,
                        article_order=article_order,
                        source=source_name,
                        title=entry.label,
                        source_entry=source_entry,
                        body=body,
                        url=url,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise CorpusConversionError(f"invalid EPUB zip: {epub_path}") from exc
    except KeyError as exc:
        raise CorpusConversionError(f"EPUB entry is missing: {exc}") from exc

    manifest_rows = [
        _manifest_row(
            article,
            article_path=f"articles/{article.article_id}.md",
            epub_filename=epub_filename,
        )
        for article in articles
    ]
    manifest_text = _write_jsonl(manifest_rows)
    receipt = {
        "article_count": len(articles),
        "epub_filename": epub_filename,
        "format": "zuaef-writing-corpus/v1",
        "manifest": "manifest.jsonl",
        "source_count": source_count,
        "toc_entries": toc_count,
    }

    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_path.name}.", dir=str(output_path.parent))
    )
    try:
        article_dir = staging / "articles"
        article_dir.mkdir()
        for article in articles:
            article_path = article_dir / f"{article.article_id}.md"
            article_path.write_text(
                _render_article(
                    article,
                    epub_filename=epub_filename,
                ),
                encoding="utf-8",
            )
        (staging / "manifest.jsonl").write_text(manifest_text, encoding="utf-8")
        (staging / "receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if output_path.exists():
            output_path.rmdir()
        os.replace(staging, output_path)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt | {"output_dir": str(output_path)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epub", required=True, help="WhereMyLife EPUB path")
    parser.add_argument("--output-dir", required=True, help="fresh corpus batch directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = convert_epub(args.epub, args.output_dir)
    except (CorpusConversionError, FileExistsError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
