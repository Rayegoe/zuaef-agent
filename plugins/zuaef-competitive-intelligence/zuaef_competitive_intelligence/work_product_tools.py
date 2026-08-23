"""Work-product tools: ``save_work_product`` and ``download_asset``.

All writes stay confined below ``workspace/artifacts/competitive-intel/
<run_id>/`` (PRD FR-8). Generic FileSystem cannot write under ``artifacts/**``
(core protection), so model-owned research content reaches the artifact
tree only through these tools. No content quality gate, no manifest ledger:
the model owns the semantics, the host validates path/size/encoding.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.models import CoreDeps

from .network import NetworkError, fetch_binary, make_client

_ALLOWED_KINDS = ("notes", "catalog", "evidence", "conflicts", "report", "qa")
_KIND_FILENAMES = {
    "notes": "analyst-notes.md",
    "catalog": "catalog.csv",
    "evidence": "evidence.md",
    "conflicts": "conflicts.md",
    "report": "report.md",
    "qa": "qa.md",
}
_MAX_WORK_PRODUCT_BYTES = 4_000_000
_MAX_ASSET_BYTES = 10_000_000
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_IMAGE_SUFFIXES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class WorkProductError(RuntimeError):
    """Model-visible tool failure with a stable machine code prefix."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def artifact_root(workspace_root: Path, run_id: str) -> Path:
    """Current run's CI artifact root — the only writable CI tree."""
    return workspace_root / "artifacts" / "competitive-intel" / run_id


def _safe_run_dir(workspace_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise WorkProductError("INVALID_RUN", f"unsafe run id {run_id!r}")
    return artifact_root(workspace_root, run_id)


def make_work_product_toolset(
    *,
    max_asset_bytes: int = _MAX_ASSET_BYTES,
    timeout_seconds: float = 30.0,
    client_factory: Any = make_client,
) -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=(
            "Work products are the business deliverable: save model-owned "
            "research/report content under the current run's CI artifact "
            "tree via save_work_product, and collect report images via "
            "download_asset. The host validates path/size/encoding only — "
            "the model owns the content and its sources. Every evidence/"
            "catalog/report note should name inspectable source URLs."
        )
    )

    @toolset.tool
    async def save_work_product(
        ctx: RunContext[CoreDeps], kind: str, content: str
    ) -> str:
        """Persist one model-owned research/report file under the current
        run's CI artifact directory.

        kind is one of: notes (analyst-notes.md), catalog (catalog.csv),
        evidence (evidence.md), conflicts (conflicts.md), report (report.md),
        qa (qa.md). Overwrites the previous version of the same file in this
        run only; never touches another run's tree.

        中文关键词：保存成果、写入目录、产品清单CSV、证据文件、分析笔记、报告文件。
        """
        if kind not in _ALLOWED_KINDS:
            raise WorkProductError(
                "INVALID_KIND",
                f"kind {kind!r} not allowed; choose one of "
                + ", ".join(sorted(_ALLOWED_KINDS)),
            )
        if content is None or not isinstance(content, str):
            raise WorkProductError("INVALID_CONTENT", "content must be a string")
        data = content.encode("utf-8")
        if len(data) > _MAX_WORK_PRODUCT_BYTES:
            raise WorkProductError(
                "CONTENT_TOO_LARGE",
                f"content is {len(data)} bytes, over the "
                f"{_MAX_WORK_PRODUCT_BYTES}-byte cap",
            )
        root = _safe_run_dir(ctx.deps.workspace_root, ctx.deps.run_id)
        root.mkdir(parents=True, exist_ok=True)
        target = root / _KIND_FILENAMES[kind]
        _atomic_write(target, data)
        return json.dumps(
            {
                "kind": kind,
                "filename": target.name,
                "path": str(target.relative_to(ctx.deps.workspace_root)),
                "size": len(data),
                "run_id": ctx.deps.run_id,
            },
            ensure_ascii=False,
        )

    @toolset.tool
    async def download_asset(ctx: RunContext[CoreDeps], url: str, name: str) -> str:
        """Download one public image into the current run's assets/
        directory (image content types only, size-capped, sanitized
        filename). Returns the local path with the original source URL.

        中文关键词：下载图片、产品图片、保存图片素材。
        """
        url = url.strip()
        name = (name or "").strip()
        if not url:
            raise WorkProductError("INVALID_URL", "url must not be empty")
        if not name:
            raise WorkProductError("INVALID_NAME", "name must not be empty")
        client = client_factory(timeout_seconds=timeout_seconds)
        try:
            with client:
                document = fetch_binary(
                    url,
                    client,
                    max_bytes=max_asset_bytes,
                )
        except NetworkError as exc:
            raise WorkProductError(exc.code, exc.message) from exc
        except httpx.HTTPError as exc:
            raise WorkProductError(
                "FETCH_BLOCKED",
                f"network error downloading {url!r}: {type(exc).__name__}: {exc}",
            ) from exc
        base = _SAFE_FILENAME.sub("_", name).strip("._")
        base = re.sub(r"\.{2,}", ".", base)
        if not base:
            raise WorkProductError(
                "INVALID_NAME", f"name {name!r} sanitizes to an empty filename"
            )
        filename = f"{base}{_IMAGE_SUFFIXES[document.content_type]}"
        root = _safe_run_dir(ctx.deps.workspace_root, ctx.deps.run_id)
        assets = root / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        target = assets / filename
        _atomic_write(target, document.data)
        return json.dumps(
            {
                "path": str(target.relative_to(ctx.deps.workspace_root)),
                "size": len(document.data),
                "content_type": document.content_type,
                "source_url": document.final_url,
                "run_id": ctx.deps.run_id,
            },
            ensure_ascii=False,
        )

    return toolset


def _atomic_write(target: Path, data: bytes) -> None:
    """Write-then-replace so a failed write never leaves a partial file."""
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_bytes(data)
    tmp.replace(target)
