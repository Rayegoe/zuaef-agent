# 02 — Transient Watchdog State Machine

This state machine is **not persisted** and is not a runtime/business state machine.

It is one host-side presentation loop per active run.

## States

```text
DISABLED
WAITING(n)
SNAPSHOT(n)
EMIT(n)
STOPPED
```

## Transitions

```text
run accepted
  |
  +-- first == 0 -----------------> DISABLED
  |
  +-- enabled --------------------> WAITING(1)

WAITING(n)
  +-- stop Event set -------------> STOPPED
  +-- deadline reached -----------> SNAPSHOT(n)

SNAPSHOT(n)
  +-- run is settled/settling ----> STOPPED
  +-- facts unavailable ----------> EMIT(n) with minimal truthful facts
  +-- facts available ------------> EMIT(n)

EMIT(n)
  +-- stop detected before send --> STOPPED
  +-- send succeeds --------------> WAITING(n+1)
  +-- send fails -----------------> WAITING(n+1) + warning log

terminal/pause settlement
  -> set stop Event
  -> remove watchdog registration
  -> STOPPED
```

## Data held in memory

Minimal recommended host state:

```python
_progress_stops: dict[str, threading.Event]
```

The thread itself owns:

```text
start_monotonic
checkpoint_index
```

Do not persist either.

## Thread lifecycle

Exactly one daemon thread is started for one enabled active run.

Pseudocode:

```python
def watchdog(run_id, session, stop):
    started = time.monotonic()
    n = 1
    while True:
        deadline = started + checkpoint_seconds(n)
        remaining = max(0.0, deadline - time.monotonic())
        if stop.wait(remaining):
            return

        if not still_registered(run_id, stop):
            return

        elapsed = int(max(0.0, time.monotonic() - started))
        facts = progress_facts(run_id, elapsed_seconds=elapsed)

        if facts.activity in TERMINAL_OR_SETTLING:
            return

        if stop.is_set() or not still_registered(run_id, stop):
            return

        try:
            send(render(facts))
        except Exception:
            log warning

        n += 1
```

## Settlement race rule

The watchdog checks stop/registration:

1. after wake;
2. after fact collection;
3. immediately before send.

This minimizes the race where terminal result and progress message cross.

The watchdog must never block terminal settlement on thread `join()`.

## Unexpected execution exceptions

The run-start seam should use `try/finally` or equivalent so the watchdog stop is guaranteed even if a non-CompositionError exception leaves the synchronous run call.

Do not change how that exception is otherwise surfaced/settled.
