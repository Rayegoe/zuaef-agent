# 01 — Schedule and Numeric Contract

## Default sequence

| Ping | Wait since previous | Absolute elapsed |
|---:|---:|---:|
| ACK | — | 0s |
| P1 | 25s | 25s |
| P2 | 25s | 50s |
| P3 | 50s | 100s |
| P4 | 75s | 175s |
| P5 | 100s | 275s |
| P6 | 125s | 400s |
| P7 | 150s | 550s |
| P8 | 175s | 725s |
| P9 | 200s | 925s |
| P10 | 225s | 1150s |
| P11 | 250s | 1400s |
| P12 | 275s | 1675s |

## Formula

For one-based checkpoint number `n`:

```python
step = second - first
checkpoint = first + step * n * (n - 1) // 2
```

Requirements:

```text
first > 0
second > first
```

Special disable case:

```text
first == 0 -> all mid-run progress disabled
```

When `first == 0`, ignore `second` for scheduling and create no watchdog thread.

When `first > 0` and `second <= first`, fail Gateway configuration with a clear `ValueError` before polling begins.

Negative values are invalid.

## Custom examples

### 30 / 60

```text
30, 60, 120, 210, 330, 480, ...
```

Intervals:

```text
30, 30, 60, 90, 120, 150, ...
```

### 20 / 40

```text
20, 40, 80, 140, 220, 320, ...
```

## Why absolute deadlines

Do not implement:

```python
sleep(interval)
collect facts
send
sleep(next_interval)
```

because fact collection and transport latency accumulate drift.

Instead:

```python
started = monotonic()
deadline = started + checkpoint(n)
wait(deadline - monotonic())
```

Each deadline remains anchored to the same start instant.

## Timing tolerance

Tests of the pure schedule formula must be exact.

Live Feishu/Telegram timing is not millisecond-exact. Acceptance tolerance:

```text
observed send time >= nominal deadline
and normally <= nominal deadline + 5 seconds
```

A delayed OS scheduler or transport may exceed this without altering execution truth; actual elapsed in the message must reflect the real delay.
