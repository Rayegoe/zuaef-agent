# 03 — Progress Facts Contract

## User-visible facts

Progress may render:

```text
requests             completed model requests only
tool_calls           unique tool calls observed so far
tool_name            one currently running tool, if any
input_tokens          settled cumulative provider-reported input tokens
output_tokens         settled cumulative provider-reported output tokens
cache_read_tokens     settled cumulative cache-read subset, when reliable
elapsed_seconds       actual monotonic elapsed seconds
```

## Internal fact

The fact reader may also return:

```text
activity
```

for suppression decisions, but it need not be shown to users.

## Request count

Count only model requests with authoritative completion evidence.

Do not count an in-flight request as completed.

## Tool count

Count unique `tool_call_id` values observed in current run events.

This count may include:

```text
started
completed
failed
```

because it is “工具调用次数”, not “successful tools”.

Do not count retry/error events twice for the same tool call id.

## Current tool

Show only a tool call with current `started` status.

When activity is `SETTLING` or a terminal/paused receipt exists, suppress current-tool text and suppress the whole progress ping.

## Unknown remains unknown

Do not substitute zero for unavailable facts.

Examples:

- no usage fact yet -> token clause unavailable;
- no tool calls yet -> omit tool-call clause or display 0 only if zero is authoritatively derivable from events;
- no current tool -> omit current-tool clause.

## No tool args/results

Progress never renders:

- tool arguments;
- tool output;
- prompts/responses;
- file names inferred from tool args;
- secrets;
- run id.
