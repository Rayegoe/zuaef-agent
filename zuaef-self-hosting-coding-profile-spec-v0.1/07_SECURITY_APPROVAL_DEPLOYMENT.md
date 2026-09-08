# 07 — Security, Approval, Deployment

## Trust model

The `coding` profile is privileged.

Only trusted supervisor identities may use it.

Do not expose it to arbitrary Feishu users or customer-facing groups.

## Gateway admission

Reuse existing:
- Feishu user allowlist;
- Feishu group allowlist;
- mention requirement;
- `ZUAEF_GATEWAY_PROFILE_ACCESS`.

Recommended production rule:

```json
{
  "coding": {
    "allowed_surfaces": ["feishu"],
    "allowed_chat_types": ["p2p", "group"],
    "allowed_channel_ids": ["<dedicated-coding-chat-id>"]
  }
}
```

If coding is intended only in DM, use only `p2p`.

## Profile alias

Recommended:

```json
{
  "coding": "coding"
}
```

Then `/coding` may be routed through the existing alias mechanism if the Gateway command parser supports the configured alias path.

Do not add hard-coded `/coding` logic to Gateway.

## Shell is not a security boundary

Harness Shell allowlists are accident guardrails.

A command such as `python` or `git` can itself start other processes.

Therefore the production statement must be:

> coding profile runs only for trusted supervisor input on a trusted host/repository.

Do not market command allowlisting as hostile-code containment.

## Host isolation

Optional future hardening may run the privileged coding deployment under:
- a dedicated Linux user;
- a container;
- ModalSandbox where appropriate;
- systemd sandboxing.

Do not block v0.1 on adding a new sandbox platform if the current operator/host is trusted.

## Repository secret protection

Repo FileSystem must deny obvious secret paths.

Shell must not receive LLM provider keys unnecessarily.

Do not intentionally give the coding agent:
- GitHub PAT;
- SSH private keys;
- cloud root credentials;
- production customer secrets.

## External effects

### Allowed without a new approval workflow

Inside the trusted repo/worktree:
- read source;
- edit source;
- run tests;
- create local files;
- create local Git commit if configured.

### Not automatically authorized in v0.1

- `git push`;
- force push;
- release publishing;
- package publishing;
- production deployment;
- system service restart;
- remote SSH;
- destructive host operations.

Do not solve these by inventing a new approval subsystem.

When required later, use PydanticAI native approval / ApprovalRequiredToolset / a narrowly scoped approved tool.

## Activation boundary

Source code can be completed and verified while the current Gateway process is still running old imported code.

Final answer must explicitly state one of:

```text
implemented + verified + active
implemented + verified + restart required
implemented + partially verified
blocked
```

Do not claim a modified plugin is active unless it actually has been loaded by a fresh process/run.

## Restart

v0.1 does not give the coding Shell `systemctl`.

The operator can restart the Gateway after receiving the result, or a later separately-approved deployment tool can be admitted.

This avoids killing the process before its own terminal reply is sent.

## Git push

Not part of v0.1 autonomous loop.

Local commit is sufficient to produce a durable engineering result.

Human/Codex/Pi remote operation may push later if desired.
