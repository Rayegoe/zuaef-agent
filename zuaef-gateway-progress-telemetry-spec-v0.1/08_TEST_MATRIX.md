# 08 — Test Matrix

## Schedule unit tests

### S1 default first checkpoints

Assert exact:

```text
25, 50, 100, 175, 275, 400, 550, 725, 925, 1150
```

### S2 custom 30/60

Assert:

```text
30, 60, 120, 210, 330, 480
```

### S3 disable

`first=0` -> no watchdog thread / no progress.

### S4 invalid ordering

`first=25, second=25` -> clear config error.

`first=50, second=25` -> clear config error.

negative -> clear config error.

## Watchdog lifecycle tests

### W1 one thread per run

Prove one enabled run creates one watchdog loop, not N checkpoint threads.

### W2 stop before first deadline

No progress sent.

### W3 two checkpoints then settle

Exactly two pings; no later ping.

### W4 absolute deadlines

Inject fake monotonic clock/wait primitives or isolate the schedule helper; prove render/send latency does not accumulate into later deadlines.

Do not make unit tests sleep for real 25/50 seconds.

### W5 transport failure

A failed progress send logs warning and does not fail/cancel the run.

### W6 terminal race

If settlement/stop occurs during fact collection, no progress message is sent afterward.

### W7 unexpected run exception

Watchdog is stopped even when run call raises outside the current CompositionError path.

## Fact tests

### F1 completed requests only

An in-flight model request does not increment completed count.

### F2 tool count

Unique tool-call IDs counted once across started/completed/failed lifecycle events.

### F3 current tool

Only currently-started tool is shown.

### F4 settling suppresses

`SETTLING`, terminal receipt or pause receipt -> no “still processing” ping.

## Live usage tests

### U1 settled responses

Two completed requests with persisted usage -> exact cumulative input/output.

### U2 cache fields

Cache read/write values are extracted when provider response usage exposes them.

### U3 cache subset

Renderer shows cache annotation but does not add it to input.

### U4 provider no cache data

Input/output still render, cache clause omitted.

### U5 historical semantic messages

Snapshot containing prior-run history plus current-run responses correlates only the current run's trailing responses.

### U6 in-flight next request

Fresh request count may be ahead of persisted usage boundary -> token text is unavailable rather than stale/misleading.

### U7 ambiguous correlation

Usage omitted/unavailable; no estimate.

### U8 terminal receipt

Receipt aggregate remains authority over live snapshot aggregate.

## Renderer tests

### R1 formatter boundaries

Test all numeric examples from `05_RENDERER_UX.md`.

### R2 full message

Assert exact ordering:

```text
requests -> tools -> current tool
usage/cache/output -> elapsed
```

### R3 missing fields

No `None`, no fake `0`, no malformed separators.

### R4 no internals

No run id, args, prompt, token prices, percentage.

### R5 ACK unchanged

Existing natural ACK tests remain green.

### R6 terminal unchanged

Existing completed/failed/limit presentation tests remain green.

## Config tests

- env defaults 25/50;
- custom values parse;
- 0 disable;
- invalid relationship fails startup;
- `ZUAEF_RUN_ACK` remains independent.

## Regression

Run repository-required:

```text
targeted Gateway/web tests
full pytest
ruff according to repo policy
BUILD_MANIFEST integrity
```

Distinguish pre-existing unrelated failures.
