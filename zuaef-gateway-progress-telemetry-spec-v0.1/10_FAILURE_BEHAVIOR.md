# 10 — Failure / Degradation Behavior

## Persisted run facts unavailable

Send minimal truthful progress:

```text
还在处理。
已运行 100 秒——出结果直接回你。
```

Do not fail the run.

## Request/tool facts available, usage unavailable

```text
还在处理：4 轮模型 · 7 次工具 · Token 用量暂不可用
已运行 100 秒——出结果直接回你。
```

## Cache unavailable

Render input/output without cache clause.

## Progress transport send fails

- log warning;
- continue execution;
- keep future checkpoints active;
- do not retry aggressively at the same checkpoint;
- terminal delivery still proceeds normally.

## Projector parsing error

Treat affected optional facts as unavailable.

Do not invent replacements.

## Invalid schedule config

Fail Gateway startup before accepting messages.

## Gateway restarts mid-run

Do not invent durable watchdog recovery.

Existing Gateway/session recovery handles routing truth; this Spec does not add progress replay.

## Very long run

Arithmetic progression continues.

No interval cap in v0.1.

Collect evidence before adding one.
