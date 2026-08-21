# Installation

This package is designed to merge into the root of `Rayegoe/zuaef-agent`.

From the parent directory of the unpacked coach pack:

```bash
rsync -av --ignore-existing \
  zuaef-runtime-refoundation-coach-pack/ \
  /path/to/zuaef-agent/
```

Review conflicts manually. Do **not** blindly overwrite the repository's existing `AGENTS.md`.

Instead, apply the normative additions described in:

```text
docs/runtime-refoundation/AGENTS_AMENDMENT.md
```

Recommended first commit scope:

```text
.agents/skills/zuaef-runtime-coach/
docs/runtime-refoundation/
prompts/runtime-refoundation/
templates/runtime-refoundation/
```

Do not modify production runtime code in the same commit that introduces this coach pack. The first code change should be a separately reviewable measured experiment.
