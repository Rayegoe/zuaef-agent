"""Operational canary: prove the plugin's own transport can send one message.

Usage (from the repo root, with local creds loaded):

    set -a && . ./.env && set +a
    TELEGRAM_CHAT_ID=<chat id> uv run python -m zuaef_telegram.canary "Delivery test"

Reads only ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_CHAT_ID`` from the
environment, prints a bounded delivery fact and exits 0 on success; exits 1
with a redacted error on failure. Never prints the bot token.
"""

from __future__ import annotations

import json
import os
import sys

from .client import TelegramClient, TelegramError


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        print(
            "canary failed: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            "(local environment only)",
            file=sys.stderr,
        )
        return 1
    message = " ".join(args) or "ZUAEF telegram canary."
    try:
        result = TelegramClient(bot_token=bot_token, chat_id=chat_id).send_message(
            message
        )
    except TelegramError as exc:
        print(f"canary failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
