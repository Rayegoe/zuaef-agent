# 12 — Master Implementation Prompt

Implement `ZUAEF Gateway Progress Telemetry v0.1` in the current `Rayegoe/zuaef-agent` repository.

## Outcome

Upgrade the existing generic Gateway mid-run progress bridge from two fixed pings into an arithmetic-backoff, host-fact-only progress experience with cumulative settled token usage.

Default behavior:

```text
ACK       0s
P1       25s
P2       50s
P3      100s
P4      175s
P5      275s
P6      400s
P7      550s
...
```

Default wait intervals are:

```text
25, 25, 50, 75, 100, 125, 150, ...
```

Use the existing two config values as seeds:

```text
first  = ZUAEF_RUN_PROGRESS_SECONDS
second = ZUAEF_RUN_PROGRESS_SECONDS_2
step   = second - first
T_n    = first + step*n*(n-1)/2
```

No new schedule knobs in v0.1.

## Architecture

Reuse:

- existing GatewayService progress seam;
- existing StepPersistence facts;
- existing web readers/projector;
- existing deterministic renderer;
- existing surface send path.

Do not add telemetry persistence, a queue, event bus, model call, agent tool, profile schema, or a second runtime state machine.

The only transient states are watchdog presentation states in memory.

## Required implementation

1. Read live repo authority and current pinned PydanticAI/Harness APIs.
2. Add pure arithmetic checkpoint calculation + validation.
3. Replace current one-thread-per-checkpoint behavior with one daemon watchdog thread per active run.
4. Anchor deadlines to `time.monotonic()` run-watchdog start so render/send latency does not drift future checkpoints.
5. Guarantee watchdog cancellation on settle/error and suppress stale post-terminal pings.
6. Extend `_progress_facts` with unique observed tool-call count.
7. Reuse/extend shared web projector for cumulative **settled provider-reported** live usage.
8. Extract input/output and cache-read/cache-write from persisted response usage when the pinned public API provides them.
9. Correlate live snapshot usage conservatively. If correlation is stale/ambiguous, say usage is unavailable; never estimate.
10. Preserve terminal receipt aggregate as final authority.
11. Extend progress renderer using the exact UX/format rules in this pack.
12. Keep natural ACK and terminal messages unchanged.
13. Keep existing config env names; `first=0` disables; enabled schedules require `second>first`.
14. Update docs/tests/BUILD_MANIFEST surgically.
15. Deploy through existing OPi5 procedure and run a real Feishu canary long enough to observe at least 25/50/100/175 checkpoints if the task duration permits.

## Token truth

Cache-read tokens are a subset of input tokens. Render them parenthetically. Never add them to input.

Never estimate in-flight usage.

Progress must add zero model requests and zero Agent tool calls.

## Expected progress UX

```text
还在处理：4 轮模型 · 7 次工具 · 当前 repo_search_files
输入 82.4k（缓存读取 61.2k）/ 输出 1.7k · 已运行 50 秒——出结果直接回你。
```

If coherent live usage is absent:

```text
还在处理：4 轮模型 · 7 次工具 · Token 用量暂不可用
已运行 50 秒——出结果直接回你。
```

## Acceptance

- arithmetic schedule correct;
- one watchdog thread per run;
- actual elapsed time displayed;
- no extra model/tool calls;
- no post-terminal progress;
- live usage never exceeds final `/inspect` receipt aggregate;
- Feishu and Telegram remain generic consumers;
- full existing Gateway/runtime behavior remains green.

## Final report

Return:

- files changed;
- schedule formula and effective defaults;
- exact live usage source/correlation rule;
- focused/full tests;
- real Feishu checkpoint times and rendered examples;
- final `/inspect` consistency check;
- local commit;
- restart/deployment state;
- any unavailable provider usage facts.
