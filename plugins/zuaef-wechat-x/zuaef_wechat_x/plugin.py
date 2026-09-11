"""``zuaef-wechat-x`` plugin factory.

Config (non-secret composition identity only):
    account_name, pen_name, slogan, audience, tone, corpus_namespace

The factory does two deterministic things:
1. seeds the bundled Machine & Soul corpus into
   ``<workspace>/knowledge/<corpus_namespace>/`` (idempotent: an existing
   target is never overwritten), so the host Knowledge capability can search
   it; a failed seed degrades to a note in the toolset instructions instead
   of breaking composition;
2. returns one toolset (brand identity instructions + ``read_guidance`` +
   ``save_deliverable``) plus the plugin's Skill directory.

``save_deliverable`` exists because ``artifacts/*`` is a protected FileSystem
pattern: generic file tools cannot write the artifact tree, and files written
elsewhere are not host-verified into the run receipt. The tool writes under
``artifacts/wechat-x/<slug>/`` so every published deliverable is receipt-visible.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .guidance import GUIDANCE_FILES, load_guidance

_ALLOWED_CONFIG_KEYS = {
    "account_name",
    "pen_name",
    "slogan",
    "audience",
    "tone",
    "corpus_namespace",
}

_PACKAGE_DIR = Path(__file__).resolve().parent
_CORPUS_SOURCE = _PACKAGE_DIR / "corpus"
_SKILLS_DIR = _PACKAGE_DIR / "skills"
_DEFAULT_NAMESPACE = "wechat-x"
_NAMESPACE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MAX_DELIVERABLE_BYTES = 1_000_000

_DELIVERABLE_FILENAMES: dict[str, str] = {
    "article": "article.md",
    "x-thread": "x-thread.md",
    "image-prompts": "images/image-prompts.md",
}

DEFAULT_AUDIENCE = "中小企业老板、业务负责人"
DEFAULT_TONE = (
    "面向业务决策者：短句给节奏，判断给重量，具体给信任；"
    "不回避复杂性，但不把复杂性扔给读者。"
)


def _seed_corpus(workspace_root: Path, namespace: str) -> str:
    """Copy the bundled corpus once; never overwrite a seeded namespace."""
    if not _CORPUS_SOURCE.is_dir():
        return "corpus unavailable: plugin package carries no corpus directory"
    target = workspace_root / "knowledge" / namespace
    if target.exists():
        return f"corpus ready at knowledge/{namespace}/ (existing, not overwritten)"
    try:
        import shutil

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(_CORPUS_SOURCE, target)
    except OSError as exc:  # read-only or missing workspace must not break composition
        return f"corpus seed failed ({type(exc).__name__}: {exc}); search may find nothing"
    return f"corpus seeded at knowledge/{namespace}/"


def _error(code: str, message: str) -> str:
    return json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False)


def _deliverable_path(workspace_root: Path, slug: str, kind: str) -> Path:
    if not _SLUG_RE.fullmatch(slug) or slug in {".", ".."}:
        raise ValueError(f"unsafe slug {slug!r}; use letters, digits, dot, dash, underscore")
    filename = _DELIVERABLE_FILENAMES[kind]
    root = workspace_root / "artifacts" / "wechat-x" / slug
    target = (root / filename).resolve()
    if not target.is_relative_to(workspace_root.resolve()):
        raise ValueError("deliverable path escapes the workspace")
    return target


def create_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    unknown = sorted(set(config) - _ALLOWED_CONFIG_KEYS)
    if unknown:
        raise CompositionError(
            "wechat-x config keys not allowed: "
            + ", ".join(unknown)
            + "; allowed: "
            + ", ".join(sorted(_ALLOWED_CONFIG_KEYS))
        )

    account_name = str(config.get("account_name") or "").strip()
    pen_name = str(config.get("pen_name") or "").strip()
    slogan = str(config.get("slogan") or "").strip()
    audience = str(config.get("audience") or DEFAULT_AUDIENCE).strip()
    tone = str(config.get("tone") or DEFAULT_TONE).strip()
    namespace = str(config.get("corpus_namespace") or _DEFAULT_NAMESPACE).strip()
    if not _NAMESPACE_RE.fullmatch(namespace):
        raise CompositionError(
            f"wechat-x corpus_namespace must match {_NAMESPACE_RE.pattern!r}, got {namespace!r}"
        )

    corpus_note = _seed_corpus(env.workspace_root, namespace)

    identity_lines = [
        "公众号 + X 双节奏创作部署：同一组素材，两种呼吸节奏。",
        f"账号身份（写作时使用；未配置则先向用户确认，不要写死别的账号）：账号名={account_name or '未配置'}；署名={pen_name or '未配置'}；标语={slogan or '未配置'}。",
        f"目标读者：{audience}",
        f"语气底色：{tone}",
        "模板与配图规范必须用 read_guidance 读取（wechat-template / x-thread-template / image-guidelines）。",
        f"语料：{corpus_note}；用 search_knowledge / read_knowledge 检索（主题页 → bridges → concepts/sources）。",
        "交付物必须用 save_deliverable 保存到 artifacts/wechat-x/<slug>/；write_file 无法写入 artifacts/**，写别处不会被 receipt 记账。",
        "写作前先加载 wechat-x-publish skill（流程要求，不是可选项）。",
    ]

    toolset: FunctionToolset[CoreDeps] = FunctionToolset(instructions="\n".join(identity_lines))

    @toolset.tool
    def read_guidance(ctx: RunContext[CoreDeps], kind: str) -> str:
        """Read one plugin-shipped writing guide.

        kind is one of: wechat-template (公众号结构/frontmatter 规范),
        x-thread-template (线程节奏规范), image-guidelines (配图视觉规范).
        中文关键词：模板、公众号模板、线程模板、配图规范。
        """
        try:
            return load_guidance(kind)
        except KeyError:
            return (
                f"UNKNOWN GUIDANCE {kind!r}; available: "
                + ", ".join(sorted(GUIDANCE_FILES))
            )

    @toolset.tool
    def save_deliverable(
        ctx: RunContext[CoreDeps], kind: str, content: str, slug: str
    ) -> str:
        """Persist one写作交付物 under artifacts/wechat-x/<slug>/.

        kind is one of: article (article.md), x-thread (x-thread.md),
        image-prompts (images/image-prompts.md). Overwrites the previous
        version of the same file. Files written here are host-verified into
        the run receipt; generic file tools cannot write under artifacts/**.
        中文关键词：保存文章、保存公众号、保存线程、保存配图提示词。
        """
        if kind not in _DELIVERABLE_FILENAMES:
            return _error(
                "INVALID_KIND",
                f"kind {kind!r} not allowed; choose one of "
                + ", ".join(sorted(_DELIVERABLE_FILENAMES)),
            )
        data = content.encode("utf-8")
        if len(data) > _MAX_DELIVERABLE_BYTES:
            return _error(
                "TOO_LARGE",
                f"{len(data)} bytes exceeds the {_MAX_DELIVERABLE_BYTES} byte limit",
            )
        try:
            target = _deliverable_path(ctx.deps.workspace_root, slug, kind)
        except ValueError as exc:
            return _error("INVALID_SLUG", str(exc))
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        return json.dumps(
            {
                "kind": kind,
                "path": str(target.relative_to(ctx.deps.workspace_root)),
                "bytes": len(data),
            },
            ensure_ascii=False,
        )

    skill_dirs = [_SKILLS_DIR] if _SKILLS_DIR.is_dir() else []
    return PluginBundle(toolsets=[toolset], skill_dirs=skill_dirs)


__all__ = ["create_plugin"]
