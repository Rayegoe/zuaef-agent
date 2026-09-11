# 09 — Codex Master Prompt

You are implementing **ZUAEF Feishu Surface v0.1** on the current Orange Pi 5
checkout.

The goal is NOT to build a Quant bot.

The goal is:

```text
Feishu Gateway
    ↓
existing zuaef-agent runtime
    ↓
existing/general Profile Router
    ├── quant-decision
    ├── research
    ├── coding
    ├── writing
    └── ...
```

## Non-negotiable architecture

1. Feishu is a generic Surface.
2. `quant-decision` is only a profile.
3. Quant is group-chat only in v0.1.
4. A Feishu DM may not activate `quant-decision`.
5. Feishu transport code may not contain Quant business logic.
6. Reuse current runtime, profile, session, approval, receipt and gateway seams.
7. Do not create a second agent core.
8. Do not duplicate capabilities already provided by `lark-channel-sdk`.
9. Use the standalone `lark-channel-sdk==1.4.0`, not a new integration on
   `lark_oapi.channel.FeishuChannel`.
10. Prefer WebSocket long connection on OPi5; no public webhook for v0.1.

## First action: inspect local truth

Before editing anything:

```bash
pwd
whoami
hostname
git status --short --branch
git rev-parse HEAD
git log -1 --oneline --decorate
systemctl --user --type=service --all | grep -i zuaef || true
systemctl --user --type=timer --all | grep -i zuaef || true
rg -n "SurfaceAdapter|SessionBinding|ProfileRouter|profile.*route|gateway|approval|pending_cursor|telegram" .
```

Then identify:
- actual Surface/Gateway ABI;
- session binding store;
- profile router;
- approval callback path;
- service unit;
- current plugin/package conventions.

The deployed checkout is authoritative. If it differs from this spec's example names,
adapt the plan to the actual code rather than creating parallel abstractions.

## Upstream SDK contract

Use:

```python
from lark_channel import FeishuChannel
```

The SDK already owns:
- WS transport;
- normalization;
- dedup;
- outbound send;
- message chunking/retry;
- media;
- card callbacks;
- streaming;
- card update;
- reply/thread options.

Only build the thin zuaef-agent adapter.

## Inbound mapping

Map Feishu to the generic runtime:

```text
surface=feishu
channel_id=chat_id
thread_id=thread/topic/root message identity or null
message_id=message_id
actor_id=sender.open_id
actor_name=sender_name
chat_type=group/p2p/topic
text=body_text
resources=generic resources
```

Prefer `body_text` for commands because it removes the current bot's @mention.

## Session/profile rules

Profile resolution:

```text
thread binding
  > chat binding
  > configured group default
  > surface default/general
```

Aliases belong in Profile Router:

```text
/quant -> quant-decision
/research -> research
/coding -> coding
/writing -> writing
```

The FeishuAdapter must not contain `/quant` business handling.

Mandatory profile access policy:

```text
quant-decision:
  allowed_chat_types: [group]
  allowed_channel_ids: [approved Quant Lab chat ids]
```

DM activation is rejected before agent execution.

## Feishu surface admission

Use allowlists and mention policy:
- approved group IDs;
- approved users;
- group requires @mention;
- ignore bot/app senders.

## Generic outbound

Implement/reuse:
- send_text / markdown;
- send_document;
- generic card;
- send_approval;
- card callback;
- thread reply;
- update card.

Do not implement:
- stock card;
- trading signal card;
- position card;
- market-specific renderer.

## Idempotency

One inbound event -> one runtime run.

One approval request -> one final decision.

Run one active Feishu worker per app.

Use the SDK dedup and the existing zuaef-agent durable idempotency/receipt mechanism
where external effects are concerned.

## Operations

Integrate Feishu into the existing OPi5 runtime/gateway service if possible.

Only add a dedicated surface service if the actual runtime architecture requires it.

Credentials:
- environment only;
- mode-600 EnvironmentFile;
- never profile/config snapshots/receipts/git.

## Implementation method

Work in phases:
1. baseline and architecture evidence;
2. dependency/config;
3. transport canary;
4. inbound normalization;
5. runtime/session/profile routing;
6. generic outbound;
7. approvals/callback;
8. OPi5 systemd;
9. tests;
10. live acceptance.

After each phase, run the narrowest meaningful tests.

Do not spend time on unrelated refactors.

## Required live acceptance

Using the same Feishu Bot:

1. `research` works in an approved group.
2. another non-Quant profile works.
3. Quant Lab can switch to `quant-decision`.
4. Feishu DM cannot switch to `quant-decision`.
5. a non-Quant group not in Quant allowlist cannot activate Quant.
6. duplicate inbound event does not double-run.
7. bot message does not loop.
8. generic approval card is idempotent.
9. service restart reconnects.
10. existing tests pass.

## Final report

Return:
- baseline;
- architecture seam reused;
- files changed;
- dependency changes;
- configuration keys;
- tests run and exact results;
- live Feishu acceptance evidence;
- systemd status;
- known limitations;
- git diff/stat/status.

Do not claim completion if only an echo bot works.
Completion means the Feishu Surface is integrated into the real zuaef-agent runtime
and multi-profile routing is proven.
