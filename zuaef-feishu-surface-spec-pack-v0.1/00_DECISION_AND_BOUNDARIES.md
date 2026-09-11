# 00 — Decision and Architecture Boundaries

## 1. Product decision

Do **not** build a "Quant Feishu bot".

Build:

> A generic Feishu Surface for zuaef-agent.

Quant is only:

```text
profile = "quant-decision"
```

The same Bot must be usable for research, coding, writing, general work, and future
profiles without touching Feishu transport code.

## 2. Why this boundary matters

A Surface and a Profile are orthogonal dimensions.

```text
Surface = where a message enters/leaves
Profile = which agent composition handles the request
```

Examples:

```text
Feishu / Telegram / Web
               ×
general / research / coding / writing / quant-decision
```

Any design that creates `FeishuQuantBot`, `QuantFeishuGateway`,
`send_quant_card()`, `parse_stock_command()`, or equivalent is rejected.

## 3. Risk containment rule

For v0.1:

```text
quant-decision:
  allowed_chat_types:
    - group
```

It is forbidden in Feishu P2P/DM.

A DM request such as:

```text
/quant
今天盯什么？
```

must fail at the **Profile Router / profile-access-policy layer**, not in the
transport adapter.

Expected response:

```text
quant-decision is enabled only in approved Feishu groups.
```

The exact user-facing wording may follow the existing runtime style.

## 4. Group examples

```text
Feishu group: Quant Lab
  chat binding → quant-decision

Feishu group: Research
  chat binding → research

Feishu DM
  default → general
```

One Bot, one runtime, multiple profiles.

## 5. Command ownership

Aliases are router configuration, not Feishu code.

Correct:

```text
ProfileRouter aliases:
  /quant    -> quant-decision
  /research -> research
  /coding   -> coding
  /writing  -> writing
```

Wrong:

```python
# FeishuAdapter
if text.startswith("/quant"):
    run_quant()
```

FeishuAdapter should forward normalized text to the generic runtime/router.

## 6. No duplicated agent core

The OPi5 already has a zuaef-agent runtime.

This task must:
- reuse it;
- reuse its profile composition;
- reuse its session/binding store if one exists;
- reuse its approval semantics;
- reuse its receipts/observability;
- reuse its external-effect policy.

Do not create a second agent loop inside a Feishu package.

## 7. Existing runtime wins

The public GitHub branch may not reflect every Gateway/Surface component currently
deployed on OPi5.

Therefore implementation begins with a **local runtime seam audit**.

Codex must first locate, in the actual OPi5 checkout:

```text
SurfaceAdapter
SessionBinding
ProfileRouter
gateway host / runtime host
approval transport contract
receipt/event store
current systemd unit(s)
```

If names differ, use the actual implementation. Do not invent parallel abstractions
just to satisfy this document.
