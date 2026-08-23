"""Provider-independent public research toolset for competitive intelligence.

Deterministic host-owned transport/security/extraction/artifacts; the model
owns source selection, lifecycle/configuration/conflict interpretation and
report emphasis. No Riese & Müller (or any brand) conclusion is encoded
here.

Search backend protocol + Brave/fixture implementations (ADR-004).
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

# Production secret (spec: zuaef-ci-console-analysis v0.2 CI_PLUGIN_SPEC §4).
# ``BRAVE_API_KEY`` is accepted as a deployment fallback only; the spec name
# always wins when both are set.
BRAVE_SECRET_ENV = "ZUAEF_BRAVE_SEARCH_API_KEY"
BRAVE_SECRET_ENV_FALLBACK = "BRAVE_API_KEY"

_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

# Provider contract: 1 query/second (x-ratelimit-policy 1;w=1, 2000;w=2678400).
# This is deterministic transport pacing shared by every backend instance —
# reproduced failure: a burst of searches drew HTTP 429 and killed a run.
_BRAVE_MIN_QUERY_INTERVAL = 1.1
_TRANSIENT_STATUSES = (429, 500, 502, 503, 504)
_pace_lock = threading.Lock()
_last_query_at = 0.0


def _retryable(exc: httpx.HTTPStatusError, *, attempt: int, max_retries: int) -> bool:
    """Bounded backoff decision: transient status + retry budget left."""
    if not BraveSearchBackend._should_backoff(
        exc.response.status_code, attempt, max_retries
    ):
        return False
    time.sleep(1.5 * (attempt + 1))
    return True


class SearchBackendError(RuntimeError):
    """A search backend failure with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


from .network import make_client


@dataclass(frozen=True)
class SearchHit:
    """One provider result with exactly the metadata the provider supplied.

    ``snippet`` / ``published_or_indexed_date`` are preserved when the
    backend returns them; missing metadata stays missing (never synthesized).
    """

    title: str
    url: str
    snippet: str | None = None
    published_or_indexed_date: str | None = None

    def as_dict(self) -> dict[str, str]:
        data: dict[str, str] = {"title": self.title, "url": self.url}
        if self.snippet is not None:
            data["snippet"] = self.snippet
        if self.published_or_indexed_date is not None:
            data["published_or_indexed_date"] = self.published_or_indexed_date
        return data


class SearchBackend(Protocol):
    """Internal plugin interface — implementation detail, not a composition ABI."""

    def search(self, query: str, *, limit: int) -> list[SearchHit]: ...


class BraveSearchBackend:
    """Brave Search API backend (ADR-004 — first production backend).

    Preserves provider title/url/description and the provider's published/
    indexed date (``page_age``) when supplied; no metadata is invented and
    provider result order is preserved.
    """

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = _BRAVE_ENDPOINT,
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
        client_factory: Any = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client_factory = client_factory

    @classmethod
    def secret_from_env(cls) -> str | None:
        return os.getenv(BRAVE_SECRET_ENV) or os.getenv(BRAVE_SECRET_ENV_FALLBACK)

    def search(self, query: str, *, limit: int) -> list[SearchHit]:
        """Run the query with bounded backoff retries on transient HTTP
        429/5xx responses (reproduced: a benchmark burst hit Brave's rate
        limit and killed an otherwise healthy run). Failures after the
        last retry stay specific — no provider fallback chain.
        """
        if limit < 1:
            raise SearchBackendError("INVALID_LIMIT", "limit must be >= 1")
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params = {"q": query, "count": limit}
        factory = self._client_factory or (
            lambda: make_client(self._timeout)
        )
        self._pace()
        last_error: SearchBackendError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with factory() as client:
                    response = client.get(
                        self._endpoint,
                        params=params,
                        headers=headers,
                        follow_redirects=True,
                    )
                    if BraveSearchBackend._should_backoff(
                        response.status_code, attempt, self._max_retries
                    ):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPStatusError as exc:
                last_error = SearchBackendError(
                    "SEARCH_BACKEND_HTTP",
                    f"Brave search returned HTTP {exc.response.status_code} "
                    f"for query {query!r}",
                )
                if _retryable(exc, attempt=attempt, max_retries=self._max_retries):
                    continue
                raise last_error from exc
            except (httpx.HTTPError, ValueError) as exc:
                raise SearchBackendError(
                    "SEARCH_BACKEND_UNAVAILABLE",
                    f"Brave search failed for query {query!r}: "
                    f"{type(exc).__name__}: {exc}",
                ) from exc
            return self._hits(payload, limit)
        if last_error is not None:
            raise last_error
        raise SearchBackendError(
            "SEARCH_BACKEND_UNAVAILABLE",
            f"Brave search failed for query {query!r}",
        )

    @staticmethod
    def _should_backoff(status: int, attempt: int, max_retries: int) -> bool:
        return status in _TRANSIENT_STATUSES and attempt < max_retries

    @staticmethod
    def _pace() -> None:
        """Respect the provider's 1-query-per-second contract across all
        backend instances (reproduced: a burst of benchmark queries drew
        HTTP 429 and killed a healthy run). Deterministic transport pacing
        — never a model decision."""
        global _last_query_at
        with _pace_lock:
            now = time.monotonic()
            wait = _BRAVE_MIN_QUERY_INTERVAL - (now - _last_query_at)
            if wait > 0:
                time.sleep(wait)
            _last_query_at = time.monotonic()

    @staticmethod
    def _hits(payload: dict, limit: int) -> list[SearchHit]:
        results = payload.get("web", {}).get("results") or []
        hits: list[SearchHit] = []
        for result in results[:limit]:
            title = str(result.get("title") or "").strip()
            url = str(result.get("url") or "").strip()
            if not title or not url:
                continue
            snippet = result.get("description")
            if snippet is not None:
                snippet = str(snippet).strip() or None
            # Provider-supplied indexed/created date: Brave returns an ISO
            # ``page_age`` for many pages; ``age`` is a relative label kept
            # only when page_age is absent (both are provider-supplied).
            date = result.get("page_age") or result.get("published_date")
            if date is None:
                date = result.get("age")
            hits.append(
                SearchHit(
                    title=title,
                    url=url,
                    snippet=snippet,
                    published_or_indexed_date=str(date) if date else None,
                )
            )
        return hits


class FixtureSearchBackend:
    """Deterministic, offline backend for tests and CI runs.

    ``fixture`` maps a normalized query to a fixed ordered list of hits; any
    other query raises a specific ``FIXTURE_MISS`` failure so a test can
    never celebrate an unseeded search. Hit ordering is the fixture order
    (provider order is preserved by contract).
    """

    def __init__(self, fixture: Mapping[str, Sequence[Mapping[str, str]]]) -> None:
        self._fixture: dict[str, list[SearchHit]] = {}
        for query, hits in fixture.items():
            self._fixture[self._key(query)] = [
                SearchHit(
                    title=str(hit.get("title") or "").strip(),
                    url=str(hit.get("url") or "").strip(),
                    snippet=(
                        str(hit["snippet"]).strip()
                        if hit.get("snippet") is not None
                        else None
                    ),
                    published_or_indexed_date=(
                        str(hit["published_or_indexed_date"]).strip()
                        if hit.get("published_or_indexed_date") is not None
                        else None
                    ),
                )
                for hit in hits
                if hit.get("title") and hit.get("url")
            ]

    @staticmethod
    def _key(query: str) -> str:
        return " ".join(query.lower().split())

    def search(self, query: str, *, limit: int) -> list[SearchHit]:
        if limit < 1:
            raise SearchBackendError("INVALID_LIMIT", "limit must be >= 1")
        hits = self._fixture.get(self._key(query))
        if hits is None:
            raise SearchBackendError(
                "FIXTURE_MISS",
                f"fixture backend has no seeded results for query {query!r}",
            )
        return hits[:limit]


def _search_result_document(query: str, hits: Sequence[SearchHit]) -> str:
    return json.dumps(
        {"query": query, "results": [hit.as_dict() for hit in hits]},
        ensure_ascii=False,
    )
