"""Operator notifier — host/operator-facing mechanical notification entry point.

Usage:

    python -m zuaef_telegram.notify <message>

This path is deliberately NOT model-visible: it performs no semantic
interpretation, and its authorization is the operator's own decision to
install the notifier with fixed local credentials (TELEGRAM_BOT_TOKEN /
TELEGRAM_CHAT_ID). It reuses the same TelegramClient transport as the
model tool ``report_to_telegram``, but targets only the configured fixed
chat and is intended for already-authorized mechanical operator
notifications (e.g. "Supervisor report published").

It is the unattended attention path: no PydanticAI approval applies because
no Agent semantic decision is being made — the host already decided to send
when it invokes this module.
"""

from __future__ import annotations

import json
import os
import sys

from .client import TelegramClient, TelegramError


def notify_operator(message: str) -> dict:
    """Send one mechanical notification to TELEGRAM_CHAT_ID.

    Raises TelegramError on missing credentials or a failed send; the caller
    (e.g. the Supervisor loop) treats this as best-effort and must never let
    a notification failure invalidate the already-completed work it reports.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        raise TelegramError(
            "telegram notifier not configured: set TELEGRAM_BOT_TOKEN and "
            "TELEGRAM_CHAT_ID (local environment only)"
        )
    return TelegramClient(bot_token=bot_token, chat_id=chat_id).send_message(message)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    message = " ".join(args) or "ZUAEF operator notification."
    try:
        result = notify_operator(message)
    except TelegramError as exc:
        print(f"notify failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
