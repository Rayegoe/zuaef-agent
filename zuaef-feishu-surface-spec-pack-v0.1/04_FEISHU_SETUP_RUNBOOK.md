# 04 — Feishu Developer Console Setup Runbook

This file is the operator checklist for creating/configuring the Feishu app.

## 1. Create an internal/custom app

In Feishu Open Platform:
1. create an enterprise/internal custom application;
2. enable **Bot** capability;
3. obtain:
   - App ID
   - App Secret

Never commit App Secret.

## 2. Event transport

Choose:
- event subscription;
- **WebSocket / long connection** mode.

v0.1 intentionally does not require a public webhook endpoint.

The SDK will obtain the server WebSocket endpoint from Feishu and keep the
connection alive.

## 3. Receive message event

Subscribe to the Feishu message receive event used by the SDK, commonly represented
as:

```text
im.message.receive_v1
```

The exact console label can change; use the console's "receive message" event.

## 4. Minimal message permissions

At minimum the app must have the message receive/send permissions required by the
console and Channel SDK, including the current SDK quickstart guidance:

```text
im:message
im:message:send_as_bot
```

If the console decomposes receive permissions into finer scopes, grant only the
scope matching the intended group/P2P receive behavior.

Do not grant broad tenant permissions "just in case".

After changing permissions:
- create/publish a new app version if Feishu requires it;
- reinstall/re-authorize the app into the tenant.

## 5. Add Bot to groups

Add the Bot to:
- approved generic zuaef-agent groups;
- the dedicated Quant Lab group used for acceptance.

The adapter's group allowlist must use stable `chat_id`, not display name.

## 6. Mention policy

For group v0.1:

```text
require_mention = true
```

This prevents every group message from becoming an agent run.

The Channel SDK provides `body_text`, which removes the current bot's own mention
for command parsing.

## 7. Bot-to-bot messages

Default v0.1:
- ignore bot/app senders;
- do not enable bot-to-bot collaboration.

If bot-to-bot is added later, the SDK documentation notes a distinct permission for
receiving another bot's @mention:

```text
im:message.group_at_msg.include_bot:readonly
```

This is not required for the human-to-agent v0.1.

## 8. Interactive cards

Enable/configure interactive message-card callback capability as required by the
Feishu console for the app.

The standalone Channel SDK exposes:

```python
channel.on("cardAction", handler)
```

and generic helpers such as:

```python
await channel.update_card(message_id, card)
```

Use cards only for generic runtime interactions such as approvals/actions.

Do not encode Quant card semantics in the adapter.

## 9. Credentials on OPi5

Recommended environment names:

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_GROUP_ALLOWLIST
FEISHU_USER_ALLOWLIST
```

The adapter may internally pass them to `FeishuChannel(app_id=..., app_secret=...)`.

Do not put secrets in:
- profile files;
- CompositionSnapshot;
- run receipts;
- git;
- generated dashboard;
- logs.

## 10. First connection test

Before agent integration, run a transport-only canary:
1. connect;
2. receive one @mention from an allowed test group;
3. log only normalized IDs/type, not secrets;
4. send `feishu surface canary ok`;
5. terminate cleanly.

Then integrate into runtime.

## 11. Common setup failures

### No inbound messages
Check:
- app version is published/installed;
- bot capability enabled;
- receive-message event subscribed;
- receive permission granted;
- bot is actually in the group;
- group is in allowlist;
- `require_mention` and @mention behavior.

### Can receive, cannot send
Check:
- `im:message:send_as_bot`;
- tenant install/re-authorization after permission changes.

### Card click never arrives
Check:
- card callback/event configuration;
- app version;
- Channel handler registration;
- callback actor/group allowlist.

### Works before restart, fails after
Check:
- environment file available to systemd;
- working directory;
- `uv` environment;
- network/DNS;
- service restart policy.
