"""Deterministic retrieval over the file-native writing corpus.

``manifest.jsonl`` is the corpus index.  Retrieval uses only lexical overlap
to locate candidate paragraphs and returns contiguous windows from the source
article.  It never summarizes, labels, or decides whether a window belongs in
the article.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS_ROOT = Path(
    os.environ.get(
        "WRITING_CORPUS_ROOT",
        _REPO_ROOT / "data" / "writing-corpus" / "wheremylife",
    )
)
MAX_CORPUS_WINDOWS = 6
MAX_CORPUS_WINDOW_CHARS = 1_800
MAX_CORPUS_CONTEXT_CHARS = 6_000


class CorpusError(RuntimeError):
    """Raised when a configured corpus is malformed or loses provenance."""


@dataclass(frozen=True)
class CorpusWindow:
    batch: str
    article_id: str
    title: str
    source: str
    url: str | None
    source_entry: str
    article_path: str
    start_paragraph: int
    end_paragraph: int
    text: str


@dataclass(frozen=True)
class _CorpusArticle:
    manifest_path: Path
    batch: str
    article_id: str
    title: str
    source: str
    url: str | None
    source_entry: str
    article_path: str
    paragraphs: tuple[str, ...]


def _lexical_units(value: str) -> set[str]:
    units = set(re.findall(r"[a-zA-Z0-9_-]+", value.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]+", value):
        units.update(run[i : i + 2] for i in range(max(0, len(run) - 1)))
    return units


def _safe_article_path(batch_root: Path, relative: object, *, manifest: Path) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise CorpusError(f"{manifest}: manifest row has no article_path")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise CorpusError(f"{manifest}: article_path must be relative")
    resolved = (batch_root / candidate).resolve()
    if not resolved.is_relative_to(batch_root.resolve()) or not resolved.is_file():
        raise CorpusError(f"{manifest}: article_path escapes batch or is missing: {relative}")
    return resolved


def _article_body(path: Path, *, manifest: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise CorpusError(f"{manifest}: article has no frontmatter: {path}")
    marker = raw.find("\n---\n", 4)
    if marker < 0:
        raise CorpusError(f"{manifest}: article frontmatter is unterminated: {path}")
    return raw[marker + len("\n---\n") :].strip()


def _load_manifest(manifest: Path, corpus_root: Path) -> list[_CorpusArticle]:
    batch_root = manifest.parent.resolve()
    try:
        batch = manifest.parent.relative_to(corpus_root.resolve()).as_posix()
    except ValueError as exc:
        raise CorpusError(f"manifest is outside corpus root: {manifest}") from exc
    if batch == ".":
        batch = ""

    articles: list[_CorpusArticle] = []
    for line_number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"{manifest}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise CorpusError(f"{manifest}:{line_number}: manifest row is not an object")
        required = ("article_id", "title", "source", "source_entry", "article_path")
        missing = [key for key in required if not row.get(key)]
        if missing:
            raise CorpusError(
                f"{manifest}:{line_number}: missing required field(s): {', '.join(missing)}"
            )
        article_path = _safe_article_path(
            batch_root, row["article_path"], manifest=manifest
        )
        body = _article_body(article_path, manifest=manifest)
        paragraphs = tuple(
            part.strip()
            for part in re.split(r"\n\s*\n", body)
            if part.strip()
        )
        articles.append(
            _CorpusArticle(
                manifest_path=manifest,
                batch=batch,
                article_id=str(row["article_id"]),
                title=str(row["title"]),
                source=str(row["source"]),
                url=row.get("url") if isinstance(row.get("url"), str) else None,
                source_entry=str(row["source_entry"]),
                article_path=str(row["article_path"]),
                paragraphs=paragraphs,
            )
        )
    return articles


def load_corpus_index(corpus_root: str | Path | None) -> list[_CorpusArticle]:
    """Load and validate all manifest rows in deterministic path order."""
    if corpus_root is None:
        return []
    root = Path(corpus_root).expanduser().resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise CorpusError(f"corpus root is not a directory: {root}")
    manifests = sorted(
        (path for path in root.rglob("manifest.jsonl") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    articles: list[_CorpusArticle] = []
    for manifest in manifests:
        articles.extend(_load_manifest(manifest, root))
    return articles


def _unique_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep each fixed-size local window; never bridge distant source hits."""
    return sorted(set(spans))


def _bounded_window(paragraphs: tuple[str, ...], start: int, end: int, limit: int) -> str:
    selected: list[str] = []
    used = 0
    for paragraph in paragraphs[start:end]:
        separator = 2 if selected else 0
        if used + separator + len(paragraph) <= limit:
            selected.append(paragraph)
            used += separator + len(paragraph)
            continue
        room = limit - used - separator
        if room > 0:
            selected.append(paragraph[:room].rstrip())
        break
    text = "\n\n".join(selected).strip()
    if end - start > len(selected) or (selected and len(selected[-1]) < len(paragraphs[start + len(selected) - 1])):
        text += "\n[连续原文窗口按字符预算截断]"
    return text


def search_corpus(
    corpus_root: str | Path | None,
    query: str,
    *,
    max_windows: int = MAX_CORPUS_WINDOWS,
    window_chars: int = MAX_CORPUS_WINDOW_CHARS,
) -> list[CorpusWindow]:
    """Return deterministic lexical hits as contiguous source windows."""
    terms = _lexical_units(query)
    if not terms:
        return []
    candidates: list[tuple[int, str, str, int, CorpusWindow]] = []
    for article in load_corpus_index(corpus_root):
        hits = [
            index
            for index, paragraph in enumerate(article.paragraphs)
            if terms & _lexical_units(paragraph)
        ]
        spans = _unique_spans(
            [(max(0, index - 1), min(len(article.paragraphs), index + 2)) for index in hits]
        )
        for start, end in spans:
            window_terms = set().union(
                *(_lexical_units(paragraph) for paragraph in article.paragraphs[start:end])
            )
            score = len(terms & window_terms)
            window = CorpusWindow(
                batch=article.batch,
                article_id=article.article_id,
                title=article.title,
                source=article.source,
                url=article.url,
                source_entry=article.source_entry,
                article_path=article.article_path,
                start_paragraph=start,
                end_paragraph=end,
                text=_bounded_window(article.paragraphs, start, end, window_chars),
            )
            candidates.append(
                (
                    -score,
                    article.batch,
                    article.article_path,
                    start,
                    window,
                )
            )
    candidates.sort(key=lambda item: item[:4])
    selected: list[CorpusWindow] = []
    occupied: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for _, batch, article_path, _, window in candidates:
        key = (batch, article_path)
        spans = occupied.setdefault(key, [])
        if any(
            window.start_paragraph < end and start < window.end_paragraph
            for start, end in spans
        ):
            continue
        spans.append((window.start_paragraph, window.end_paragraph))
        selected.append(window)
        if len(selected) >= max_windows:
            break
    return selected


def render_corpus_search(
    windows: list[CorpusWindow],
    *,
    max_chars: int = MAX_CORPUS_CONTEXT_CHARS,
) -> str:
    """Render raw search windows with only mechanical provenance."""
    if not windows:
        return ""
    sections = [
        "## Writing Corpus：搜索到的连续原文窗口",
        "",
        "以下内容是按词法检索定位的原文窗口。是否有用、如何理解和是否采用由 Writer 判断。",
    ]
    for window in windows:
        batch_ref = f"{window.batch}/{window.article_path}" if window.batch else window.article_path
        sections.extend(
            [
                "",
                f"### [{window.article_id}] {window.title}",
                f"- source: {window.source}",
                f"- url: {window.url if window.url is not None else 'null'}",
                f"- source_entry: {window.source_entry}",
                f"- article_path: {batch_ref}",
                f"- contiguous_paragraphs: {window.start_paragraph + 1}-{window.end_paragraph}",
                "",
                window.text,
            ]
        )
    rendered = "\n".join(sections).strip()
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 80].rstrip() + "\n\n[Writing Corpus 窗口按上下文预算截断]"
    return rendered
