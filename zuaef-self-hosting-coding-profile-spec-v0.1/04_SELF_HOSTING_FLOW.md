# 04 — Self-Hosting Flow

## Definition

The coding profile is "self-hosting" when it can change the same codebase that defines its own future capability composition.

This is source-level self-hosting, not unsafe live monkey-patching.

## Flow A — Add a new Skill

User:

```text
给你自己增加一个处理 GitHub issue triage 的 skill。
```

Expected behavior:

```text
inspect current skills
-> choose Skill because no new executable action is required
-> create .agents/skills/.../SKILL.md
-> validate existing Skills discovery rules
-> targeted tests if repository has them
-> git diff
-> report changed + verification
```

No plugin is required.

## Flow B — Add a new Toolset / plugin

User:

```text
以后你要能读取某个内部结构化数据源，给自己增加组件。
```

Expected:

```text
inspect plugin_api + similar plugin
-> implement lowest viable Toolset/plugin
-> add entry point/workspace dependency if needed
-> add profile composition
-> run uv sync/profile check/tests
-> inspect diff
-> optional local commit
-> report activation requirement
```

## Flow C — Modify coding profile itself

User:

```text
给 coding profile 加上 web search，因为这次已经证明缺官方文档会卡住。
```

Expected:

```text
inspect profile + host ceiling
-> change only the coding profile
-> verify profile resolves
-> do not enable web globally
-> report whether gateway restart/profile rebind is required
```

## Flow D — Core change

User/task exposes a real kernel problem.

Expected:

```text
reproduce failure
-> read AGENTS.md kernel admission rule
-> prove Skill/Toolset/Plugin/Profile cannot contain it
-> make smallest core patch
-> rerun same reproduction
-> full relevant regression
```

"Self-hosting" does not waive core admission rules.

## Spec Pack execution

When the prompt references a Spec Pack:

1. Locate the path from:
   - current message attachment paths;
   - explicit workspace path;
   - explicit repo path.
2. Inspect the pack's source-of-truth/master prompt/tasks.
3. Resolve conflicts using repository authority:
   - live local tree;
   - `AGENTS.md`;
   - current pack;
   - older docs.
4. Execute the pack directly.
5. Use Codex/Pi only if:
   - user explicitly asks; or
   - the Agent has a concrete reason that an external coding worker improves the result.
6. Do not hand every Spec Pack to Codex by default.

## Local commit policy

A local Git commit is an engineering record, not external delivery.

If `allow_local_commit=true`, the Agent may create a local commit after:
- requested outcome is implemented;
- relevant tests are green;
- diff is inspected;
- no obvious unrelated changes are included.

Do not push by default.

## Runtime Capability Creation

PydanticAI Harness now provides Runtime Capability Creation: an Agent can author, validate and persist capabilities for later activation.

Do not make it a v0.1 dependency.

Reason:
- current ZUAEF composition freezes profile/plugin identity for continuation;
- active runtime-authored capability sets are an additional run-composition fact;
- blindly loading the store during a resumed run could change the capability set.

Future admission condition:
- integrate it without breaking frozen resume semantics;
- no second manifest/ledger added by ZUAEF;
- use upstream store/activation contract directly.

Until then, source-level plugin/skill/profile creation is already sufficient for the requested self-hosting product outcome.
