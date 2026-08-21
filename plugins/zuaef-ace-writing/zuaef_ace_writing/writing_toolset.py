"""Small production writing environment over the ACE material store.

The model sees two actions only: ``pull_context(query)`` searches the bound
world and returns a bounded Markdown desk pack; ``save_article(markdown)``
persists the finished article. Persistence, receipts and source bookkeeping
remain host concerns.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps

DEFAULT_ACE_ROOT = Path(
    os.environ.get(
        "ACE_ROOT",
        Path.home() / "projects/article-context-engine/article-context-engine",
    )
)
MAX_CONTEXT_CHARS = 18_000
MAX_TECHNIQUE_SHARDS = 3

WRITER_INSTRUCTIONS = """\
You are the writer. The host gives you a bounded desk pack and keeps all
operational state out of your context. You own meaning, selection, viewpoint,
narrative, factual restraint and language. Do not turn those judgments into a
workflow. Call pull_context only when the desk pack leaves a concrete question
unanswered. Technique examples are possibilities, never rules or factual
sources, and their wording must not be copied. Before finishing, reread the
article for premature conclusions, repetitive paragraph shapes, missing human
presence, forced brand insertion and claims that exceed the supplied material.
Submit the complete article with save_article(markdown).
"""


def _ace(
    ace_root: Path,
    *args: str,
    input_text: str | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(ace_root / "tools" / "ctx.py"), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        input=input_text,
    )


def ace_prepare(
    article_id: str,
    *,
    title: str = "",
    account: str = "",
    materials: list[str] | None = None,
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> dict:
    """Create an ACE workspace and ingest the host-bound source files."""
    if not (ace_root / "workspaces" / article_id).exists():
        result = _ace(
            ace_root,
            "new",
            article_id,
            "--title",
            title,
            *(["--account", account] if account else []),
        )
        if result.returncode != 0:
            raise RuntimeError(f"ctx.py new failed: {result.stderr or result.stdout}")
    if materials:
        result = _ace(ace_root, "ingest", article_id, *materials)
        if result.returncode != 0:
            raise RuntimeError(
                f"ctx.py ingest failed: {result.stderr or result.stdout}"
            )
    return {"article_id": article_id, "materials": materials or []}


def list_materials_impl(
    article_id: str, run_id: str = "", ace_root: Path = DEFAULT_ACE_ROOT
) -> str:
    result = _ace(ace_root, "materials", article_id, "--run-id", run_id)
    return (
        result.stdout
        if result.returncode == 0
        else f"MATERIALS FAILED: {result.stderr or result.stdout}"
    )


def read_material_impl(
    article_id: str,
    material_id: str,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    result = _ace(
        ace_root, "material", article_id, material_id, "--run-id", run_id
    )
    return (
        result.stdout
        if result.returncode == 0
        else f"MATERIAL READ FAILED: {result.stderr or result.stdout}"
    )


def _query_terms(value: str | list[str]) -> list[str]:
    raw = " ".join(str(item) for item in value) if isinstance(value, list) else value
    return re.findall(r"[a-zA-Z0-9_-]+|[\u4e00-\u9fff]{2,8}", raw.lower())[:16]


def retrieve_exemplars_impl(
    article_id: str,
    query: str | list[str],
    *,
    tags: list[str] | None = None,
    budget: int = MAX_TECHNIQUE_SHARDS,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    args = [
        "exemplars",
        article_id,
        "--query",
        *_query_terms(query),
        "--budget",
        str(budget),
        "--execution-id",
        "writer-context",
        "--run-id",
        run_id,
    ]
    if tags:
        args.extend(["--tags", *tags])
    result = _ace(ace_root, *args)
    return (
        result.stdout
        if result.returncode == 0
        else f"EXEMPLARS FAILED: {result.stderr or result.stdout}"
    )


def _lexical_units(value: str) -> set[str]:
    units = set(re.findall(r"[a-zA-Z0-9_-]+", value.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]+", value):
        units.update(run[i : i + 2] for i in range(max(0, len(run) - 1)))
    return units


def _relevance(text: str, query: str) -> int:
    return len(_lexical_units(text) & _lexical_units(query))


def _bounded_excerpt(text: str, query: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    ranked = sorted(
        enumerate(paragraphs),
        key=lambda item: (-_relevance(item[1], query), item[0]),
    )
    chosen: list[tuple[int, str]] = []
    used = 0
    for index, paragraph in ranked:
        if used >= limit:
            break
        room = limit - used
        chosen.append((index, paragraph[:room]))
        used += min(len(paragraph), room) + 2
    chosen.sort()
    return "\n\n".join(paragraph for _, paragraph in chosen).strip()


def _material_rows(output: str) -> list[dict]:
    rows: list[dict] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("id"):
            rows.append(value)
    return rows


def _material_body(output: str) -> str:
    lines = output.splitlines()
    if lines and lines[0].startswith("MATERIAL "):
        lines = lines[2:]
    if lines and lines[-1].startswith("RECEIPT "):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _technique_tags(query: str) -> list[str]:
    tags = {"ordinary_prose", "low_rhetorical_density"}
    if any(word in query for word in ("人", "采访", "用户", "场景", "现场")):
        tags.update(("human_presence", "scene_preserving"))
    if any(word in query.lower() for word in ("ai", "模板", "开头", "改稿", "反馈")):
        tags.add("human_presence")
    if any(word in query for word in ("品牌", "产品", "知识", "解释")):
        tags.add("knowledge_braid")
    return sorted(tags)


def _parse_technique_records(output: str) -> list[dict]:
    records: list[dict] = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("text_ref"):
            records.append(value)
    return records


def _read_relative(root: Path, relative: str) -> str:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        return ""
    return target.read_text(encoding="utf-8", errors="replace").strip()


def _technique_section(
    article_id: str, query: str, run_id: str, ace_root: Path
) -> str:
    raw = retrieve_exemplars_impl(
        article_id,
        [],
        tags=_technique_tags(query),
        run_id=run_id,
        ace_root=ace_root,
    )
    records = _parse_technique_records(raw)
    if not records:
        raw = retrieve_exemplars_impl(
            article_id, [], run_id=run_id, ace_root=ace_root
        )
        records = _parse_technique_records(raw)
    rendered: list[str] = []
    for record in records[:MAX_TECHNIQUE_SHARDS]:
        body = _read_relative(ace_root, str(record["text_ref"]))
        if not body:
            continue
        rendered.append(
            "\n".join(
                [
                    f"### {record.get('exemplar_id', '技巧片段')}",
                    "",
                    _bounded_excerpt(body, query, 1_600),
                    "",
                    "不要复制原句。这个片段只用于理解一种可能的叙事运动。",
                    "",
                    f"来源：{record.get('source_ref', record['text_ref'])}",
                ]
            )
        )
    return "\n\n".join(rendered)


def _experience_section(query: str, learning_root: Path | None) -> str:
    if learning_root is None or not learning_root.is_dir():
        return ""
    candidates: list[tuple[int, Path]] = []
    for review in learning_root.glob("cases/*/human-review.md"):
        revised = review.with_name("revised.md")
        combined = review.read_text(encoding="utf-8", errors="replace")
        if revised.is_file():
            combined += "\n" + revised.read_text(encoding="utf-8", errors="replace")
        score = _relevance(combined, query)
        if score:
            candidates.append((score, review))
    if not candidates:
        return ""
    _, review = max(candidates, key=lambda item: (item[0], item[1].as_posix()))
    revised = review.with_name("revised.md")
    parts = [
        "### 过去编辑真正改过的地方",
        "",
        _bounded_excerpt(
            review.read_text(encoding="utf-8", errors="replace"), query, 1_800
        ),
    ]
    if revised.is_file():
        parts.extend(
            [
                "",
                "### 人工采纳后的稿件",
                "",
                _bounded_excerpt(
                    revised.read_text(encoding="utf-8", errors="replace"),
                    query,
                    1_500,
                ),
            ]
        )
    return "\n".join(parts)


def build_writer_context(
    article_id: str,
    query: str,
    *,
    run_id: str = "",
    ace_root: Path = DEFAULT_ACE_ROOT,
    learning_root: Path | None = None,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """Search the bound world and render one bounded Markdown desk pack."""
    rows = _material_rows(list_materials_impl(article_id, run_id, ace_root))
    material_budget = 11_000
    per_material = max(1_200, material_budget // max(1, len(rows)))
    material_parts: list[str] = []
    direct_matches = 0
    for row in rows:
        material_id = str(row["id"])
        body = _material_body(
            read_material_impl(article_id, material_id, run_id, ace_root)
        )
        direct_matches += int(_relevance(body, query) > 0)
        material_parts.append(
            "\n".join(
                [
                    f"### [{material_id}] {row.get('filename', '')}".rstrip(),
                    "",
                    _bounded_excerpt(body, query, per_material),
                ]
            )
        )

    experience = _experience_section(query, learning_root)
    techniques = _technique_section(article_id, query, run_id, ace_root)
    sections = [
        "# 当前可用材料",
        "",
        "## 与当前问题最相关的原始材料",
        "",
        "\n\n".join(material_parts) if material_parts else "没有绑定材料。",
        "",
        "## 事实边界",
        "",
        f"已搜索全部 {len(rows)} 份绑定材料。",
    ]
    if rows and direct_matches == 0:
        sections.append(
            "没有找到与本次查询直接匹配的原文；不要把查询中的具体说法写成事实。"
        )
    else:
        sections.append(
            "只有材料中明确出现的内容才能写成事实；推断应保留分寸和限定。"
        )
    if experience:
        sections.extend(["", "## 相关的真实人工修改", "", experience])
    if techniques:
        sections.extend(["", "## 可参考的写作片段 / 技巧", "", techniques])
    context = "\n".join(sections).strip()
    if len(context) > max_chars:
        context = context[: max_chars - 80].rstrip() + "\n\n[案头材料已按上下文预算截断]"
    return context


def save_article_impl(markdown: str, workspace_root: Path, run_id: str) -> str:
    """Persist one article; no model-authored ledger or semantic gate."""
    article = markdown.strip()
    if not article:
        return "文章为空，未保存。"
    artifact_root = (workspace_root / "artifacts").resolve()
    target = (artifact_root / run_id / "final.md").resolve()
    if not target.is_relative_to(artifact_root):
        raise ValueError(f"unsafe run id for artifact path: {run_id!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(article + "\n", encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    relative = target.relative_to(workspace_root.resolve()).as_posix()
    return f"文章已保存：{relative}（{len(article)} 字符，sha256={digest}）"


class WritingEnvironmentToolset(FunctionToolset[CoreDeps]):
    """The production writer's complete model-visible action surface."""

    def __init__(
        self,
        *,
        ace_root: Path,
        learning_root: Path | None = None,
    ) -> None:
        super().__init__(instructions=WRITER_INSTRUCTIONS)
        self.ace_root = ace_root
        self.learning_root = learning_root


def build_writing_toolset(
    ace_root: Path = DEFAULT_ACE_ROOT,
    *,
    learning_root: Path | None = None,
) -> WritingEnvironmentToolset:
    toolset = WritingEnvironmentToolset(
        ace_root=ace_root, learning_root=learning_root
    )

    @toolset.tool(metadata={"code_mode": True})
    def pull_context(ctx: RunContext[CoreDeps], query: str) -> str:
        """Search all bound sources for one semantic need and return Markdown."""
        article_id = ctx.deps.bindings.get("writing_article_id", ctx.deps.run_id)
        return build_writer_context(
            article_id,
            query,
            run_id=ctx.deps.run_id,
            ace_root=ace_root,
            learning_root=learning_root,
        )

    @toolset.tool
    def save_article(ctx: RunContext[CoreDeps], markdown: str) -> str:
        """Save the complete article. Pass Markdown only."""
        return save_article_impl(markdown, ctx.deps.workspace_root, ctx.deps.run_id)

    return toolset
