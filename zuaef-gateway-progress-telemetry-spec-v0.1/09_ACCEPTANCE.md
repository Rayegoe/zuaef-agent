# 09 — Production Acceptance

Unit tests are supporting evidence. Release requires a real Gateway canary.

## Feishu canary

Use one task that naturally runs longer than 3 minutes (coding or quant is acceptable).

Expected transport behavior:

```text
t≈0     natural ACK
t≈25    progress P1
t≈50    progress P2
t≈100   progress P3
t≈175   progress P4
...
terminal result
```

If the run finishes before a checkpoint, that checkpoint must not be sent.

## Message content

Once at least one settled usage snapshot is available, progress should look approximately like:

```text
还在处理：4 轮模型 · 7 次工具 · 当前 repo_search_files
输入 82.4k（缓存读取 61.2k）/ 输出 1.7k · 已运行 50 秒——出结果直接回你。
```

If usage is not coherently available:

```text
Token 用量暂不可用
```

is acceptable.

## Hard acceptance gates

### A — No model overhead

Compare model-request trajectory: progress system itself adds **zero** model requests and zero agent tool calls.

### B — Arithmetic timing

First checkpoints follow configured arithmetic sequence, within live scheduling tolerance.

### C — One watchdog thread per run

No growth proportional to number of future checkpoints.

### D — Fact truth

Progress values are host-derived/persisted facts only.

### E — Usage monotonicity

When token totals are shown in multiple progress messages:

```text
input_n+1 >= input_n
output_n+1 >= output_n
cache_n+1 >= cache_n (when both known)
```

### F — Final consistency

Final `/inspect` totals must be >= the last displayed settled progress totals.

A progress total must never exceed final authoritative receipt aggregate.

### G — No post-terminal ping

After terminal/pause delivery, zero additional progress messages.

### H — Surfaces remain generic

Same Gateway logic works for Feishu and Telegram; no profile-specific or surface-specific business branch.

### I — Restart/recovery behavior unchanged

Progress state is transient. Gateway restart does not attempt to reconstruct old pings.

Existing session recovery remains authoritative for routing/run settlement.
