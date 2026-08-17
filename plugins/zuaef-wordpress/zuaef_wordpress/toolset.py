"""WordPress toolset — SPEC v0.3 §49–§53.

Four tools, exact names, effect-classified: observation is read-only;
create/update/publish are ``external_write`` and therefore carry PydanticAI
native ``requires_approval``. The Gateway never imports this module — it
composes through the profile entry point only.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.effects import EffectClass, requires_approval
from zuaef_agent.models import CoreDeps

from .client import WordPressClient

TOOLSET_INSTRUCTIONS = """\
WordPress operations on the configured site.

- wordpress_get_post is read-only observation.
- wordpress_create_draft, wordpress_update_post and wordpress_publish_post are
  external writes to the remote WordPress site; they require explicit human
  approval before execution and settle as tool effects in the run receipt.
"""


def make_toolset(client: WordPressClient) -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=TOOLSET_INSTRUCTIONS
    )

    @toolset.tool_plain
    def wordpress_get_post(post_id: int) -> str:
        """Fetch one WordPress post's identity and summary fields (never full HTML)."""
        return _json(client.get_post(post_id))

    @toolset.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def wordpress_create_draft(
        title: str, content: str, excerpt: str | None = None
    ) -> str:
        """Create a DRAFT post on the remote WordPress site (external write)."""
        return _json(client.create_draft(title=title, content=content, excerpt=excerpt))

    @toolset.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def wordpress_update_post(
        post_id: int,
        title: str | None = None,
        content: str | None = None,
        excerpt: str | None = None,
    ) -> str:
        """Update fields of an existing post on the remote site (external write)."""
        return _json(
            client.update_post(
                post_id, title=title, content=content, excerpt=excerpt
            )
        )

    @toolset.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def wordpress_publish_post(post_id: int) -> str:
        """Publish a draft post on the remote WordPress site (external write)."""
        return _json(client.publish_post(post_id))

    return toolset


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
