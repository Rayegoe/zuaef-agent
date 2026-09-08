# 10 — Expected Files and Patch Map

This is a planning map, not a command to create every file listed if the installed API makes a smaller patch possible.

## Expected new files

```text
plugins/zuaef-coding/pyproject.toml
plugins/zuaef-coding/zuaef_coding/__init__.py
plugins/zuaef-coding/zuaef_coding/plugin.py
plugins/zuaef-coding/zuaef_coding/skills/coding/SKILL.md
profiles/coding.toml
tests/test_coding_profile.py
```

Feishu attachment tests may go into an existing Gateway/Feishu test file rather than forcing a new file.

## Expected changed files

Likely:

```text
pyproject.toml
uv.lock
src/zuaef_agent/gateway/feishu.py
src/zuaef_agent/gateway/runner.py
BUILD_MANIFEST.json
```

Potentially:
- `.env.example` for coding profile deployment variables;
- ops/systemd env/runbook docs;
- README/docs if production operator commands need documentation.

## Files that should normally remain unchanged

Avoid modifying unless a real implementation constraint proves necessary:

```text
src/zuaef_agent/runtime.py
src/zuaef_agent/continuation.py
src/zuaef_agent/plugin_api.py
src/zuaef_agent/composition.py
src/zuaef_agent/gateway/service.py
src/zuaef_agent/gateway/bridge.py
src/zuaef_agent/models.py
src/zuaef_agent/receipt_store.py
```

Why:
- existing composition already supports plugin capabilities;
- existing bridge already carries attachment paths;
- existing service already routes profiles;
- existing runtime already owns execution truth.

## Explicit forbidden additions

Do not add files/modules named conceptually like:

```text
worker_backend.py
worker_runtime.py
worker_dispatcher.py
coding_orchestrator.py
codex_backend.py
pi_backend.py
worker_receipt.py
coding_job_store.py
```

unless implementation discovers a concrete impossible gap and documents it before proceeding.

## BUILD_MANIFEST

Follow the repository's existing surgical manifest update rule.

Do not regenerate the whole manifest.

Do not add new hash machinery around this feature.
