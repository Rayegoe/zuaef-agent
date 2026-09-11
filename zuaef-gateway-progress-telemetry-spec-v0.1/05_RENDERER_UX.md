# 05 — Progress Renderer UX

## ACK unchanged

Fresh run:

```text
收到，开始处理（coding），结果出来直接回你。
```

Continuation wording remains existing behavior.

## Preferred progress shape

Use at most two short lines.

### Full facts

```text
还在处理：4 轮模型 · 7 次工具 · 当前 search_files
输入 82.4k（缓存读取 61.2k）/ 输出 1.7k · 已运行 50 秒——出结果直接回你。
```

### No active tool

```text
还在处理：4 轮模型 · 7 次工具
输入 82.4k / 输出 1.7k · 已运行 50 秒——出结果直接回你。
```

### Usage temporarily unavailable

```text
还在处理：4 轮模型 · 7 次工具 · Token 用量暂不可用
已运行 50 秒——出结果直接回你。
```

### Before first completed request

```text
还在处理：当前 repo_run_command
已运行 25 秒——出结果直接回你。
```

or, if no current tool:

```text
还在处理。
已运行 25 秒——出结果直接回你。
```

## Wording rules

- `轮模型` means completed requests.
- `次工具` means unique tool calls observed.
- `当前 X` only if a tool is genuinely in-flight.
- No percentage complete.
- No invented phase names.
- No run id.
- No model chain-of-thought.
- No tool args.
- No token budget remaining estimate.

## Token formatter

Deterministic formatter:

```text
0..999                   integer
1,000..999,999           k, max 1 decimal, strip trailing .0
>=1,000,000               M, max 2 decimals, strip trailing zeros
```

Examples:

```text
0          -> 0
999        -> 999
1000       -> 1k
1500       -> 1.5k
82400      -> 82.4k
465795     -> 465.8k
1000000    -> 1M
1250000    -> 1.25M
12345000   -> 12.35M
```

Do not use locale commas in compact display.

## Cache display

Show cache clause only when `cache_read_tokens` is known and `> 0`.

Example:

```text
输入 466k（缓存读取 424k）/ 输出 9.7k
```

## Final/failed rendering

Do not change current terminal presentation policy.

Operational usage details remain in `/inspect` after settlement.
