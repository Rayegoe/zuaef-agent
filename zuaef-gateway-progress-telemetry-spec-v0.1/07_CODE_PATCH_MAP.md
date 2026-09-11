# 07 — Code Patch Map

## Primary expected changes

### `src/zuaef_agent/gateway/runner.py`

- keep existing env names;
- update comments/semantics;
- validate schedule seed relationship during startup/config validation;
- continue passing the two seed values to `GatewayService`.

### `src/zuaef_agent/gateway/service.py`

- replace list-of-stop-events with one stop Event per run;
- replace two fixed checkpoint threads with one arithmetic watchdog loop;
- use monotonic absolute deadlines;
- guarantee watchdog stop on all run exit paths;
- extend `_progress_facts()` with tool count and shared usage projection;
- suppress progress for settling/terminal state.

### `src/zuaef_agent/gateway/renderer.py`

- add request/tool/usage/cache fields to `render_run_progress`;
- add deterministic compact-token formatter;
- preserve ACK/terminal behavior.

### `src/zuaef_agent/web/projector.py`

- extend persisted response usage extraction to cache fields where supported;
- add conservative live settled-usage aggregation;
- preserve receipt aggregate priority.

## Expected tests

Likely update existing:

```text
tests/test_gateway_service.py
tests/test_gateway_renderer.py
tests/test_gateway_cli.py or config-related gateway tests
tests/test_web_console.py / projector-focused tests
```

Prefer extending existing test files over creating a new subsystem test file.

## Documentation

Likely:

```text
.env.example
ops/systemd/README.md and/or existing Gateway docs
```

## Manifest

Update `BUILD_MANIFEST.json` surgically according to repo authority.

## Normally unchanged

Do not modify unless a reproduced implementation constraint requires it:

```text
src/zuaef_agent/runtime.py
src/zuaef_agent/core.py
src/zuaef_agent/continuation.py
src/zuaef_agent/plugin_api.py
src/zuaef_agent/composition.py
src/zuaef_agent/gateway/feishu.py
src/zuaef_agent/gateway/telegram.py
```

No surface-specific progress branch should be needed.
