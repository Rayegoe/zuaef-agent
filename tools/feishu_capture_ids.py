#!/usr/bin/env python3
"""One-off operator tool: bootstrap the Feishu gateway allowlists.

Connects to Feishu over WebSocket with the SDK directly and PRINTS the
``open_id`` / ``chat_id`` of real inbound events, so the operator can fill
``FEISHU_USER_ALLOWLIST`` / ``FEISHU_GROUP_ALLOWLIST`` in ``feishu.env``.

The gateway itself stays fail-closed (it refuses to start with an empty
allowlist); this tool never runs the agent, never sends messages and never
touches gateway state. Stop the gateway unit before capturing: one app
should have only one active event consumer at a time.

Usage (on the runtime node, with the credential file present):

    set -a; . ~/.config/zuaef/feishu.env; set +a
    uv run python tools/feishu_capture_ids.py --seconds 90

Then send a message to the bot (@mention in the test group, and one DM).
Copy the printed ``ou_...`` / ``oc_...`` ids into ``feishu.env``.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from lark_channel import FeishuChannel


async def main(seconds: int) -> None:
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise SystemExit(
            "FEISHU_APP_ID / FEISHU_APP_SECRET must be in the environment "
            "(source the operator env file first)"
        )
    channel = FeishuChannel(app_id=app_id, app_secret=app_secret, transport="ws")
    seen: dict[tuple[str, str, str], int] = {}

    def on_message(msg) -> None:
        key = (msg.sender_id or "?", msg.chat_id or "?", msg.chat_type or "?")
        seen[key] = seen.get(key, 0) + 1
        preview = (msg.body_text or "")[:40]
        print(
            f"event: sender_open_id={key[0]} chat_id={key[1]} "
            f"chat_type={key[2]} mentioned_bot={msg.mentioned_bot} "
            f"text={preview!r}",
            flush=True,
        )

    def on_card_action(event) -> None:
        print(
            f"card:  operator_open_id={event.operator.open_id} "
            f"chat_id={event.chat_id}",
            flush=True,
        )

    channel.on("message", on_message)
    channel.on("cardAction", on_card_action)

    await channel.connect_until_ready(timeout=30)
    print(f"connected; capturing inbound events for {seconds}s ...", flush=True)
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        pass
    await channel.disconnect()

    print("=== unique identities seen (copy into feishu.env) ===", flush=True)
    if not seen:
        print("(none — send @Bot a message in the test group and one DM, then rerun)")
    for (sender, chat, chat_type), count in sorted(seen.items()):
        print(f"ou={sender}  oc={chat}  type={chat_type}  events={count}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--seconds", type=int, default=90, help="capture window length"
    )
    try:
        asyncio.run(main(parser.parse_args().seconds))
    except KeyboardInterrupt:
        print("\ncapture interrupted", flush=True)
