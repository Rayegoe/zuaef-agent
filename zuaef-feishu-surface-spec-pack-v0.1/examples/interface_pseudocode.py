"""
Architecture pseudocode only.
Do not copy blindly; adapt to the real SurfaceAdapter/Runtime ABI on OPi5.
"""

from lark_channel import FeishuChannel


class FeishuSurface:
    def __init__(self, runtime, config):
        self.runtime = runtime
        self.config = config
        self.channel = FeishuChannel(
            app_id=config.app_id,
            app_secret=config.app_secret,
            # policy/safety/security objects omitted here intentionally:
            # construct them using the exact 1.4.0 API in the deployed env.
        )

        self.channel.on("message", self._on_message)
        self.channel.on("cardAction", self._on_card_action)
        self.channel.on("error", self._on_error)

    async def _on_message(self, msg):
        if msg.sender_is_bot:
            return

        envelope = {
            "surface": "feishu",
            "channel_id": msg.chat_id,
            "thread_id": normalize_thread_id(msg),
            "message_id": msg.message_id,
            "actor_id": msg.sender_id,
            "actor_name": msg.sender_name,
            "chat_type": msg.chat_type,
            "text": msg.body_text,
            "resources": msg.resources,
            "reply_to": msg.reply_to_message_id,
        }

        # Runtime owns:
        # - session binding
        # - profile routing
        # - profile access policy
        # - approval policy
        # - agent execution
        result = await self.runtime.handle_surface_message(envelope)
        await self._render_result(msg, result)

    async def _on_card_action(self, event):
        callback = normalize_generic_callback(event)
        result = await self.runtime.handle_surface_callback(callback)
        await self._render_callback_result(event, result)

    async def _render_result(self, inbound, result):
        # Generic rendering only. Never inspect "quant-decision".
        if result.kind == "text":
            await self.channel.send(
                inbound.chat_id,
                {"markdown": result.text},
                {"reply_to": inbound.message_id},
            )
        elif result.kind == "artifact":
            await self.channel.send(
                inbound.chat_id,
                {"file": {"source": result.path, "file_name": result.name}},
                {"reply_to": inbound.message_id},
            )
        elif result.kind == "approval":
            await self.channel.send(
                inbound.chat_id,
                {"card": render_generic_approval_card(result)},
                {"reply_to": inbound.message_id},
            )
