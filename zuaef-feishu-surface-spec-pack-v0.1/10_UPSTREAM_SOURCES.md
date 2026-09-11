# 10 — Upstream Source Manifest

Verified baseline date: 2026-09-06.

## Current standalone Channel SDK

Package:
- `lark-channel-sdk`
- latest verified PyPI release: `1.4.0`
- release date: 2026-08-31
- Python requirement: >=3.8
- project status on PyPI: Production/Stable
- pure Python wheel available

PyPI:
https://pypi.org/project/lark-channel-sdk/

Source:
https://github.com/larksuite/channel-sdk-python

Chinese README:
https://github.com/larksuite/channel-sdk-python/blob/main/README.zh.md

## Required SDK docs

Quickstart:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/quickstart.md

Channel reference:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/reference.md

Security:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/security.md

Dedup architecture:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/dedup-architecture.md

Markdown:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/markdown.md

Webhook adapter:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/webhook-server.md

CardKit streaming:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/cardkit-streaming.md

Migration from `lark_oapi.channel`:
https://github.com/larksuite/channel-sdk-python/blob/main/docs/migration-from-lark-oapi.md

## Feishu Open Platform

Open Platform:
https://open.feishu.cn/

Server-side documentation root:
https://open.feishu.cn/document/server-docs

Feishu Cards / interaction documentation can move within the Open Platform
information architecture. Use the developer console's current links for:
- enabling Bot capability;
- event subscription;
- WebSocket long connection;
- receive-message event;
- message send/receive permissions;
- card interaction callbacks.

## Key facts used by this Spec

From current Channel SDK Quickstart/reference:
- create a bot application;
- enable event subscriptions;
- WebSocket is supported and is the default Channel transport;
- subscribe to receive-message events;
- message send/receive scopes include `im:message` and
  `im:message:send_as_bot`;
- reinstall/re-authorize after permission changes;
- `FeishuChannel` handles normalized inbound messages and outbound send;
- `PolicyConfig` provides group/DM/mention admission behavior;
- `SafetyConfig` provides dedup-related safety controls;
- `SecurityConfig` provides compat/audit/strict modes;
- `body_text` removes the current bot's own mention;
- `reply_to` and `reply_in_thread` are supported outbound options;
- card actions are emitted as `cardAction`;
- `update_card` is supported;
- media/file sending is supported.

From current dedup documentation:
- pipeline and safety dedup are separate layers;
- multi-worker shared-cache dedup is not a strict atomic coordination boundary;
- single-worker routing and idempotent handlers are the safe v0.1 pattern.

## Version policy for this delivery

Pin `1.4.0`.

Do not use a floating unbounded dependency in the first production Feishu deployment.

After v0.1 is stable, upgrades may be handled as explicit dependency bumps with:
- upstream changelog/source review;
- unit/integration suite;
- live group canary;
- rollback.
