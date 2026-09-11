"""``zuaef-wechat-x`` — 公众号 + X 双节奏创作插件。

One plugin, one deferred writing Skill, one guidance toolset, one corpus seed:

- ``skills/wechat-x-publish`` carries the writing method (style A/B, length
  discipline, X-thread rhythm, forbidden moves) as deferred instructions;
- ``read_guidance`` returns the three plugin-shipped guides (WeChat template,
  X-thread template, image guidelines) because bundled files are never
  auto-loaded by the Skills capability and the model cannot read the
  installed package through the workspace-scoped FileSystem capability;
- the Machine & Soul corpus is seeded once into
  ``<workspace>/knowledge/<namespace>/`` so the host Knowledge capability can
  search it; the skill does not carry the corpus itself.

Brand identity comes from non-secret profile config only, never hardcoded in
the Skill: the factory exposes it through toolset instructions.
"""

from .plugin import create_plugin

__all__ = ["create_plugin"]
