# 07 — Acceptance Tests

## A. Architecture gates

### A1 Generic Surface
Pass only if one Feishu Bot can route to at least:
- `research`;
- one of `general` / `writing` / `coding`;
- `quant-decision` in approved group.

### A2 No Quant transport coupling
Search Feishu adapter source.

Fail if it contains executable logic for:
- stock symbols;
- market timing;
- holdings;
- BUY/WATCH/HOLD;
- PIT;
- T+N;
- market-data queries.

### A3 Quant removal test
Temporarily make `quant-decision` unavailable in test composition.

Pass if:
- Feishu connects;
- research still works;
- generic send/callback tests still work.

## B. Session/profile gates

### B1 Group binding
In Research group:

```text
/profile research
```

Then send a normal follow-up.

Expected:
- no need to repeat `/profile`;
- effective profile remains research.

### B2 Thread override
Group default research.

In one thread:
```text
/profile writing
```

Expected:
- that thread uses writing;
- other group messages remain research.

### B3 Quant allowed group
In approved Quant Lab:

```text
/quant
今天盯什么？
```

Expected:
- router selects quant-decision;
- adapter remains unaware of business logic.

### B4 Quant DM denial
In P2P:

```text
/quant
```

Expected:
- no Quant agent run;
- explicit profile-policy denial;
- no side effect.

### B5 Quant wrong-group denial
In allowed generic Feishu group not present in Quant profile channel allowlist:

```text
/profile quant-decision
```

Expected:
- denied.

## C. Transport gates

### C1 Mention
Group message without @bot:
- ignored under v0.1 mention policy.

With @bot:
- delivered once.

### C2 Duplicate event
Inject same message/event twice.

Expected:
- exactly one runtime dispatch.

### C3 Bot loop
Inject sender type bot/app.

Expected:
- no runtime dispatch.

### C4 Reconnect
Drop network briefly or simulate transport reconnect.

Expected:
- service reconnects;
- no duplicate execution for already handled message.

### C5 Reply/thread
Agent response appears as intended:
- reply to source message;
- thread reply where requested by generic session semantics.

## D. Outbound gates

### D1 Markdown/text
Normal response renders correctly.

### D2 Long response
SDK chunking/format behavior works; adapter does not implement arbitrary manual
split logic unless required by existing renderer.

### D3 File
Generic artifact/file is delivered.

### D4 Approval
Generic approval card:
- approve;
- reject;
- repeated click.

Expected:
- one final runtime decision;
- card reflects completion.

## E. OPi5 operational gates

### E1 Service
```bash
systemctl --user status <actual-zuaef-unit> --no-pager
```

Healthy.

### E2 Restart
```bash
systemctl --user restart <actual-zuaef-unit>
```

Feishu reconnects.

### E3 Reboot contract
Unit is enabled or otherwise started by the same mechanism as current runtime.

### E4 Secret hygiene
```bash
git grep -n "FEISHU_APP_SECRET"
git status --short
```

No secret value in git-tracked content.

## F. Regression

Run repository's established gates.

At minimum, where applicable:

```bash
uv sync --frozen
uv run pytest
uv run ruff check .
git diff --check
```

Do not replace current project gates with these if the deployed branch has a more
specific test procedure.

## Final PASS

PASS requires all:
- generic multi-profile behavior;
- Quant group-only restriction;
- no business coupling in adapter;
- dedup/replay protection;
- OPi5 persistence/reconnect;
- no regression.
