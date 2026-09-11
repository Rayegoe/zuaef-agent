# 03 — Runtime, Profile Routing, and Session Contract

## 1. Binding model

Extend/reuse the existing `SessionBinding` concept:

```text
SessionBinding
├── surface    = "feishu"
├── channel_id = chat_id
├── thread_id  = thread_id / root_message_id / null
└── profile    = profile_id
```

Do not create a Feishu-only session database if the runtime already has a generic
binding store.

## 2. Binding precedence

Recommended effective-profile lookup:

```text
1. explicit thread binding
2. explicit chat binding
3. configured group default
4. surface default
5. general
```

Example:

```text
Quant Lab group:
  chat binding = quant-decision

one thread in Quant Lab:
  thread binding = research
```

This is a runtime/router capability. The adapter simply supplies stable
`channel_id` and `thread_id`.

## 3. Thread identity

Preferred normalized identity:

```text
channel_id = Feishu chat_id

thread_id:
  if Feishu provides a thread/topic id -> use it
  else if the message is inside a reply thread -> use root_message_id
  else -> null
```

Do not use a new message_id as the session key for each turn.

## 4. Profile commands

Implement in Profile Router, not FeishuAdapter.

Minimum generic commands:

```text
/profile
/profile <profile-id>
```

Optional aliases:

```text
/quant
/research
/coding
/writing
```

Aliases are data/configuration:

```yaml
profile_aliases:
  quant: quant-decision
  research: research
  coding: coding
  writing: writing
```

## 5. Quant risk policy

Runtime profile-access policy:

```yaml
profile_access:
  quant-decision:
    allowed_surfaces:
      - feishu
    allowed_chat_types:
      - group
    allowed_channel_ids:
      - "<approved Quant group chat_id>"
```

This is the critical guard.

DM:

```text
surface=feishu
chat_type=p2p
requested_profile=quant-decision
```

must be denied before agent execution.

The adapter remains generic.

## 6. Feishu admission vs profile admission

Two separate gates:

### Surface admission
Answers:
- Is this Feishu group permitted to use the Bot at all?
- Is this Feishu user permitted?
- Must the Bot be @mentioned?

Owned by:
- Feishu Channel `PolicyConfig`;
- generic Surface authorization config.

### Profile admission
Answers:
- May this session use `quant-decision`?
- May this group use a sensitive profile?

Owned by:
- runtime Profile Router / profile-access policy.

Do not collapse the two.

## 7. Default policies

Suggested v0.1:

```text
Feishu group:
  allowlist only
  require @mention = true

Feishu DM:
  allowlist users only, or runtime's existing authenticated-user set
  default profile = general

quant-decision:
  group only
  explicit approved-channel allowlist
```

## 8. Session persistence

Use existing runtime persistence.

Acceptance requires:
- switching a chat to `research`;
- restarting only the Feishu surface/runtime as normally deployed;
- the binding remains according to the existing session persistence contract.

If existing zuaef-agent sessions are intentionally ephemeral, preserve that behavior
and document it; do not silently invent a second persistence model.
