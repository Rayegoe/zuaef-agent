# 06 — Codex and Pi Role

## Product stance

Codex and Pi are useful, but they are not the architecture.

They are equivalent to other advanced engineering commands available to a trusted coding agent.

## Correct relationship

```text
ZUAEF coding profile
    |
    +-> uses its own FileSystem/Shell/RepoContext/CodeMode
    |
    +-> optionally runs `codex ...`
    |
    +-> optionally runs `pi ...`
```

Not:

```text
ZUAEF -> backend selector -> worker runtime -> Codex/Pi
```

## Why

The PydanticAI Agent already owns:
- semantic task understanding;
- tool choice;
- planning;
- context;
- execution receipts;
- conversation continuity.

Putting another ZUAEF orchestration layer between the Agent and the coding command duplicates those concerns.

## Codex

If `allow_codex=true`, add the installed `codex` executable to the repo Shell allowlist.

The Agent may use the repository's currently supported non-interactive invocation when needed.

Do not hardcode one Codex path in the plugin.

Resolve through normal PATH/environment used by the Gateway deployment.

## Pi

If `allow_pi=true`, add `pi` to the allowlist.

Use its installed CLI contract directly.

Do not build `PiBackend`.

## Default decision policy

Prefer own Harness abilities for normal edits.

Use external worker when:
- user explicitly requests it;
- large code transformation benefits from a specialist coding CLI;
- independent review is useful;
- the current model is blocked by a coding problem but the external worker may solve it.

## Authority

An external worker's output is evidence / implementation output.

The ZUAEF Agent remains responsible for:
- reading the resulting diff;
- running relevant tests;
- deciding whether the requested outcome is actually met;
- reporting failures accurately.

Do not blindly equate worker exit code 0 with task completion.

## Existing supervisor loop

`tools/supervisor_loop.py` remains a separate internal Supervisor transport.

Do not refactor it into this coding profile unless a concrete later requirement demands convergence.

This pack does not delete it.
