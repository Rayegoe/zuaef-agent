"""Source acquisition tools: ``search_sources`` and ``read_source``.

External read operations only (ARCHITECTURE §5.3) — no approval. Results
preserve provider-supplied metadata, never synthesize it, and failures are
specific so the model can choose another source or preserve an unknown
(CI_PLUGIN_SPEC §10, §11).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic_ai import FunctionToolset
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.models import CoreDeps

from .network import (
    NetworkError,
    extract_document,
    fetch_document,
    make_client,
)
from .search_backend import (
    SearchBackend,
    SearchBackendError,
    _search_result_document,
)

TOOLSET_INSTRUCTIONS = """\
Source acquisition for competitive intelligence:

- search_sources discovers public sources. Prefer official product /
  configurator / model-year press / help surfaces for decision-critical
  facts; treat secondary summaries as discovery hints, not replacements.
- read_source fetches one public HTML page or PDF and returns bounded
  extractable text. A failed read is reported specifically; choose another
  source or preserve the unknown — never claim a fact was read from a page
  you did not open.

Failures carry a machine code (URL_UNSAFE, FETCH_BLOCKED, FETCH_TIMEOUT,
UNSUPPORTED_CONTENT, DOWNLOAD_TOO_LARGE, PARSE_EMPTY, SEARCH_BACKEND_*).
A PARSE_EMPTY result means the page contained no extractable text — that
is not evidence. Absence of a result in search output is not proof that a
product/price/config does not exist; official checks decide that.
"""


class SourceToolError(RuntimeError):
    """Model-visible tool failure with a stable machine code prefix."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def make_source_toolset(
    backend: SearchBackend,
    *,
    max_search_results: int,
    max_fetch_bytes: int,
    max_preview_chars: int,
    domain: str = "ebike",
    output_language: str = "zh-CN",
    timeout_seconds: float = 30.0,
    client_factory: Any = make_client,
) -> AbstractToolset[CoreDeps]:
    """Build the source toolset.

    ``client_factory`` returns an ``httpx.Client`` (tests inject one with a
    mock transport; production uses :func:`make_client`).
    """
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=(
            TOOLSET_INSTRUCTIONS
            + f"\nDeployment context: domain={domain}, report language preference="
            f"{output_language}."
        )
    )

    @toolset.tool_plain
    def search_sources(query: str, limit: int | None = None) -> str:
        """Discover public sources for a competitive-intelligence question.

        Returns the query and provider results with title/url and (when the
        provider supplied them) snippet and published/indexed date. Missing
        metadata is not synthesized. Raise the limit for broad discovery,
        keep it small for a targeted official-page check.

        中文关键词：搜索、检索来源、公开网页、产品研究、竞品调研、新闻网、官方页面。
        """
        capped = min(limit or max_search_results, max_search_results)
        if capped < 1:
            raise SourceToolError("INVALID_LIMIT", "limit must be >= 1")
        query = query.strip()
        if not query:
            raise SourceToolError("INVALID_QUERY", "query must not be empty")
        try:
            hits = backend.search(query, limit=capped)
        except SearchBackendError as exc:
            raise SourceToolError(exc.code, exc.message) from exc
        if not hits:
            raise SourceToolError(
                "SEARCH_EMPTY",
                f"search for {query!r} returned no results — revise the "
                "query or preserve the unknown instead of assuming absence",
            )
        return _search_result_document(query, hits)

    @toolset.tool_plain
    def read_source(url: str, focus: str | None = None) -> str:
        """Fetch one public HTML page or PDF and extract bounded useful text.

        ``focus`` describes the decision fact you are hunting; the same
        bounded text is returned either way (extraction never fabricates or
        reorders content). Use it when you want to record intent, not to
        skip verifying what is actually on the page.

        中文关键词：读取网页、打开链接、获取内容、阅读PDF、提取正文。
        """
        url = url.strip()
        if not url:
            raise SourceToolError("INVALID_URL", "url must not be empty")
        client = client_factory(timeout_seconds=timeout_seconds)
        try:
            with client:
                document = fetch_document(
                    url,
                    client,
                    max_bytes=max_fetch_bytes,
                )
                title, text = extract_document(document)
        except NetworkError as exc:
            raise SourceToolError(exc.code, exc.message) from exc
        except httpx.HTTPError as exc:
            raise SourceToolError(
                "FETCH_BLOCKED",
                f"network error reading {url!r}: {type(exc).__name__}: {exc}",
            ) from exc
        truncated = len(text) > max_preview_chars
        body = text[:max_preview_chars]
        result: dict[str, Any] = {
            "url": document.final_url,
            "content_type": document.content_type,
            "text": body,
            "truncated": truncated,
        }
        if title:
            result["title"] = title
        if truncated:
            result["preview_chars"] = max_preview_chars
        if focus and focus.strip():
            result["focus"] = focus.strip()
        return json.dumps(result, ensure_ascii=False)

    return toolset
