# ZUAEF Feishu Surface Spec Pack v0.1

Date baseline: 2026-09-06

Target:
- Existing `zuaef-agent` runtime already deployed on Orange Pi 5 / OPi5.
- Add a **generic Feishu group/DM Surface**.
- Quant is **not** a Feishu bot product and **not** implemented inside the adapter.
- `quant-decision` is only one profile routed by the existing zuaef-agent runtime.
- For risk containment, `quant-decision` is **group-chat only** in v0.1.

Primary architecture:

```text
Feishu
  ↓
Feishu Surface / Gateway
  ↓
zuaef-agent runtime
  ↓
Profile Router
  ├── general
  ├── quant-decision
  ├── research
  ├── coding
  ├── writing
  └── ...
```

Hard boundary:

```text
FeishuAdapter knows:
- Feishu transport
- user/group identity
- group/DM admission
- chat/thread identity
- inbound message normalization
- outbound text/document/card
- callback normalization
- session handoff

FeishuAdapter does NOT know:
- stocks
- symbols
- BUY / WATCH / HOLD
- T+1 / T+3 / T+5
- PIT
- positions
- market data
- Quant card semantics
- Quant workflow
```

The package is written to be handed directly to Codex on the OPi5 checkout.

## Read order

1. `00_DECISION_AND_BOUNDARIES.md`
2. `01_PRD.md`
3. `02_ARCHITECTURE.md`
4. `03_RUNTIME_AND_SESSION_CONTRACT.md`
5. `04_FEISHU_SETUP_RUNBOOK.md`
6. `05_SECURITY_AND_RISK.md`
7. `06_IMPLEMENTATION_TASKS.md`
8. `07_ACCEPTANCE_TESTS.md`
9. `08_OPI5_DEPLOYMENT.md`
10. `09_CODEX_MASTER_PROMPT.md`
11. `10_UPSTREAM_SOURCES.md`

The `references/` directory contains concise implementation snapshots of the latest
standalone Feishu/Lark Channel SDK documentation needed for this delivery.

## Upstream baseline

Use:

```text
lark-channel-sdk == 1.4.0
release date: 2026-08-31
import: from lark_channel import FeishuChannel
```

Do not start a new integration on `lark_oapi.channel.FeishuChannel`.
The standalone Channel SDK is the current bot/channel integration package.

The existing `lark-oapi` SDK may remain installed only if some separate zuaef-agent
feature needs the broader Feishu OpenAPI surface.

## Delivery definition

This work is complete only when:

1. One Feishu Bot reaches the existing zuaef-agent runtime.
2. At least two non-Quant profiles work through the same Bot.
3. `quant-decision` works only from an allowed Feishu group.
4. `/quant` in a DM is rejected by runtime profile policy.
5. Chat/thread profile bindings survive normal runtime operation.
6. The adapter contains no Quant business logic.
7. A duplicate Feishu event cannot produce duplicate agent execution.
8. Bot-originated messages are not recursively processed.
9. OPi5 service recovers after reboot and reconnect.
10. Existing Telegram/runtime/Quant behavior has no regression.
