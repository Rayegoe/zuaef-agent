"""Business composition for the v1.1 capability proof gate.

A real Research Toolset over the local engineering guide plus the controlled
side-effect tool whose only external write is a marker under ``.state-proof/``
(outside ``workspace/**`` and ``knowledge/**``, per the frozen SPEC).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import FunctionToolset, RunContext

from zuaef_agent.models import CoreDeps

DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "Outcome-First PydanticAI Agent Engineering Guide v2.0.md"
DEFAULT_MARKER_ROOT = Path(__file__).resolve().parent.parent / ".state-proof"


def build_research_toolset(source_path: Path = DEFAULT_SOURCE) -> FunctionToolset[CoreDeps]:
    source = Path(source_path).resolve()

    def _lines() -> list[str]:
        return source.read_text(encoding="utf-8").splitlines()

    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions="Real research tools over one local source document. Read before you write."
    )

    @toolset.tool
    def list_source_sections(ctx: RunContext[CoreDeps]) -> list[dict[str, str]]:
        """List the source document's headings with line numbers."""
        sections: list[dict[str, str]] = []
        for index, line in enumerate(_lines()):
            if line.startswith("#"):
                sections.append(
                    {
                        "line": str(index + 1),
                        "level": str(len(line) - len(line.lstrip("#"))),
                        "heading": line.lstrip("# ").strip(),
                    }
                )
        return sections

    @toolset.tool
    def read_source_section(ctx: RunContext[CoreDeps], heading: str) -> str:
        """Read one section of the source by its heading text."""
        wanted = heading.strip().lstrip("#").strip().lower()
        out: list[str] = []
        capturing = False
        for line in _lines():
            if line.startswith("#"):
                current = line.lstrip("# ").strip().lower()
                if capturing:
                    break
                capturing = current == wanted
            elif capturing:
                out.append(line)
        text = "\n".join(out).strip()
        return text[:20000] if text else f"(section not found: {heading!r})"

    @toolset.tool
    def search_source(ctx: RunContext[CoreDeps], query: str, limit: int = 8) -> list[dict[str, str]]:
        """Lexically search the source document line by line."""
        bounded = max(1, min(int(limit), 100))
        terms = [t.lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        hits: list[dict[str, str]] = []
        for index, line in enumerate(_lines()):
            low = line.lower()
            if any(term in low for term in terms):
                hits.append({"line": str(index + 1), "text": line.strip()[:300]})
        return hits[:bounded]

    return toolset


def build_state_proof_toolset(marker_root: Path = DEFAULT_MARKER_ROOT) -> FunctionToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()

    @toolset.tool(requires_approval=True)
    def publish_digest(ctx: RunContext[CoreDeps], digest: str) -> str:
        """Publish the research digest (controlled external effect; requires human approval).

        The only external write is a marker file under .state-proof/ — never
        knowledge/**, sources, or the report.
        """
        root = Path(marker_root)
        root.mkdir(parents=True, exist_ok=True)
        conversation = getattr(ctx, "conversation_id", None) or ctx.deps.run_id
        marker = root / f"external-effect-{conversation}.marker"
        marker.write_text(digest[:2000], encoding="utf-8")
        return f"published digest marker {marker.name}"

    return toolset
