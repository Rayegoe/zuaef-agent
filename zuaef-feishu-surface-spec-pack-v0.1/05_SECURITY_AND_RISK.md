# 05 — Security and Risk Controls

## 1. Threat model

Primary v0.1 risks:
- an unauthorized group drives the agent;
- an unauthorized user drives the agent;
- bot output loops back into the bot;
- Feishu redelivery triggers duplicate runs/external effects;
- stale events execute after reconnect;
- a card callback is replayed;
- App Secret leaks into config/logs;
- a sensitive profile is activated in a DM;
- two workers process the same app concurrently;
- Feishu transport code accidentally accumulates Quant/business authority.

## 2. Surface policy

Use Channel SDK `PolicyConfig` where it matches the current version.

Target behavior:

```text
group_policy = allowlist
group_allowlist = configured chat IDs
require_mention = true

DM:
  allowlist or existing zuaef authenticated-user policy
```

Ignore:
- bot senders;
- app/system-originated messages unless explicitly needed.

## 3. SDK security mode

The standalone Channel SDK supports:

```text
compat
audit
strict
```

Rollout:
1. local/canary: `audit`;
2. validate normal WS behavior and event parsing;
3. production: `strict`.

`strict` is preferred after compatibility verification.

Because v0.1 uses WebSocket rather than webhook, webhook signature concerns are not
the primary ingress path, but strict mode still provides useful WebSocket/security
limits.

Suggested limits should be conservative and based on SDK defaults/current API;
do not invent values if the deployed SDK version exposes different names.

## 4. Dedup

Use SDK dedup first.

It has:
- pipeline-layer event/message dedup;
- safety-layer dispatch dedup.

Additionally make runtime dispatch idempotent using:
- Feishu message_id;
- event/callback identity where available.

Never rely on in-memory dedup alone to protect a high-impact external effect if the
existing zuaef runtime already has durable receipt/idempotency semantics.

## 5. One worker

One Feishu App -> one active gateway worker.

Do not horizontally run two workers against the same app in v0.1.

Reason:
the SDK's optional shared cache interface is best-effort for cross-process dedup,
not a strict atomic coordination boundary.

## 6. Sensitive profile gate

`quant-decision` restrictions live in Profile Router policy:

```text
surface: feishu
chat_type: group only
channel_id: explicit allowlist
```

DM denial is mandatory.

This policy is testable without Feishu transport.

## 7. External effects

Feishu is a Surface, not an approval bypass.

Any zuaef-agent external effect that normally requires approval must still require
approval when invoked through Feishu.

The Feishu approval card is merely a UI representation of the existing approval
object.

## 8. Callback authorization

On card actions:
- identify operator `open_id`;
- identify chat/message;
- verify the callback belongs to a live generic approval/action;
- verify actor is allowed by existing approval policy;
- make decision idempotent;
- reject old/completed request IDs;
- then update card.

Do not treat "button clicked" as sufficient authority.

## 9. Secret storage

Preferred:
- systemd `EnvironmentFile=` pointing to a mode-600 file outside git.

Example:

```text
~/.config/zuaef/feishu.env
```

Permissions:

```bash
chmod 600 ~/.config/zuaef/feishu.env
```

No secret values in journald.

## 10. No Quant coupling gate

CI/test must fail if the Feishu adapter package introduces obvious Quant business
tokens.

At minimum scan Feishu-specific source for:

```text
BUY
WATCH
HOLD
PIT
T+1
T+3
T+5
stock
ticker
position
market_data
quant rule
```

Allow occurrences only in architecture tests/comments that explicitly assert the
forbidden coupling; prefer an allowlist of test files.

The strongest test is behavioral:
- disable/remove `quant-decision`;
- Feishu `general/research/writing` still works unchanged.
