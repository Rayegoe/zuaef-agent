"""Small production writing environment over the ACE material store.

The production model sees two actions: ``pull_context(query)`` searches the
bound world and returns a bounded Markdown desk pack; ``save_article(markdown)``
persists the finished article. T006-B2 adds an experimental third action,
``pull_techniques(ids)``, only in the model-owned technique profile. Persistence,
receipts and source bookkeeping remain host concerns.
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

from .epub_corpus import (
    DEFAULT_CORPUS_ROOT,
    MAX_CORPUS_CONTEXT_CHARS,
    render_corpus_search,
    search_corpus,
)

DEFAULT_ACE_ROOT = Path(
    os.environ.get(
        "ACE_ROOT",
        Path.home() / "projects/article-context-engine/article-context-engine",
    )
)
MAX_CONTEXT_CHARS = 18_000
MAX_TECHNIQUE_SHARDS = 3
MAX_TECHNIQUE_CATALOG_CHARS = 6_000
MAX_SELECTED_TECHNIQUE_CHARS = 1_600
TECHNIQUE_SELECTION_MODES = ("host", "none", "model")

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

MODEL_OWNED_TECHNIQUE_INSTRUCTIONS = """\
This run exposes a neutral technique catalog. Technique selection belongs to
you: choose a technique only when you can name a concrete use in the current
materials or task. A technique is an optional resource, not an article
template; zero techniques is valid. If techniques are needed, call
pull_techniques once with 1–3 exact catalog IDs. The host will return exactly
those IDs and will not rank, add or substitute a technique.
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


def _technique_index_records(ace_root: Path) -> list[dict]:
    """Load the existing neutral ACE exemplar index without task ranking."""
    index_path = ace_root / "corpus" / "exemplar_index.jsonl"
    if not index_path.is_file():
        return []
    records: list[dict] = []
    for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        rights = value.get("rights") if isinstance(value, dict) else None
        if (
            isinstance(value, dict)
            and value.get("exemplar_id")
            and value.get("text_ref")
            and value.get("status") == "active"
            and isinstance(rights, dict)
            and rights.get("runtime_allowed") is True
        ):
            records.append(value)
    return records


def _mechanical_excerpt(text: str, limit: int) -> str:
    """Bound a selected shard by prefix; never rank its paragraphs."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[片段按字符预算截断]"


def build_technique_catalog(ace_root: Path = DEFAULT_ACE_ROOT) -> str:
    """Render the existing ACE metadata as a task-neutral model catalog."""
    records = _technique_index_records(ace_root)
    if not records:
        return "TECHNIQUE CATALOG FAILED: no active runtime technique index."
    lines: list[str] = []
    for record in records:
        lines.append(
            " | ".join(
                [
                    str(record["exemplar_id"]),
                    f"function={record.get('primary_function', '')}",
                    "effects=" + ",".join(str(v) for v in record.get("effect_tags") or []),
                    "use_when=" + ",".join(str(v) for v in record.get("use_when") or []),
                    f"interpretation_distance={record.get('interpretation_distance', '')}",
                    f"author_intrusion={record.get('author_intrusion', '')}",
                ]
            )
        )
    return _mechanical_excerpt("\n".join(lines), MAX_TECHNIQUE_CATALOG_CHARS)


def retrieve_selected_techniques_impl(
    technique_ids: list[str],
    *,
    ace_root: Path = DEFAULT_ACE_ROOT,
) -> str:
    """Return exactly the requested active ACE shards in request order."""
    ids = [str(value).strip() for value in technique_ids]
    if len(ids) > MAX_TECHNIQUE_SHARDS:
        return (
            "TECHNIQUES FAILED: at most "
            f"{MAX_TECHNIQUE_SHARDS} technique ids are allowed."
        )
    if len(ids) != len(set(ids)):
        return "TECHNIQUES FAILED: duplicate technique ids are not allowed."

    records = {
        str(record["exemplar_id"]): record
        for record in _technique_index_records(ace_root)
    }
    missing = [value for value in ids if value not in records]
    if missing:
        return "TECHNIQUES FAILED: unknown technique id(s): " + ", ".join(missing)

    rendered: list[str] = [
        "TECHNIQUE_SELECTION: " + (", ".join(ids) if ids else "none"),
    ]
    for technique_id in ids:
        record = records[technique_id]
        body = _read_relative(ace_root, str(record["text_ref"]))
        if not body:
            return f"TECHNIQUES FAILED: missing body for {technique_id}."
        rendered.extend(
            [
                f"### {technique_id}",
                "",
                _mechanical_excerpt(body, MAX_SELECTED_TECHNIQUE_CHARS),
                "",
                "不要复制原句。这个片段只用于理解一种可能的叙事运动。",
                "",
                f"来源：{record.get('source_ref', record['text_ref'])}",
                "",
            ]
        )
    return "\n".join(rendered).strip()


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
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    include_technique_guidance: bool = True,
    technique_selection_mode: str = "host",
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """Search the bound world and render one bounded Markdown desk pack.

    ``include_technique_guidance`` is the T006-B1 experiment control.
    ``technique_selection_mode`` is the T006-B2 benchmark seam: ``host``
    keeps current production behavior, ``none`` omits technique projection,
    and ``model`` exposes only a neutral catalog. It does not rank records.
    """
    if technique_selection_mode not in TECHNIQUE_SELECTION_MODES:
        raise ValueError(
            "technique_selection_mode must be one of "
            f"{TECHNIQUE_SELECTION_MODES}, got {technique_selection_mode!r}"
        )
    if technique_selection_mode != "host" and not include_technique_guidance:
        raise ValueError(
            "include_technique_guidance=false cannot be combined with "
            f"technique_selection_mode={technique_selection_mode!r}"
        )
    effective_mode = (
        "host" if include_technique_guidance else "none"
    ) if technique_selection_mode == "host" else technique_selection_mode
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
    corpus_context = render_corpus_search(
        search_corpus(corpus_root, query),
        max_chars=MAX_CORPUS_CONTEXT_CHARS,
    )
    techniques = (
        _technique_section(article_id, query, run_id, ace_root)
        if effective_mode == "host"
        else ""
    )
    technique_catalog = (
        build_technique_catalog(ace_root) if effective_mode == "model" else ""
    )
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
    if corpus_context:
        sections.extend(["", corpus_context])
    if techniques:
        sections.extend(["", "## 可参考的写作片段 / 技巧", "", techniques])
    if technique_catalog:
        sections.extend(
            [
                "",
                "## 可按需选择的 technique catalog",
                "",
                (
                    "这是现有 corpus 的中性 metadata，不是文章模板或写作指令。"
                    "只有能指出具体用途时才选择；0 个合法。若需要，选择 1–3 个"
                    "准确 ID，并一次调用 pull_techniques；Host 不会替你排序或补选。"
                ),
                "",
                technique_catalog,
            ]
        )
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
        corpus_root: Path = DEFAULT_CORPUS_ROOT,
        include_technique_guidance: bool = True,
        technique_selection_mode: str = "host",
    ) -> None:
        if technique_selection_mode not in TECHNIQUE_SELECTION_MODES:
            raise ValueError(
                "technique_selection_mode must be one of "
                f"{TECHNIQUE_SELECTION_MODES}, got {technique_selection_mode!r}"
            )
        if technique_selection_mode != "host" and not include_technique_guidance:
            raise ValueError(
                "include_technique_guidance=false cannot be combined with "
                f"technique_selection_mode={technique_selection_mode!r}"
            )
        instructions = WRITER_INSTRUCTIONS
        if technique_selection_mode == "model":
            instructions += "\n" + MODEL_OWNED_TECHNIQUE_INSTRUCTIONS
        super().__init__(instructions=instructions)
        self.ace_root = ace_root
        self.learning_root = learning_root
        self.corpus_root = corpus_root
        self.include_technique_guidance = include_technique_guidance
        self.technique_selection_mode = technique_selection_mode


def build_writing_toolset(
    ace_root: Path = DEFAULT_ACE_ROOT,
    *,
    learning_root: Path | None = None,
    corpus_root: Path = DEFAULT_CORPUS_ROOT,
    include_technique_guidance: bool = True,
    technique_selection_mode: str = "host",
) -> WritingEnvironmentToolset:
    toolset = WritingEnvironmentToolset(
        ace_root=ace_root,
        learning_root=learning_root,
        corpus_root=corpus_root,
        include_technique_guidance=include_technique_guidance,
        technique_selection_mode=technique_selection_mode,
    )

    @toolset.tool(metadata={"code_mode": True})
    def pull_context(ctx: RunContext[CoreDeps], query: str) -> str:
        """Search all bound sources for one semantic need and return Markdown."""
        article_id = ctx.deps.bindings.get("writing_article_id", ctx.deps.run_id)
        bound_corpus_root = ctx.deps.bindings.get("writing_corpus_root")
        effective_corpus_root = (
            Path(bound_corpus_root).expanduser().resolve()
            if bound_corpus_root
            else corpus_root
        )
        return build_writer_context(
            article_id,
            query,
            run_id=ctx.deps.run_id,
            ace_root=ace_root,
            learning_root=learning_root,
            corpus_root=effective_corpus_root,
            include_technique_guidance=include_technique_guidance,
            technique_selection_mode=technique_selection_mode,
        )

    if technique_selection_mode == "model":

        @toolset.tool
        def pull_techniques(
            ctx: RunContext[CoreDeps], technique_ids: list[str]
        ) -> str:
            """Return exactly 0–3 selected technique shards in request order."""
            return retrieve_selected_techniques_impl(
                technique_ids,
                ace_root=ace_root,
            )

    @toolset.tool
    def save_article(ctx: RunContext[CoreDeps], markdown: str) -> str:
        """Save the complete article. Pass Markdown only."""
        return save_article_impl(markdown, ctx.deps.workspace_root, ctx.deps.run_id)

    return toolset
