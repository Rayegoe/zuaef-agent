# 00 — Source of Truth

## Existing facts

Current `GatewayConfig` has:

```python
run_ack: bool = True
run_progress_seconds: int = 25
run_progress_seconds_2: int = 50
```

Current environment names:

```text
ZUAEF_RUN_ACK
ZUAEF_RUN_PROGRESS_SECONDS
ZUAEF_RUN_PROGRESS_SECONDS_2
```

Current `GatewayService`:

- sends ACK at run acceptance;
- starts progress watchdog before synchronous agent execution;
- stops progress watchdog before terminal/pause settlement;
- currently creates one daemon thread **per configured checkpoint**;
- currently has exactly two checkpoints;
- reads request count/current tool from persisted StepPersistence facts;
- progress failures are non-fatal.

Current renderer is deterministic and model-free.

Current web projector already owns the generic run-fact projection and final usage aggregation.

## Frozen decisions

### D1 — Gateway owns presentation timing only

Progress is transport/presentation behavior.

It must never alter:

- Agent execution;
- request/tool limits;
- continuation;
- approval semantics;
- receipts;
- business outcome.

### D2 — Reuse existing persistence

StepPersistence / existing snapshots / receipts remain the only execution facts.

No progress-specific persistence is admitted.

### D3 — One watchdog thread per active run

Replace current “one thread per checkpoint” with one daemon watchdog loop per run.

This prevents the arithmetic sequence from causing unbounded thread creation.

### D4 — Arithmetic-backoff schedule

Reuse the existing first/second checkpoint settings as the only numeric seeds.

Let:

```text
A = first checkpoint = ZUAEF_RUN_PROGRESS_SECONDS       (default 25)
B = second checkpoint = ZUAEF_RUN_PROGRESS_SECONDS_2   (default 50)
g = B - A                                               (default 25)
```

For checkpoint index `n >= 1`:

```text
T_n = A + g * n * (n - 1) / 2
```

where `T_n` is absolute elapsed time from run start.

Default:

```text
T1=25
T2=50
T3=100
T4=175
T5=275
T6=400
T7=550
...
```

Equivalent intervals:

```text
d1 = A
d_n = (n-1) * g, for n >= 2
```

Default intervals:

```text
25, 25, 50, 75, 100, 125, 150, ...
```

### D5 — Preserve existing config instead of inventing more knobs

Do not add:

```text
PROGRESS_BACKOFF_STEP
PROGRESS_MAX_INTERVAL
PROGRESS_CHECKPOINTS
PROGRESS_STATE
```

in v0.1.

Existing two values completely define the progression.

### D6 — No interval cap in v0.1

Do not add an arbitrary maximum interval without a reproduced long-run UX failure.

### D7 — Actual elapsed time is measured

Scheduling uses monotonic time.

Rendered elapsed time is actual measured elapsed time at fact collection, not the nominal checkpoint constant.

### D8 — Usage is settled/provider-reported only

Never estimate tokens.

Never infer current in-flight request usage.

Never call the provider to fetch usage just for progress.

### D9 — Cache tokens are a subset, not additive

Display:

```text
输入 465.8k（缓存读取 423.7k）
```

Never calculate:

```text
input + cache_read
```

as a total.

### D10 — Terminal truth wins races

After a run settles, no later “还在处理” message may be emitted.
