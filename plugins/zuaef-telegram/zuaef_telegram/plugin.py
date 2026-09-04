"""``zuaef-telegram`` plugin factory.

The plugin exposes exactly two model-visible actions — ``report_to_telegram``
(approval-gated external write) and ``send_artifact_to_supervisor``
(host-scoped operator self-delivery) — over the existing plugin composition
ABI (one distribution, one Toolset, optional deferred Skill guidance).
Credentials come from the environment (``TELEGRAM_BOT_TOKEN`` /
``TELEGRAM_CHAT_ID``) and never enter a profile, a CompositionSnapshot or a
receipt; missing credentials are a loud composition error, so a profile
fails to resolve instead of running half-configured.

Host does only transport and path validation; the Agent owns message content
and whether a material update warrants a send.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .client import TelegramClient
from .toolset import make_toolset


def _resolve_skill_dir() -> Path | None:
    """The bundled ``skills/`` library root (harness Skills contract).

    Harness Skills consumes library roots whose immediate children are skill
    packages (``<library>/<package>/SKILL.md``); passing a package directory
    itself fails during agent build. Editable and wheel layouts alike: the
    distribution root is ``parent.parent`` and the library is ``skills/``.
    """
    root = Path(__file__).resolve().parent.parent
    skills = root / "skills"
    return skills if (skills / "telegram-reporting" / "SKILL.md").is_file() else None


def create_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    del config  # no non-secret config: target chat is a fixed environment fact
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise CompositionError(
            "telegram plugin credentials missing: set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_CHAT_ID (local environment only, never in a profile)"
        )
    client = TelegramClient(bot_token=bot_token, chat_id=chat_id)
    skill_dir = _resolve_skill_dir()
    return PluginBundle(
        toolsets=[make_toolset(client, workspace_root=env.workspace_root)],
        skill_dirs=([skill_dir] if skill_dir is not None else []),
    )
