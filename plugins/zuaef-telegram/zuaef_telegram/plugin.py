"""``zuaef-telegram`` plugin factory.

The plugin exposes exactly one model-visible action — ``report_to_telegram``
— over the existing plugin composition ABI (one distribution, one Toolset,
optional deferred Skill guidance). Credentials come from the environment
(``TELEGRAM_BOT_TOKEN`` / ``TELEGRAM_CHAT_ID``) and never enter a profile, a
CompositionSnapshot or a receipt; missing credentials are a loud composition
error, so a profile fails to resolve instead of running half-configured.

Host does only transport; the Agent owns message content and whether a
material update warrants a send.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .client import TelegramClient
from .toolset import make_toolset


def _resolve_skill_dir() -> Path | None:
    """The bundled ``skill/`` directory (editable and wheel layout alike)."""
    skill = Path(__file__).resolve().parent.parent / "skill"
    return skill if skill.is_dir() else None


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
        toolsets=[make_toolset(client)],
        skill_dirs=([skill_dir] if skill_dir is not None else []),
    )
