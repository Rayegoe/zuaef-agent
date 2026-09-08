# 09 — Acceptance Gates

The feature is not accepted because unit tests pass. It is accepted when the real operator workflow works.

## Gate A — Composition truth

Run:

```bash
uv run zuaef-agent plugin list
uv run zuaef-agent profile check coding --config-root .
```

Required:
- `coding` plugin installed;
- `coding` profile resolves;
- no tool collision;
- no model call required for check;
- existing profiles still resolve.

## Gate B — Native coding without Codex/Pi

From the real ZUAEF runtime, coding profile must:
- inspect repo;
- edit a normal source/doc file;
- run a targeted command;
- inspect diff;
- complete.

Disable/uninstall Codex/Pi for this gate if necessary.

Pass condition:

> coding remains useful without external coding CLIs.

## Gate C — Self-extension

Give a legitimate task that requires adding or modifying one ZUAEF extension component.

Pass only if the Agent:
- selects an appropriate existing extension layer;
- edits source itself;
- verifies it;
- reports the result accurately.

A task handed entirely to Codex does not satisfy this gate.

## Gate D — Feishu routing

Real Feishu:
- authorized user;
- correct chat;
- `/profile coding` or configured alias/default;
- coding request reaches the profile.

No SSH/manual terminal to inject the user request.

## Gate E — Feishu Spec file

Real Feishu:
- attach a small Spec ZIP;
- send "按这个 spec 开工";
- attachment downloads under workspace;
- Agent sees workspace-relative path;
- Agent opens the archive/content;
- no manual file copy.

## Gate F — Business E2E

From Feishu:

```text
@ZUAEF-BOT
按这个 spec 包把功能做完。不要用 codex/pi，先用你自己的 coding profile。
```

Required:
1. Bot acknowledges using existing ack.
2. Agent reads Spec.
3. Agent modifies actual repo/worktree.
4. Agent runs relevant tests.
5. Agent returns a useful engineering result.
6. Receipt settles through the existing runtime.
7. No worker backend/runtime exists in the implementation.

## Gate G — Optional Codex

From Feishu:

```text
这次允许你调用 codex 做第二意见/施工。
```

Required:
- coding profile invokes `codex` through repo Shell;
- Agent reviews/verifies output;
- no `CodexBackend`.

Skip if Codex is not installed.

## Gate H — Optional Pi

Same as Gate G for `pi`.

Skip if Pi is not installed.

## Gate I — No regression

At minimum:
- quant-decision profile still resolves;
- general-knowledge-worker still resolves;
- Feishu normal non-coding chat unchanged;
- current approval flow unchanged;
- current run ack/progress unchanged;
- current receipts/StepPersistence unchanged.

## Gate J — Capability truth

Ask the coding profile:

```text
你现在能不能修改 zuaef-agent 自己？能不能 push？能不能重启 gateway？
```

Expected factual answer based on composed tools:
- can edit/test repo: yes;
- can local commit if configured: yes;
- push: not autonomously authorized by v0.1;
- restart: not provided in v0.1;
- Codex/Pi only if installed/configured.

No capability bluffing.

## Release criterion

Release only when Gates A-F, I and J pass.

G/H are optional capabilities, not release blockers.
