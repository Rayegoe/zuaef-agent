"""Competitive-intelligence plugin tests — no-network contract.

Search uses the fixture backend or a mocked Brave transport; fetch uses
httpx MockTransport; renderer runs on locally generated fixture content.
No test requires Brave credentials or the public internet.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic_ai import RunContext, RunUsage, models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_competitive_intelligence import build_plugin
from zuaef_competitive_intelligence import network as ci_network
from zuaef_competitive_intelligence.plugin import DEFAULT_MAX_PREVIEW_CHARS
from zuaef_competitive_intelligence.report_renderer import pdf_page_count
from zuaef_competitive_intelligence.search_backend import (
    BraveSearchBackend,
    FixtureSearchBackend,
    SearchBackendError,
)
from zuaef_competitive_intelligence.source_tools import (
    SourceToolError,
    make_source_toolset,
)
from zuaef_competitive_intelligence.work_product_tools import (
    WorkProductError,
    make_work_product_toolset,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv
from zuaef_agent.runtime import execute_run

models.ALLOW_MODEL_REQUESTS = False

FIXTURE_HITS = {
    "charger5 riese müller": [
        {
            "title": "Charger5 — Riese & Müller",
            "url": "https://www.r-m.de/de/bikes/charger5/",
            "snippet": "Passenger e-bike family page.",
            "published_or_indexed_date": "2026-08-01",
        },
        {
            "title": "Charger5 test report",
            "url": "https://media.example.com/charger5-review",
            "snippet": "Review of the Charger5.",
        },
    ],
    "es gibt hier nichts": [],
}


def _mock_client(handler):
    def factory(timeout_seconds: float = 30.0) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(handler),
            timeout=timeout_seconds,
            follow_redirects=False,
        )

    return factory


def _html_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        content=(
            b"<html><head><title>Charger5 &mdash; Riese &amp; M&uuml;ller</title>"
            b"<script>var x=1;</script></head><body>"
            b"<h1>Charger5</h1><p>Das neue Charger5 mit 800Wh Akku.</p>"
            b"<style>p{color:red}</style></body></html>"
        ),
    )


# ── fixture backend ─────────────────────────────────────────────────────────


def test_fixture_backend_preserves_provider_metadata() -> None:
    backend = FixtureSearchBackend(FIXTURE_HITS)
    hits = backend.search("Charger5 Riese Müller", limit=5)
    assert len(hits) == 2
    first = hits[0]
    assert first.url == "https://www.r-m.de/de/bikes/charger5/"
    assert first.published_or_indexed_date == "2026-08-01"
    # provider order preserved
    assert hits[0].title.startswith("Charger5")
    # missing metadata not synthesized
    assert hits[1].published_or_indexed_date is None


def test_fixture_backend_miss_is_specific() -> None:
    backend = FixtureSearchBackend(FIXTURE_HITS)
    with pytest.raises(SearchBackendError) as exc_info:
        backend.search("unseeded query", limit=5)
    assert exc_info.value.code == "FIXTURE_MISS"


def test_fixture_backend_empty_seed_returns_empty_list() -> None:
    backend = FixtureSearchBackend(FIXTURE_HITS)
    assert backend.search("es gibt hier nichts", limit=5) == []


# ── Brave backend normalization (mocked transport) ──────────────────────────


def test_brave_backend_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "X-Subscription-Token" in request.headers
        assert request.url.params["count"] == "3"
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Nevo5",
                            "url": "https://www.r-m.de/de/bikes/nevo5/",
                            "description": "Nevo5 family",
                            "page_age": "2026-07-15",
                        },
                        {
                            "title": "Nevo5 (old)",
                            "url": "https://old.example.com/nevo5",
                            # no snippet / no date supplied
                        },
                        {"title": "", "url": "https://empty.example.com/"},
                    ]
                }
            },
        )

    backend = BraveSearchBackend(
        api_key="test-key",
        endpoint="https://api.search.brave.com/res/v1/web/search",
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ),
    )
    hits = backend.search("Nevo5", limit=3)
    assert len(hits) == 2
    assert hits[0].published_or_indexed_date == "2026-07-15"
    assert hits[1].snippet is None and hits[1].published_or_indexed_date is None


def test_brave_backend_http_error_is_specific() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    backend = BraveSearchBackend(
        api_key="k",
        endpoint="https://brave.test/search",
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ),
    )
    with pytest.raises(SearchBackendError) as exc_info:
        backend.search("q", limit=3)
    assert exc_info.value.code == "SEARCH_BACKEND_HTTP"


# ── URL safety ──────────────────────────────────────────────────────────────


def test_url_guard_rejects_non_public_destinations() -> None:
    from zuaef_competitive_intelligence.network import (
        NetworkError,
        validate_public_url,
    )

    for url in (
        "ftp://example.com/file",
        "file:///etc/passwd",
        "https://user:pass@example.com/",
        "https://user@example.com/",
        "http://localhost/x",
        "https://localhost.localdomain/x",
        "http://127.0.0.1/x",
        "http://127.0.0.2/x",
        "http://10.0.0.1/x",
        "http://172.16.0.1/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/x",
        "http://[fe80::1]/x",
        "http://0.0.0.0/x",
        "http://224.0.0.1/x",
        "not a url",
    ):
        with pytest.raises(NetworkError) as exc_info:
            validate_public_url(url)
        assert exc_info.value.code == "URL_UNSAFE", url


def test_url_guard_accepts_public_url() -> None:
    from zuaef_competitive_intelligence.network import validate_public_url

    parsed = validate_public_url("https://www.r-m.de/de/bikes/charger5/")
    assert parsed.host == "www.r-m.de"


def test_public_destination_dns_boundary() -> None:
    from zuaef_competitive_intelligence.network import (
        NetworkError,
        assert_public_destination,
        validate_public_url,
    )

    with pytest.raises(NetworkError) as exc_info:
        assert_public_destination(validate_public_url("http://127.0.0.1/x"))
    assert exc_info.value.code == "URL_UNSAFE"


# ── fetch + extraction ──────────────────────────────────────────────────────


@pytest.mark.skipif(
    not httpx._transports  # type: ignore[attr-defined]
    ,
    reason="httpx mock transports unavailable",
)
def test_read_source_html_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)
    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=DEFAULT_MAX_PREVIEW_CHARS,
        client_factory=_mock_client(_html_handler),
    )
    result = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://www.r-m.de/de/bikes/charger5/"}, _tool_ctx()
            )
        )
    )
    assert result["content_type"] == "text/html"
    assert "Charger5" in result["text"]
    assert "800Wh" in result["text"]
    assert "var x=1" not in result["text"]  # script removed
    assert result["truncated"] is False


def _tool_ctx() -> RunContext[CoreDeps]:
    return RunContext(
        deps=_deps(Path(".")), usage=RunUsage(), prompt="", model=None
    )


def _tool_map(toolset):
    """Sync-context tool map (plain test functions only)."""
    import asyncio

    return asyncio.run(toolset.get_tools(_tool_ctx()))


async def _tool_map_async(toolset):
    """Async-context tool map (inside _scenario bodies)."""
    deps = _deps(Path("."))
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    return await toolset.get_tools(ctx)


def test_read_source_html_title_and_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        body = "<html><head><title>T</title></head><body>" + ("x" * 1000) + "</body></html>"
        return httpx.Response(200, headers={"Content-Type": "text/html"}, content=body)

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(handler),
    )
    result = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/page"}, _tool_ctx()
            )
        )
    )
    assert result["title"] == "T"
    assert result["truncated"] is True
    assert len(result["text"]) == 100


def test_read_source_pdf_extraction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pymupdf

    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)
    pdf_path = tmp_path / "fixture.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Riese & Mueller 2026 market data")
    doc.save(str(pdf_path))
    doc.close()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=pdf_path.read_bytes(),
        )

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=DEFAULT_MAX_PREVIEW_CHARS,
        client_factory=_mock_client(handler),
    )
    result = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/market.pdf"}, _tool_ctx()
            )
        )
    )
    assert result["content_type"] == "application/pdf"
    assert "2026 market data" in result["text"]


def test_fetch_rejects_private_redirect_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/internal"})

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(handler),
    )
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/redirect"}, _tool_ctx()
            )
        )
    )
    assert payload["error"]["code"] == "URL_UNSAFE"


def test_fetch_byte_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            content=b"y" * 1000,
        )

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=100,
        max_preview_chars=100,
        client_factory=_mock_client(handler),
    )
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/big"}, _tool_ctx()
            )
        )
    )
    assert payload["error"]["code"] == "DOWNLOAD_TOO_LARGE"


def test_fetch_unsupported_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Type": "application/octet-stream"}, content=b"zzz"
        )

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(handler),
    )
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/weird"}, _tool_ctx()
            )
        )
    )
    assert payload["error"]["code"] == "UNSUPPORTED_CONTENT"


def test_empty_parse_is_failure_not_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Type": "text/html"}, content=b"<html><body></body></html>"
        )

    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(handler),
    )
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["read_source"].call_func(
                {"url": "https://example.com/empty"}, _tool_ctx()
            )
        )
    )
    assert payload["error"]["code"] == "PARSE_EMPTY"


def test_search_empty_is_specific_failure() -> None:
    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(_html_handler),
    )
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["search_sources"].call_func(
                {"query": "es gibt hier nichts"}, _tool_ctx()
            )
        )
    )
    assert payload["error"]["code"] == "SEARCH_EMPTY"
    assert payload["results"] == []


def test_search_sources_bounded_limit() -> None:
    toolset = make_source_toolset(
        FixtureSearchBackend(FIXTURE_HITS),
        max_search_results=10,
        max_fetch_bytes=5_000_000,
        max_preview_chars=100,
        client_factory=_mock_client(_html_handler),
    )
    result = json.loads(
        asyncio.run(
            _tool_map(toolset)["search_sources"].call_func(
                {"query": "Charger5 Riese Müller", "limit": 1}, _tool_ctx()
            )
        )
    )
    assert len(result["results"]) == 1


# ── work products ───────────────────────────────────────────────────────────


def _deps(workspace: Path, run_id: str = "run-test-1") -> CoreDeps:
    return CoreDeps(workspace_root=workspace.resolve(), run_id=run_id)


def _ctx(workspace: Path) -> RunContext[CoreDeps]:
    return RunContext(
        deps=_deps(workspace),
        usage=RunUsage(),
        model="test",
        prompt="p",
    )


def test_save_work_product_kind_mapping(tmp_path: Path) -> None:
    import asyncio

    async def _scenario():
        toolset = make_work_product_toolset()
        tools = await _tool_map_async(toolset)
        ctx = _ctx(tmp_path)
        for kind, filename in (
            ("notes", "analyst-notes.md"),
            ("catalog", "catalog.csv"),
            ("evidence", "evidence.md"),
            ("conflicts", "conflicts.md"),
            ("report", "report.md"),
            ("qa", "qa.md"),
        ):
            result = json.loads(await tools["save_work_product"].call_func({"kind": kind, "content": "内容"}, ctx))
            target = tmp_path / "artifacts" / "competitive-intel" / "run-test-1" / filename
            assert target.is_file()
            assert result["path"] == target.relative_to(tmp_path).as_posix()


    asyncio.run(_scenario())

def test_save_work_product_invalid_kind(tmp_path: Path) -> None:
    import asyncio

    async def _scenario():
        toolset = make_work_product_toolset()
        ctx = _ctx(tmp_path)
        payload = json.loads(
            await (await _tool_map_async(toolset))["save_work_product"].call_func(
                {"kind": "manifest", "content": "x"}, ctx
            )
        )
        assert payload["error"]["code"] == "INVALID_KIND"


    asyncio.run(_scenario())

def test_save_work_product_run_isolation(tmp_path: Path) -> None:
    """The fixed kind->filename mapping can never escape the run root, and
    two runs never share a tree."""
    import asyncio

    async def _scenario():
        toolset = make_work_product_toolset()
        ctx_a = RunContext(
            deps=CoreDeps(workspace_root=tmp_path.resolve(), run_id="run-a"),
            usage=RunUsage(),
            model="test",
            prompt="p",
        )
        ctx_b = RunContext(
            deps=CoreDeps(workspace_root=tmp_path.resolve(), run_id="run-b"),
            usage=RunUsage(),
            model="test",
            prompt="p",
        )
        tools = await _tool_map_async(toolset)
        await tools["save_work_product"].call_func(
            {"kind": "report", "content": "AA"}, ctx_a
        )
        await tools["save_work_product"].call_func(
            {"kind": "report", "content": "BB"}, ctx_b
        )
        root_a = tmp_path / "artifacts" / "competitive-intel" / "run-a"
        root_b = tmp_path / "artifacts" / "competitive-intel" / "run-b"
        assert (root_a / "report.md").read_text(encoding="utf-8") == "AA"
        assert (root_b / "report.md").read_text(encoding="utf-8") == "BB"
        # Nothing was planted outside the two run roots.
        assert not (tmp_path / "report.md").exists()
        assert not (root_a / ".." / "report.md").resolve().exists()

    asyncio.run(_scenario())

def test_download_asset_image_mime_and_confinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from PIL import Image as PILImage

    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)
    buf = __import__("io").BytesIO()
    PILImage.new("RGB", (4, 4), "red").save(buf, format="PNG")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "image/png"},
            content=buf.getvalue(),
        )

    toolset = make_work_product_toolset(
        client_factory=_mock_client(handler),
    )
    ctx = _ctx(tmp_path)
    result = json.loads(
        asyncio.run(
            _tool_map(toolset)["download_asset"].call_func(
                {"url": "https://example.com/bike.png", "name": "charger5 ../x"}, ctx
            )
        )
    )
    target = tmp_path / "artifacts" / "competitive-intel" / "run-test-1" / "assets"
    files = list(target.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".png"
    assert ".." not in files[0].name
    assert result["source_url"] == "https://example.com/bike.png"


def test_download_asset_non_image_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    monkeypatch.setattr(ci_network, "assert_public_destination", lambda url: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Type": "text/html"}, content=b"<p>not an image</p>"
        )

    toolset = make_work_product_toolset(client_factory=_mock_client(handler))
    payload = json.loads(
        asyncio.run(
            _tool_map(toolset)["download_asset"].call_func(
                {"url": "https://example.com/x", "name": "img"}, _ctx(tmp_path)
            )
        )
    )
    assert payload["error"]["code"] == "UNSUPPORTED_CONTENT"


# ── renderer + preview ──────────────────────────────────────────────────────


FIXTURE_REPORT = """\
# 执行摘要

**Riese & Müller** 提供 *丰富的产品线*。

## 产品地图

| 系列 | 类型 | 状态 |
| ---- | ---- | ---- |
| Charger5 | 客运 | CURRENT |
| Load5 | Cargo | CURRENT |

## 关键发现

- 官方页面为决策事实提供来源。
- 冲突保持未解决状态。

> 引用块内容保持原样。

![alt](assets/photo.png)
"""


def _write_fixture_report(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "report.md").write_text(FIXTURE_REPORT, encoding="utf-8")
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    from PIL import Image as PILImage

    PILImage.new("RGB", (60, 30), "blue").save(assets / "photo.png")


def test_render_report_and_preview(tmp_path: Path) -> None:
    import asyncio

    async def _scenario():
        root = tmp_path / "artifacts" / "competitive-intel" / "run-render"
        _write_fixture_report(root)
        from zuaef_competitive_intelligence.report_tools import make_report_toolset

        toolset = make_report_toolset()
        tools = await _tool_map_async(toolset)
        ctx = RunContext(
            deps=CoreDeps(workspace_root=tmp_path.resolve(), run_id="run-render"),
            usage=RunUsage(),
            model="test",
            prompt="p",
        )
        render = json.loads(await tools["render_report"].call_func({"style": "executive"}, ctx))
        assert (root / "report.pdf").is_file()
        assert (root / "report.docx").is_file()
        assert render["pages"] >= 1
        assert pdf_page_count(root / "report.pdf") == render["pages"]

        preview = json.loads(await tools["render_report_preview"].call_func({"max_pages": 10}, ctx))
        assert preview["page_count"] == render["pages"]
        assert preview["rendered_pages"] == render["pages"]
        assert (root / "preview" / "contact-sheet.png").is_file()
        assert (root / "preview" / "page-001.png").is_file()
        assert preview["contact_sheet"] is not None


    asyncio.run(_scenario())

def test_render_report_missing_report(tmp_path: Path) -> None:
    import asyncio

    async def _scenario():
        from zuaef_competitive_intelligence.report_tools import (
            ReportToolError,
            make_report_toolset,
        )

        toolset = make_report_toolset()
        ctx = RunContext(
            deps=CoreDeps(workspace_root=tmp_path.resolve(), run_id="run-empty"),
            usage=RunUsage(),
            model="test",
            prompt="p",
        )
        payload = json.loads(
            await (await _tool_map_async(toolset))["render_report"].call_func(
                {"style": "executive"}, ctx
            )
        )
        assert payload["error"]["code"] == "REPORT_MISSING"


    asyncio.run(_scenario())

# ── plugin composition ──────────────────────────────────────────────────────


def _plugin_bundle(
    workspace: Path, backend_name: str, **config
) -> PluginBundle:
    base = {
        "domain": "ebike",
        "search_backend": backend_name,
        "output_language": "zh-CN",
        "max_search_results": 10,
        "max_fetch_bytes": 5_000_000,
        "max_preview_chars": 14_000,
    }
    base.update(config)
    return build_plugin(
        PluginEnv(
            plugin_id="competitive-intelligence",
            plugin_version="0.1.0",
            workspace_root=workspace,
            state_root=workspace.parent / ".zuaef-state-test",
        ),
        base,
    )


def test_plugin_factory_fixture_backend(tmp_path: Path) -> None:
    bundle = _plugin_bundle(
        tmp_path, "fixture", fixture_hits=FIXTURE_HITS
    )
    assert len(bundle.toolsets) == 3
    deps = CoreDeps(workspace_root=tmp_path.resolve(), run_id="r1")
    ctx = RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)
    names = set()
    for toolset in bundle.toolsets:
        names |= set(asyncio.run(toolset.get_tools(ctx)))
    assert names == {
        "search_sources",
        "read_source",
        "save_work_product",
        "download_asset",
        "render_report",
        "render_report_preview",
    }
    assert len(bundle.skill_dirs) == 1
    skill_library = bundle.skill_dirs[0]
    assert (skill_library / "e-bike-product-intelligence" / "SKILL.md").is_file()
    assert (skill_library / "executive-competitor-report" / "SKILL.md").is_file()


def test_plugin_factory_unknown_backend(tmp_path: Path) -> None:
    with pytest.raises(CompositionError) as exc_info:
        _plugin_bundle(tmp_path, "google")
    assert "unsupported search_backend" in str(exc_info.value)


def test_plugin_factory_brave_missing_secret_is_loud(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ZUAEF_BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    with pytest.raises(CompositionError) as exc_info:
        _plugin_bundle(tmp_path, "brave")
    assert "no API key" in str(exc_info.value)


def test_plugin_secret_never_in_snapshot(tmp_path: Path) -> None:
    import os

    os.environ["ZUAEF_BRAVE_SEARCH_API_KEY"] = "secret-value"
    try:
        from zuaef_agent.composition import resolve_profile
        from zuaef_agent.config import AgentSettings

        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()
        (profile_dir / "ci-fixture.toml").write_text(
            """schema = 1
name = "ci-fixture"

[generalist]
tool_search = true

[[plugins]]
id = "competitive-intelligence"
defer_tools = true

[plugins.config]
domain = "ebike"
search_backend = "brave"
max_search_results = 5
""",
            encoding="utf-8",
        )
        settings = AgentSettings(
            workspace_root=tmp_path / "workspace",
            runtime_state_root=tmp_path / "state",
        ).with_overrides(enable_tool_search=True)
        snapshot = resolve_profile(
            "ci-fixture", settings, config_root=tmp_path
        )
        serialized = snapshot.model_dump_json()
        assert "secret-value" not in serialized
    finally:
        os.environ.pop("ZUAEF_BRAVE_SEARCH_API_KEY", None)


# ── one end-to-end agent run (function model, fixture backend) ──────────────


def test_agent_run_search_read_save(tmp_path: Path) -> None:
    """One composed agent run: search → read → save over fixtures.

    A stateful scripted FunctionModel drives one normal execute_run — no
    real LLM, no network. Proves the CI tools answer through the shared
    runtime and the artifact lands under the run's CI artifact root.
    """
    bundle = build_plugin(
        PluginEnv(
            plugin_id="competitive-intelligence",
            plugin_version="0.1.0",
            workspace_root=tmp_path.resolve(),
            state_root=tmp_path.resolve() / ".state",
        ),
        {
            "domain": "ebike",
            "search_backend": "fixture",
            "output_language": "zh-CN",
            "max_search_results": 10,
            "max_fetch_bytes": 5_000_000,
            "max_preview_chars": 2000,
            "fixture_hits": FIXTURE_HITS,
        },
    )

    run_id = uuid4().hex
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".state",
        request_limit=8,
        tool_calls_limit=20,
        enable_skills=False,
        enable_knowledge=False,
    )

    steps: list[str] = []

    def _has_tool_return(messages) -> bool:
        return any(
            part.part_kind in ("tool-return", "tool-retry")
            for message in messages
            for part in getattr(message, "parts", [])
        )

    def fn(messages, info):  # type: ignore[no-untyped-def]
        call_id = f"call-{len(steps)}"
        if "search" not in steps:
            steps.append("search")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="search_sources",
                        args=json.dumps(
                            {"query": "Charger5 Riese Müller", "limit": 3}
                        ),
                        tool_call_id=call_id,
                    )
                ]
            )
        if "read" not in steps:
            steps.append("read")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="read_source",
                        args=json.dumps(
                            {"url": "https://www.r-m.de/de/bikes/charger5/"}
                        ),
                        tool_call_id=call_id,
                    )
                ]
            )
        if "save" not in steps:
            steps.append("save")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="save_work_product",
                        args=json.dumps(
                            {
                                "kind": "catalog",
                                "content": (
                                    "model,family,lifecycle\n"
                                    "Charger5,passenger,CURRENT\n"
                                ),
                            }
                        ),
                        tool_call_id=call_id,
                    )
                ]
            )
        return ModelResponse(parts=[TextPart("research complete")])

    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=list(bundle.toolsets),
        extra_skill_dirs=bundle.skill_dirs,
    )
    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(
            agent,
            deps=CoreDeps(workspace_root=workspace.resolve(), run_id=run_id),
            prompt="研究 Charger5 并保存目录。",
            settings=settings,
        )
    assert outcome.receipt.execution_state == "completed"
    assert steps == ["search", "read", "save"]
    catalog = (
        workspace
        / "artifacts"
        / "competitive-intel"
        / run_id
        / "catalog.csv"
    )
    assert catalog.is_file()
