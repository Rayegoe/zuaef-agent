# 06 — Implementation Tasks

## P0 — Local truth / no-code baseline

### T000 Runtime seam audit
On OPi5:

```bash
pwd
git status --short --branch
git rev-parse HEAD
git log -1 --oneline --decorate
systemctl --user --type=service --all | grep -i zuaef || true
systemctl --user --type=timer --all | grep -i zuaef || true
rg -n "SurfaceAdapter|SessionBinding|ProfileRouter|profile.*route|gateway|approval|pending_cursor" .
```

Record:
- actual repo path;
- actual branch/commit;
- running units;
- gateway process;
- session store;
- profile router;
- current Telegram surface seam, if any.

Stop if the checkout is dirty in unrelated high-risk files; do not overwrite user work.

### T001 Verify Python/package baseline
Confirm:
- Python >=3.11;
- `uv` workspace is healthy;
- current tests pass before change.

## P1 — Package and generic surface skeleton

### T010 Add Feishu integration package/module
Follow existing repository conventions.

If surfaces are plugins, create a workspace member such as:

```text
plugins/zuaef-feishu/
```

If surfaces live under runtime/gateway code, use the existing layout instead.

Add exactly:

```text
lark-channel-sdk==1.4.0
```

to the narrowest package that owns Feishu.

Do not add it globally unless the repository architecture requires global runtime
dependencies.

### T011 Configuration
Add non-secret config:
- enabled;
- group allowlist;
- user allowlist;
- require mention;
- security mode;
- optional default profile mapping.

Secrets come from environment only:
- `FEISHU_APP_ID`;
- `FEISHU_APP_SECRET`.

## P2 — Transport

### T020 Construct FeishuChannel
Use standalone import:

```python
from lark_channel import FeishuChannel
```

Default transport:
```text
ws
```

Register:
- message;
- cardAction;
- error;
- reconnect/reconnected if useful for logs.

### T021 Lifecycle
Hook start/stop into the existing gateway lifecycle.

Must support:
- ready state;
- graceful disconnect;
- reconnect logs;
- no orphan event loop.

### T022 Queue bridge only if required
If existing SurfaceAdapter requires `poll_once`, bridge pushed SDK events into an
internal async queue.

Do not implement API polling.

## P3 — Inbound normalization

### T030 Message normalization
Map:
- chat_id;
- chat_type;
- sender.open_id;
- sender_name;
- message_id;
- reply/thread context;
- `body_text`;
- resources.

Prefer SDK normalized structures.

### T031 Authorization
Surface-level:
- group allowlist;
- user allowlist;
- require mention;
- ignore bots.

### T032 Idempotency
Ensure duplicate SDK delivery creates one runtime inbound dispatch.

## P4 — Runtime/profile handoff

### T040 Session key
Reuse generic SessionBinding.

Fields:
```text
surface=feishu
channel_id=chat_id
thread_id=<normalized>
```

### T041 Profile commands
Implement `/profile` and aliases in Profile Router.

Do not parse Quant aliases inside FeishuAdapter.

### T042 Quant group-only policy
Add router/profile policy:

```text
quant-decision:
  chat_type=group
  channel allowlist=<approved Quant group>
```

P2P attempt must fail before agent run.

### T043 Profile precedence
Thread binding > chat binding > group default > general.

Use existing semantics if equivalent.

## P5 — Generic outbound

### T050 Text/markdown
Use `channel.send`.

Use reply-to when responding to a specific message.

### T051 Thread reply
Use SDK `reply_in_thread` where runtime surface semantics indicate thread reply.

### T052 Artifact/document
Use generic file sending through SDK.

Do not make a Quant-specific report sender.

### T053 Generic cards
Implement a generic card renderer sufficient for:
- approval;
- status;
- generic actions.

No Quant-specific card schema.

## P6 — Approval callbacks

### T060 Send approval
Render existing runtime approval object to a generic Feishu card.

### T061 Handle cardAction
Normalize:
- actor;
- action value;
- message/chat identity;
- approval/request id.

Hand to existing approval engine.

### T062 Idempotent completion
Repeated click must not execute the approved effect twice.

Update card to final state.

## P7 — Operations on OPi5

### T070 Integrate existing service
Prefer extending existing runtime/gateway service.

Only create a separate gateway service if there is no generic persistent gateway
host.

### T071 Secret environment file
Create local operator-owned env file, mode 600.

### T072 Startup/restart
Enable appropriate systemd unit and verify reboot-safe startup.

### T073 Logging
Log:
- connect;
- disconnect;
- reconnect;
- rejected group/user;
- profile selected;
- dispatch id;
- send failure.

Do not log:
- App Secret;
- full tokens;
- sensitive content by default.

## P8 — Tests and closure

### T080 Unit tests
Normalization, session identity, policy, callback mapping.

### T081 Integration fixture
Synthetic Feishu events -> runtime -> mock Channel sender.

### T082 Multi-profile acceptance
Same Bot:
- research;
- writing/general;
- quant-decision in allowed group.

### T083 Risk tests
- DM cannot use quant;
- forbidden group cannot use quant;
- bot sender ignored;
- duplicate event runs once;
- callback replay runs once.

### T084 Regression
Run entire existing test suite plus lint/check gates.

### T085 Evidence
Produce one concise acceptance report with:
- changed files;
- tests;
- runtime service state;
- one successful group interaction per required profile;
- one rejected DM Quant attempt;
- known limitations.
