from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from .knowledge_store import KnowledgeStore
from .models import CoreDeps, SourceRef


@dataclass
class Knowledge(AbstractCapability[CoreDeps]):
    """File-native knowledge operations with evidence-preserving writes."""

    def get_toolset(self) -> AgentToolset[CoreDeps] | None:
        toolset: FunctionToolset[CoreDeps] = FunctionToolset(
            instructions=(
                "Knowledge files are durable evidence-backed artifacts. Search/read before writing. "
                "Never invent a source URL or evidence locator. Use knowledge ids such as "
                "concepts/agent-harness or sources/youtube-abc123. Valid doc types: "
                "concept, claim, method, reference (each requires >=1 source) or "
                "project-note, decision, user-authored-note (no source required)."
            )
        )

        @toolset.tool
        def search_knowledge(ctx: RunContext[CoreDeps], query: str, limit: int = 12) -> list[dict[str, str]]:
            """Lexically search the file-native knowledge corpus."""
            return KnowledgeStore(ctx.deps.workspace_root).search(query, limit=limit)

        @toolset.tool
        def read_knowledge(ctx: RunContext[CoreDeps], knowledge_id: str) -> str:
            """Read one knowledge node by id, e.g. concepts/agent-harness.

            Returns an error string when the node does not exist, so a bad or
            invented knowledge id is a recoverable tool result, not a fatal
            exception (Writing v0.2 field experience: an agent once conflated
            ACE evidence hints with ZUAEF workspace knowledge ids and the
            resulting FileNotFoundError blocked the whole run)."""
            try:
                return KnowledgeStore(ctx.deps.workspace_root).read_doc(knowledge_id)
            except (ValueError, OSError) as exc:
                return (
                    f"NO SUCH KNOWLEDGE NODE: {knowledge_id!r} — {type(exc).__name__}: {exc}. "
                    "Use list_knowledge to see the actual node ids; workspace "
                    "knowledge is NOT the ACE evidence corpus."
                )

        @toolset.tool
        def list_knowledge(ctx: RunContext[CoreDeps]) -> list[str]:
            """List knowledge documents without loading their bodies."""
            return KnowledgeStore(ctx.deps.workspace_root).list_docs()

        @toolset.tool
        def write_knowledge(
            ctx: RunContext[CoreDeps],
            knowledge_id: str,
            doc_type: str,
            title: str,
            body: str,
            tags: list[str] | None = None,
            sources: list[SourceRef] | None = None,
        ) -> str:
            """Write one Markdown+frontmatter knowledge node and rebuild the progressive index."""
            return KnowledgeStore(ctx.deps.workspace_root).write_doc(
                knowledge_id=knowledge_id,
                doc_type=doc_type,
                title=title,
                body=body,
                tags=tags or [],
                sources=sources or [],
                run_id=ctx.deps.run_id,
            )

        return toolset
