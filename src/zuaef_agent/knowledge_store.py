from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_./-]*$")

MAX_SEARCH_RESULTS = 100

# Reserved ids that must never be overwritten by a run.
RESERVED_IDS = frozenset({"index"})


class KnowledgeStore:
    """Small file-native document store using Markdown + YAML frontmatter.

    Document-first (v1.2 SPEC §7): the store is a safe file container for
    Markdown documents with optional tags and optional run provenance. It
    does NOT enforce a semantic type taxonomy and does NOT pretend a
    ``sources`` frontmatter field proves a claim is supported — source URLs
    belong in the document body where a reader can follow them.

    ``index.md`` is a rebuildable projection; document writes are atomic
    (same-dir temp + ``os.replace``).
    """

    def __init__(self, workspace_root: Path):
        self.root = workspace_root.resolve() / "knowledge"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, knowledge_id: str) -> Path:
        """Validate a knowledge id and return its target path inside the root."""
        clean = knowledge_id.strip().removesuffix(".md")
        if not clean or not _ID_RE.fullmatch(clean) or ".." in Path(clean).parts:
            raise ValueError(f"invalid knowledge id: {knowledge_id!r}")
        if clean in RESERVED_IDS:
            raise ValueError(f"knowledge id is reserved: {knowledge_id!r}")
        target = (self.root / f"{clean}.md").resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise ValueError("knowledge path escapes root")
        return target

    # Backwards-compatible alias used by older callers.
    _path_for = path_for

    def write_doc(
        self,
        *,
        knowledge_id: str,
        title: str,
        body: str,
        tags: Iterable[str] = (),
        generated_by: str = "zuaef-agent",
        run_id: str | None = None,
    ) -> str:
        """Write one Markdown+frontmatter document and rebuild the index.

        No semantic type requirement, no source-requirement gate: the store
        records the document and optional provenance, never an epistemic
        verdict. Source URLs live in ``body`` where a reader can follow them.
        """
        target = self.path_for(knowledge_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        frontmatter: dict[str, Any] = {
            "title": title,
            "tags": sorted(set(tags)),
            "generated": {"by": generated_by},
        }
        if run_id:
            frontmatter["generated"]["run_id"] = run_id
        rendered = (
            "---\n"
            + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
            + "\n---\n\n"
        )
        rendered += body.strip() + "\n"
        tmp = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text(rendered, encoding="utf-8")
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        self.rebuild_index()
        return str(target.relative_to(self.root.parent))

    def read_doc(self, knowledge_id: str) -> str:
        return self.path_for(knowledge_id).read_text(encoding="utf-8")

    def search(self, query: str, *, limit: int = 12) -> list[dict[str, str]]:
        if limit <= 0 or limit > MAX_SEARCH_RESULTS:
            raise ValueError(f"limit must be in 1..{MAX_SEARCH_RESULTS}, got {limit}")
        terms = [t.lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        hits: list[tuple[int, dict[str, str]]] = []
        for path in self.root.rglob("*.md"):
            if path.name == "index.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            low = text.lower()
            score = sum(low.count(term) for term in terms)
            if not score:
                continue
            compact = " ".join(
                line.strip()
                for line in text.splitlines()
                if line.strip() and line != "---"
            )
            hits.append(
                (
                    score,
                    {
                        "path": str(path.relative_to(self.root.parent)),
                        "snippet": compact[:500],
                    },
                )
            )
        hits.sort(key=lambda item: (-item[0], item[1]["path"]))
        return [item for _, item in hits[:limit]]

    def list_docs(self) -> list[str]:
        return sorted(
            str(path.relative_to(self.root.parent))
            for path in self.root.rglob("*.md")
            if path.name != "index.md"
        )

    def list_generated_by_run(self, run_id: str) -> list[str]:
        """Return knowledge docs whose frontmatter records this run as generator.

        Provenance only: the returned paths record that THIS run wrote the
        document, not that its content is correct.
        """
        matched: list[str] = []
        for path in self.root.rglob("*.md"):
            if path.name == "index.md":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.startswith("---\n"):
                continue
            try:
                _, raw_frontmatter, _ = text.split("---", 2)
                frontmatter = yaml.safe_load(raw_frontmatter) or {}
            except (ValueError, yaml.YAMLError):
                continue
            generated = (
                frontmatter.get("generated") if isinstance(frontmatter, dict) else None
            )
            if isinstance(generated, dict) and generated.get("run_id") == run_id:
                matched.append(str(path.relative_to(self.root.parent)))
        return sorted(matched)

    def rebuild_index(self) -> str:
        index = self.root / "index.md"
        lines = [
            "# Knowledge Index",
            "",
            "Read only the relevant nodes; do not load the whole corpus by default.",
            "",
        ]
        for rel in self.list_docs():
            target = Path(rel)
            link = target.relative_to("knowledge").as_posix()
            lines.append(f"- [{target.stem}]({link})")
        tmp = index.with_name(f"{index.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
            os.replace(tmp, index)
        finally:
            tmp.unlink(missing_ok=True)
        return str(index.relative_to(self.root.parent))
