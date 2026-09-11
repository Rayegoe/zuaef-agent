# 01 — PRD: Generic Feishu Surface v0.1

## Objective

Give every eligible zuaef-agent profile a stable Feishu group/mobile interaction
surface while preserving the existing runtime as the sole agent execution core.

## User outcome

From one Feishu Bot:

```text
/profile research
分析 Qlib 在 ARM64 上的部署方案
```

and later:

```text
/profile writing
把刚才的研究结果整理成公众号草稿
```

In an approved Quant group:

```text
/quant
今天盯什么？
```

routes to:

```text
quant-decision
```

without Feishu code knowing anything about markets.

## In scope

### Inbound
- Feishu WebSocket long connection.
- Group message receive.
- P2P message receive.
- `@bot` mention stripping using SDK normalized `body_text`.
- user identity.
- group identity.
- thread/reply identity.
- message-id/event-id dedup.
- card action callback normalization.

### Generic outbound
- text / markdown.
- rich post if existing Surface contract needs it.
- file/document.
- image if already part of generic artifact delivery.
- generic interactive card.
- reply to message.
- reply in thread.
- update card.
- error/fallback text.

### Runtime handoff
- generic inbound envelope.
- profile router invocation.
- session binding.
- approval response transport.
- runtime result rendering.

### Operations
- OPi5 startup.
- reconnect.
- graceful shutdown.
- logs.
- health signal.
- credential loading.
- regression tests.

## Out of scope

- Quant business logic.
- market-data fetching.
- holdings.
- trade execution.
- stock-code parsing.
- stock-specific cards.
- PIT/timing rules.
- T+N logic.
- Feishu meeting agents.
- external/public webhook ingress for v0.1.
- multi-tenant Feishu SaaS.
- multiple simultaneous workers for one Feishu App.
- custom WebSocket implementation.
- custom tenant token refresh.
- rebuilding Channel SDK dedup/media/markdown facilities.

## Success metrics

Technical:
- one WebSocket connection remains stable through normal reconnect.
- duplicate inbound delivery causes one runtime execution.
- group thread context maps deterministically to one runtime session key.
- startup after reboot needs no manual operation.
- no new public inbound port is required.

Architecture:
- Feishu-specific code contains zero Quant business decisions.
- new profiles require router/profile config only, not Feishu code changes.
- Quant can be removed entirely without changing Feishu transport.

Business:
- approved Feishu group can use `quant-decision` as the first real acceptance profile.
- research/coding/writing prove that the Surface is genuinely generic.
