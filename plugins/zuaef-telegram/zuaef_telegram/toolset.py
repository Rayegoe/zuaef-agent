"""Telegram reporting toolset — one model-visible action.

``report_to_telegram`` is an external write (a message leaves the host for a
third-party service and a human's chat), so it carries the same native
PydanticAI approval contract as the WordPress write tools: the Agent owns
*what* is worth reporting; the human approves the external send.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.effects import EffectClass, requires_approval
from zuaef_agent.models import CoreDeps

from .client import TelegramClient

TOOLSET_INSTRUCTIONS = """\
Send a concise human-facing report to the configured Telegram chat.

- report_to_telegram is an external write (third-party service + a human's
  chat) and therefore requires explicit human approval before execution.
- Report material milestones, completion, blocking failures, or when a human
  decision is required. Keep messages concise and outcome-oriented.
- Do not report routine internal reasoning or every tool action.
- Never send secrets, credentials, or private source material unless
  explicitly authorized.
"""


def make_toolset(client: TelegramClient) -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=TOOLSET_INSTRUCTIONS
    )

    @toolset.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def report_to_telegram(message: str) -> str:
        """Send one concise report message to the configured Telegram chat (external write)."""
        return _json(client.send_message(message))

    return toolset


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
