# Reference Snapshot — lark-channel-sdk 1.4.0

This is a concise implementation snapshot for the Spec Pack, not a replacement for
the upstream source.

## Main entry point

```python
from lark_channel import FeishuChannel
```

`FeishuChannel` combines:
- WebSocket/webhook event transport;
- inbound normalization;
- policy;
- safety/dedup;
- outbound send;
- media;
- streaming;
- card helpers.

## Constructor areas

Current reference exposes configuration areas including:
- `app_id`, `app_secret`;
- `domain`;
- `transport` (`ws` default, or `webhook`);
- `encrypt_key`, `verification_token`;
- `policy=PolicyConfig(...)`;
- `safety=SafetyConfig(...)`;
- `inbound=InboundConfig(...)`;
- `outbound=OutboundConfig(...)`;
- `security=SecurityConfig(...)`;
- custom dedup/cache/token stores.

## Lifecycle

Available patterns include:
- `await channel.connect()`;
- `await channel.connect_until_ready(timeout=...)`;
- `await channel.start_background(...)`;
- `await channel.disconnect()`;
- readiness waiting.

## Events

Important v0.1 events:
```text
message
cardAction
error
reconnecting
reconnected
```

Other SDK events exist but are not required for this Spec.

## Inbound message fields

Useful normalized fields:
- `message_id` / `id`;
- `create_time`;
- `chat_id`;
- `chat_type`;
- sender identity/open_id;
- sender name;
- sender type / bot flag;
- mentions;
- reply parent;
- content;
- `content_text`;
- `safe_content_text`;
- `body_text`;
- resources;
- raw content type;
- raw event.

Use `body_text` for command parsing.

## Outbound

`channel.send(to, message, opts)` supports:
- text;
- markdown;
- post;
- card;
- image;
- file;
- audio;
- video;
- share chat/user;
- sticker.

Important opts:
- `reply_to`;
- `reply_in_thread`;
- `receive_id_type`;
- idempotency/uuid option where applicable.

## Helpers

Useful generic helpers:
- `update_card`;
- `edit_message`;
- `recall_message`;
- add/remove reaction;
- download resources;
- chat info/mode;
- resource cache helpers.

## Streaming

SDK supports:
- markdown streaming;
- card streaming.

Streaming is not required for v0.1 closure unless the existing runtime already
exposes streamed assistant output.
