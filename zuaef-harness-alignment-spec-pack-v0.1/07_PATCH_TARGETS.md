# Patch Targets and Do-Not-Rewrite List

## 1. Expected candidate-branch dependency files

### `pyproject.toml`

Candidate-only edit during H003:

```text
pydantic-ai-harness[skills,code-mode] >=0.29,<0.30
pydantic-ai compatible with Harness upstream floor (>=2.38,<3)
```

Do not merge until H013 says `PROMOTE_0_29`.

### `uv.lock`

Refresh only as required by candidate dependency resolution.

Do not use this task to opportunistically refresh unrelated dependencies.

## 2. Known compatibility hotspot — test only

### `tests/test_writing_codemode_skills.py`

Known issue:

```python
getattr(caps, "_deferred_capabilities", ())
```

This inspects a private Harness attribute.

Preferred change if 0.29 exposes the problem:

- test the public deferred skill catalog/loading behavior;
- or test the actual model-visible/on-demand capability contract;
- do not add a ZUAEF adapter that recreates `_deferred_capabilities`.

## 3. Highest-value runtime compatibility hotspot

### `src/zuaef_agent/runtime.py`

Focus only on the existing pause frontier persistence seam and any public API changes required by candidate Harness.

Do not refactor unrelated receipt/artifact/effect logic during version work.

### `src/zuaef_agent/continuation.py`

Focus on:

- `FileStepStore`;
- `continue_run(..., include_interrupted=True)`;
- reconstruction of native `DeferredToolRequests/DeferredToolResults`;
- frozen composition and bindings.

If candidate breaks this, isolate whether the break is:

- public API change;
- private/internal assumption;
- behavioral change;
- ZUAEF bug.

## 4. Composition hotspot

### `src/zuaef_agent/core.py`

Expected default: **no architecture change**.

It already directly composes upstream primitives.

Only modify if the public constructor/API changed and a minimal compatibility edit is required.

### `src/zuaef_agent/composition.py`

Expected default: **no architecture change**.

Keep upstream ownership of tool-name collision and ToolSearch/deferred-tool mechanics.

### `src/zuaef_agent/plugin_api.py`

Expected default: **no change**.

Do not broaden PluginBundle into hooks/services/event buses/background tasks for version compatibility.

## 5. Focused tests to preserve/extend

Likely relevant existing tests:

```text
tests/test_generalist_activation.py
tests/test_phase2_generalist_policy.py
tests/test_phase2_deferred_tools.py
tests/test_plugin_composition.py
tests/test_continuation.py
tests/test_execute_run_seam.py
tests/test_writing_codemode_skills.py
tests/test_core_contract_static.py
```

Add/adjust only the smallest tests needed to lock observable compatibility behavior.

## 6. Do not rewrite

Do not use this work to replace or redesign:

- ZUAEF Gateway;
- Telegram bridge;
- quant strategy/runtime;
- domain Toolsets;
- Knowledge model;
- artifact policy;
- runtime-refoundation experiment logic;
- StillWrite integration;
- provider configuration;
- current capability defaults.

## 7. No new engineering ceremony

Do not add for this spec:

- compatibility registry;
- feature matrix service;
- manifest;
- checksum/hash evidence layer;
- schema migration system;
- plugin ABI version service;
- custom event bus;
- generic middleware stack.

A markdown decision record + tests + dependency diff is sufficient.
