# ZUAEF Gateway Progress Telemetry v0.1 — Spec Pack

Status: implementation-ready  
Target repo: `Rayegoe/zuaef-agent`  
Scope: generic Gateway progress UX for Feishu and Telegram  
Primary outcome: long runs stay observable without fixed-interval spam or extra model work.

## Product definition

When a run lasts longer than the initial acknowledgement window, Gateway emits deterministic progress messages from already-persisted runtime facts.

The default schedule is:

```text
ACK      t≈0
P1       t=25s
P2       t=50s
P3       t=100s
P4       t=175s
P5       t=275s
P6       t=400s
P7       t=550s
P8       t=725s
P9       t=925s
P10      t=1150s
...
```

The first two checkpoints stay fast. After that, the **wait interval grows arithmetically by 25 seconds each time**:

```text
25, 25, 50, 75, 100, 125, 150, 175, 200, 225, ...
```

Each progress message may show, when truthfully available:

```text
completed model requests
observed tool-call count
currently running tool name
settled cumulative input tokens
settled cumulative output tokens
cache-read tokens as a subset of input
actual elapsed seconds
```

No progress ping may trigger a model request.

## Current implementation to extend

The repo already has:

- natural ACK rendering;
- two fixed progress checkpoints (25s, 50s);
- host-only progress watchdog;
- `_progress_facts()` reading persisted StepPersistence facts;
- shared web projector/inspection logic for request/tool/usage facts;
- provider-reported cache token projection in final inspection.

This pack extends those seams instead of adding a telemetry subsystem.

## Non-goals

Do not add:

- durable progress state;
- a progress database/table;
- event bus;
- polling daemon;
- model-generated progress summaries;
- profile-specific progress schemas;
- estimated token counts;
- percentage-complete guesses;
- a second runtime state machine.

The only "state machine" in this pack is an in-memory watchdog lifecycle for presentation timing.
