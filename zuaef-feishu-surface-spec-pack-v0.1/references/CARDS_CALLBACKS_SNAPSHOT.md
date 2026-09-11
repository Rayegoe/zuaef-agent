# Reference Snapshot — Cards and Callbacks

## Event

Register generic card actions:

```python
channel.on("cardAction", handler)
```

The normalized action exposes action metadata/value plus operator/context fields.

## Adapter role

The Feishu adapter converts the card action into the runtime's generic callback or
approval-decision envelope.

It does not decide the business meaning.

## Outbound card

```python
await channel.send(
    chat_id,
    {"card": card_json},
    {"reply_to": message_id},
)
```

## Update card

```python
await channel.update_card(message_id, new_card_json)
```

## v0.1 approval card

Generic fields only:
- request/action id;
- title;
- summary;
- approve;
- reject;
- final status.

No stock/Quant fields belong in the adapter's card renderer.
