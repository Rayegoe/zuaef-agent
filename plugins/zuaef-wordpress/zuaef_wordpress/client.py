"""WordPress REST client — SPEC v0.3 §48, §54, §55.

Thin, bounded, fail-loud. Every response is reduced to the v0.3 field set
before a tool returns it; HTTP errors, timeouts and network failures raise
``WordPressError`` — a write is never reported as success unless the real
response supports it.
"""

from __future__ import annotations

from typing import Any

import httpx

WRITE_FIELDS = ("id", "status", "link", "modified")
READ_FIELDS = ("id", "status", "slug", "link", "title", "modified")


class WordPressError(RuntimeError):
    """A loud WordPress failure: never rendered as a successful tool result."""


def _bound(data: dict[str, Any], *, fields: tuple[str, ...]) -> dict[str, Any]:
    bounded = {key: data.get(key) for key in fields}
    if "title" in bounded and isinstance(bounded["title"], dict):
        bounded["title"] = bounded["title"].get("rendered")
    if bounded.get("link") is None and isinstance(data.get("guid"), dict):
        bounded["link"] = data["guid"].get("rendered")
    return bounded


class WordPressClient:
    """BasicAuth application-password client for /wp-json/wp/v2."""

    def __init__(
        self,
        *,
        site_url: str,
        username: str,
        app_password: str,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ):
        base = site_url.rstrip("/") + "/wp-json/wp/v2"
        self._client = httpx.Client(
            base_url=base,
            auth=httpx.BasicAuth(username, app_password),
            timeout=timeout,
            transport=transport,
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method, path, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise WordPressError("wordpress request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise WordPressError(
                f"wordpress {method} {path} failed: HTTP "
                f"{exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise WordPressError(f"wordpress request failed: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise WordPressError("wordpress returned non-JSON response") from exc

    def get_post(self, post_id: int) -> dict[str, Any]:
        """Observe one post: identity/summary fields only, never full HTML."""
        data = self._request("GET", f"/posts/{post_id}")
        return _bound(data, fields=READ_FIELDS)

    def create_draft(
        self,
        *,
        title: str,
        content: str,
        excerpt: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "content": content, "status": "draft"}
        if excerpt:
            payload["excerpt"] = excerpt
        data = self._request("POST", "/posts", payload)
        return _bound(data, fields=WRITE_FIELDS)

    def update_post(
        self,
        post_id: int,
        *,
        title: str | None = None,
        content: str | None = None,
        excerpt: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            key: value
            for key, value in (
                ("title", title),
                ("content", content),
                ("excerpt", excerpt),
            )
            if value is not None
        }
        if not payload:
            raise WordPressError("wordpress_update_post requires at least one field")
        data = self._request("POST", f"/posts/{post_id}", payload)
        return _bound(data, fields=WRITE_FIELDS)

    def publish_post(self, post_id: int) -> dict[str, Any]:
        data = self._request("POST", f"/posts/{post_id}", {"status": "publish"})
        return _bound(data, fields=WRITE_FIELDS)
