# 04 — Live Usage / Token Contract

## Goal

Expose cumulative usage from **settled model responses** while a run is still active.

Final receipt remains authoritative after settlement.

## Existing shared seam

Use/extend `src/zuaef_agent/web/projector.py` rather than duplicating token parsing in Gateway.

Current projector already:

- pairs current-run model request events;
- reads persisted snapshot messages;
- extracts per-response usage;
- gives terminal receipt aggregate priority;
- projects final cache-read/cache-write usage when present in receipt.

## Required enhancement

### 1. Extend response usage extraction

For each persisted `ModelResponse.usage`, extract integer values when present:

```text
input_tokens
output_tokens
cache_read_tokens
cache_write_tokens
```

Use public attributes on the pinned PydanticAI version.

Do not assume every provider supplies cache fields.

### 2. Produce a conservative live aggregate

A live run has no terminal receipt yet.

Derive cumulative usage only from a persisted snapshot boundary that can be correlated unambiguously with completed model requests in this run.

Recommended algorithm:

1. Build current-run model-request rows from StepPersistence events.
2. Find latest persisted `ContinuableSnapshot` and its `step_index`.
3. Select completed current-run model requests whose `step_index <= snapshot.step_index`.
4. Let `N` be that count.
5. From snapshot messages, take the trailing `N` model `response` messages as current-run settled responses. Earlier responses may be semantic history from prior runs.
6. Require at least `N` trailing responses and unambiguous ordering.
7. Require input/output usage on every selected response before exposing a cumulative input/output total.
8. Sum those usage values.
9. Sum cache-read/cache-write only if each selected response provides that field consistently; otherwise omit that cache component.

If correlation is ambiguous, return usage unknown.

### 3. Coherence with request count

Do not show a token total that silently lags behind the displayed completed-request count.

If the latest completed request is newer than the persisted snapshot boundary, either:

- display request count but mark token usage unavailable; or
- display only the count corresponding to the same settled snapshot boundary.

Preferred v0.1 UX: keep the freshest completed-request count and render token usage as unavailable until snapshot catches up.

## Final receipt priority

When a receipt exists:

```text
receipt aggregate > live snapshot aggregate
```

No behavior change to `/inspect` authority.

## Cache semantics

Provider input-token count is displayed as reported.

Cache read is a subset annotation:

```text
输入 465.8k（缓存读取 423.7k）
```

Do not subtract cache read to manufacture “uncached input” unless provider contract explicitly gives that independent fact.

Do not add cache read to input.

## Usage unavailable text

When at least one model request has completed but coherent settled usage is not available:

```text
Token 用量暂不可用
```

If zero requests have completed, omit token text entirely rather than claiming unavailable usage before the first response exists.

## No estimates

Forbidden:

```text
characters / 4
prompt length approximation
provider pricing estimates
current streamed-token estimates
```
