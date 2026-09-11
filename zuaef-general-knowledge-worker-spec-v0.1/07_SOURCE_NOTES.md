# Source Notes

Checked on 2026-09-08.

## Current ZUAEF repository

Repository:
https://github.com/Rayegoe/zuaef-agent

Relevant paths:
- `src/zuaef_agent/core.py`
- `src/zuaef_agent/config.py`
- `src/zuaef_agent/profiles.py`
- `src/zuaef_agent/composition.py`
- `src/zuaef_agent/plugin_api.py`
- `src/zuaef_agent/knowledge_capability.py`
- `profiles/quant-decision.toml`
- `.agents/skills/bmad-build/SKILL.md`
- `.agents/skills/bmad-build-auto/SKILL.md`

Observed:
- one core Agent plus profile/plugin composition
- plugins may return toolsets, skill dirs, and explicitly allowed capabilities
- global generalist flag list is intentionally closed
- FileSystem and Knowledge already exist in core
- `quant-decision` does not request Shell or RepoContext
- BMAD build entries are Skills whose workflow requires command execution

## Pydantic AI Harness

Harness:
https://pydantic.dev/docs/ai/harness/

You.com:
https://pydantic.dev/docs/ai/harness/youdotcom/

Announcement:
https://pydantic.dev/articles/youdotcom-pydantic-ai-harness

Researcher:
https://pydantic.dev/docs/ai/harness/researcher/

Coder:
https://pydantic.dev/docs/ai/harness/coder/

FileSystem:
https://pydantic.dev/docs/ai/harness/filesystem/

Shell:
https://pydantic.dev/docs/ai/harness/shell/

Releases:
https://github.com/pydantic/pydantic-ai-harness/releases

Relevant version fact:
- YouSearch and YouResearch were added before the repository's current Harness 0.29 line.
- first try adding the You.com extra without broadening the current minor constraint.

## Why You.com

YouSearch:
- web survey
- relevant excerpts
- full-page fetch on demand
- freshness/domain controls
- structured source metadata

YouResearch:
- cited answer
- multi-step research
- finance-tuned research

The profile intentionally chooses one open-web provider to avoid duplicate web tool names.

## Why not Coder in this profile

Harness Coder bundles codebase filesystem, shell, repository context, planning, delegation and context controls.

That is a different authority class from a general knowledge-work bot.

A future supervisor-only build deployment may reuse Coder or a narrower composition, but it should not be silently mixed into General Knowledge Worker.
