# Architecture

## Four components

```text
                 HUMAN (phone/web)
                   │ activate / merge
                   ▼
          ChatGPT Project Supervisor
                   │ reads / proposes
                   ▼
┌──────────────── GitHub ─────────────────┐
│ main                current code truth  │
│ supervisor-report   evidence channel    │
│ supervisor-control  authorization chan. │
└──────────────▲───────────────┬───────────┘
               │               │
        report push        merged NEXT
               │               ▼
        local publisher   local watcher
               ▲               │
               │          fresh worktree
               │               ▼
          Console /       Codex / ZUAEF
          Run Analysis      Worker
          (observer)       (executor)
```

## Two loops remain separate

Production:

```text
request → observe → decide → act → outcome
```

Improvement:

```text
run/result → observe → evidence → Supervisor → human authorization
→ frozen instruction → worker → new evidence
```

The bus transports authority/evidence; it does not move semantic ownership into host code.

## Why GitHub

GitHub already supplies branch identity, commit identity, history, PR review and mobile merge. Therefore no workflow database, task registry, handoff hash or custom event bus is required.

## Why two branches

`supervisor-report` is local→Supervisor evidence.

`supervisor-control` is Supervisor/human→local authority.

A worker cannot overwrite its own instruction while reporting.

## Why PR only in the control direction

A report is evidence, so direct push is sufficient.

A control instruction can start code execution, so v0.1 uses a native PR:

```text
open = proposed
merged = authorized
closed = rejected/superseded
```

No second status system is added.

## Why fresh worktrees

Concurrent uncommitted edits have already appeared in the primary checkout. Fresh worktrees isolate transport and workers without stashing/resetting human work.

## Why polling

Outbound `git fetch` via a user-level timer requires no local public endpoint, no tunnel and no self-hosted runner.

## Why the phone remains in the loop

The architecture goal is bounded remote supervision, not self-authorized recursive improvement.

The human still activates the Project and normally merges the control PR. Both actions are possible remotely.
