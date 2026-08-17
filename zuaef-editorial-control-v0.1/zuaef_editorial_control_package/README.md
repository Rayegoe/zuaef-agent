# ZUAEF Editorial Control — code deliverable

This package is prepared against:

- repository: `Rayegoe/zuaef-agent`
- baseline commit: `a03fd4a52afddb98e347e5d447fbbbf7975c942f`
- plugin: `plugins/zuaef-ace-writing`
- PydanticAI API floor: `2.27`

## What changes

- **does not touch** `writing_toolset.py`;
- adds `EditorialControlCapability(AbstractCapability[CoreDeps])`;
- adds host-owned editorial evidence models/retrieval;
- composes the capability from the existing `ace-writing` plugin;
- enables capability permission in the example profile;
- bumps plugin version to `0.2.0`;
- adds unit/contract tests;
- includes a full SPEC and example evidence JSONL.

## Files

`repo_overlay/` mirrors paths in the target repository. Copy it over the repository root, or apply `editorial-control.patch`.

## Validation

Recommended from the repository root:

```bash
uv sync
uv pip install -e plugins/zuaef-ace-writing
uv run pytest tests/test_ace_writing_plugin.py tests/test_editorial_control_capability.py
uv run pytest
```

The patch intentionally preserves the existing ACE writing toolset byte-for-byte.

## Product behavior

The control loop is:

```text
observe material
→ prepare evidence-backed cognitive move
→ next model request is nudged
→ observe trajectory
→ update intervention
→ save_artifact candidate
→ bounded pre-side-effect veto if strongly templated
→ local patch
→ save
```

The default store is conservative. The real quality asset is the approved evidence file built from human patches and curated corpus observations.
