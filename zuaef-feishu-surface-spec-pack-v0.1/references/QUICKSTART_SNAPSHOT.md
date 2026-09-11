# Reference Snapshot — Channel Quickstart

## Install

```bash
pip install lark-channel-sdk
```

For this repo use uv and pin `==1.4.0`.

## Developer console checklist

Current SDK quickstart states:
- create a bot application;
- enable event subscriptions;
- enable WebSocket event subscription channel;
- subscribe to receive-message events;
- grant send/receive message scopes such as:
  - `im:message`
  - `im:message:send_as_bot`
- reinstall the app after scope changes.

## Minimal lifecycle pattern

```python
channel = FeishuChannel(
    app_id=...,
    app_secret=...,
)

channel.on("message", on_message)
await channel.connect()
```

`connect()` keeps the WebSocket transport running.

Graceful shutdown:
```python
await channel.disconnect()
```

## Reply

```python
await channel.send(
    msg.chat_id,
    {"markdown": "..."},
    {"reply_to": msg.message_id},
)
```

## Webhook note

The SDK also supports webhook mode via `handle_webhook_request`, but it does not
ship a public HTTP server.

This Spec deliberately selects WebSocket for OPi5 v0.1.
