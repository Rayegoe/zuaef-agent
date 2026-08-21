# T002 — Wall-clock instrumentation

Status: `KEEP_CHANGE`

## Failure

T001 normalized aggregate WCASE facts—requests, tool calls, token usage and
tool-effect facts—but could not show where run time was spent. The missing
facts were per-model-request duration, per-tool-call duration, full-run
duration, and the largest provider-reported request input size.

## Existing surfaces

- `RunReceipt.started_at` / `finished_at` already bound the run lifecycle.
- Harness `StepEvent.timestamp` already existed for model-request and tool-call
  start/terminal events, and existing `StepPersistence` already retained it.
- `ModelResponse.usage.input_tokens` already existed per response; aggregate
  usage remained the receipt source of truth.
- The T001 normalizer already treated unavailable metrics as nullable.

## Minimal change

The runtime now derives `largest_input_tokens` from positive provider-reported
per-response usage, without treating synthetic zero-valued usage as a metric.
The WCASE projection reads existing receipt timestamps and existing public
Harness StepStore events. It pairs model requests in event order and tool calls
by `tool_call_id`, retaining `None` for an unfinished or unavailable interval.
The normalizer passes these fields through and preserves the raw usage/runtime
facts. No events, persistence, model action, capability, prompt, or writing
tool were added or changed by T002.

## Real WCASE sample

Observed from the existing `WCASE-3` learned draft run:

```json
{
  "case": "WCASE-3",
  "variant": "learned",
  "pass": "draft",
  "requests": 9,
  "tool_calls": 18,
  "input_tokens": 162377,
  "wall_clock_ms": 155609.758,
  "request_latencies_ms": [2833.818, 1638.99, 62616.025, 20184.711, 2233.706, 9862.005, 42869.234, 6975.384, 5942.138],
  "tool_latencies_ms": {
    "check_claim": [58.202, 60.127, 59.29, 69.29, 60.516, 70.851, 69.182, 67.909],
    "list_materials": [40.452],
    "read_material": [42.222],
    "read_plan": [1.447],
    "retrieve_knowledge": [45.786],
    "save_artifact": [54.567],
    "update_task_status": [2.424],
    "update_task_statuses": [7.935, 2.911],
    "write_memory": [28.571],
    "write_plan": [2.55]
  },
  "largest_input_tokens": 30067
}
```

## Tests

- Normalizer timing/compatibility tests: `8 passed`.
- Timing projection test: `1 passed`.
- Largest-input receipt tests: `2 passed`.
- Ruff on touched files: passed.
- `git diff --check`: passed.
- Host-permission full suite: `608 passed, 4 failed` in existing manifest and
  production-prompt expectations unrelated to T002; the sandbox run also
  exposed an AnyIO thread-pool hang in an existing Harness test path.

## Behavioral semantics changed?

No. T002 adds only nullable runtime facts to the WCASE projection and receipt
usage payload; it does not alter agent decisions, capability composition,
prompts, writing tools, or model actions.

## Next task

T003 — WCASE-1 current baseline.
