# 02 — Architecture

## 1. Target data flow

```text
Feishu Cloud
   │ WebSocket events
   ▼
FeishuChannel (lark-channel-sdk)
   │ normalized InboundMessage/CardActionEvent
   ▼
FeishuAdapter
   │ generic SurfaceEnvelope
   ▼
Gateway Host
   │
   ├── admission / identity
   ├── session lookup
   └── runtime dispatch
           ▼
      Profile Router
           │
           ├── general
           ├── research
           ├── coding
           ├── writing
           └── quant-decision
                    │
                    ▼
              existing agent core
                    │
                    ▼
              generic RunResult
                    │
                    ▼
              Feishu renderer
                    │
                    ▼
              FeishuChannel.send/update_card
```

## 2. SDK choice

Pin:

```toml
lark-channel-sdk==1.4.0
```

Use:

```python
from lark_channel import (
    FeishuChannel,
    PolicyConfig,
    SafetyConfig,
    SecurityConfig,
)
```

The standalone SDK already provides:
- WebSocket transport;
- event normalization;
- policy controls;
- two-layer dedup;
- outbound message sending;
- retry/chunking;
- media upload/download;
- card callbacks;
- streaming;
- thread reply options;
- card update helpers.

Do not duplicate these.

## 3. Transport strategy

OPi5 v0.1 uses **WebSocket long connection**, not a public webhook.

Reasons:
- no public IP required;
- no reverse proxy required;
- no TLS certificate required for inbound callbacks;
- NAT/home/office network friendly;
- simplest deployment on a small always-on board;
- official Channel SDK defaults to `transport="ws"`.

If the existing Surface interface exposes `poll_once`, preserve the host ABI by
placing WebSocket events into an internal async queue.

Example conceptual bridge:

```python
async def on_message(msg):
    await inbound_queue.put(normalize(msg))

async def poll_once(timeout):
    return await wait_for(inbound_queue.get(), timeout)
```

This is **not** HTTP polling and **not** Feishu API polling.

If the current runtime can natively consume pushed async events, do not add
`poll_once` merely because this spec mentions it.

## 4. Adapter interface

Use the existing SurfaceAdapter ABI where available.

Conceptual minimum:

```python
class FeishuAdapter:
    async def start(self): ...
    async def stop(self): ...
    async def poll_once(self): ...        # only if existing ABI requires
    async def send_text(self, target, text, *, reply_to=None): ...
    async def send_document(self, target, source, filename=None): ...
    async def send_card(self, target, card, *, reply_to=None): ...
    async def update_card(self, message_id, card): ...
    async def send_approval(self, target, approval): ...
    async def answer_callback(self, callback): ...
```

Do not force this exact class if the deployed runtime uses another ABI.

## 5. Generic inbound envelope

Map Feishu fields to the existing runtime envelope. If the runtime lacks equivalent
fields, add only the smallest general-purpose extension.

Conceptual form:

```text
SurfaceEnvelope
  surface       = "feishu"
  channel_id    = chat_id
  thread_id     = thread_id or root_message_id or null
  message_id    = Feishu message_id
  actor_id      = sender.open_id
  actor_name    = sender_name
  chat_type     = group | p2p | topic
  text          = body_text
  raw_type      = original Feishu msg type
  resources     = generic attachments/resources
  reply_to      = parent message id if present
```

`body_text` is preferred for command routing because the Channel SDK removes the
current bot's own @-mention from it.

## 6. Outbound normalization

The runtime returns generic renderable results.

Renderer policy:

```text
short text       -> markdown/text
long structured  -> post or markdown chunks
artifact         -> file
approval         -> generic interactive card
error            -> text
```

No renderer branch may inspect `profile == "quant-decision"`.

## 7. Card callbacks

Card buttons carry generic action metadata, for example:

```json
{
  "action": "approval_decision",
  "decision": "approve",
  "request_id": "..."
}
```

The Feishu layer maps `CardActionEvent` to the runtime's generic approval callback.

The approval engine decides what approval means.

Feishu only:
- receives the click;
- authenticates the actor;
- extracts generic action value;
- hands it to runtime;
- updates/acknowledges the card.

## 8. Single-worker rule

Run one active Feishu Surface worker per Feishu App in v0.1.

The Channel SDK has two dedup layers, but its shared-cache interface is not a strict
cross-process atomic coordination boundary.

Therefore:
- one app -> one OPi5 gateway worker;
- handlers remain idempotent by message/event id;
- do not run two competing systemd instances.
