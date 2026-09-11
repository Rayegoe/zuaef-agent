# Codex Master Prompt — Implement General Knowledge Worker v0.1

Implement this spec pack inside the existing `zuaef-agent` repository.

## Outcome

Ship `general-knowledge-worker` supporting:
- direct Q&A
- workspace document reading/search
- live web search
- URL reading
- multi-step research
- source-backed answers
- durable Knowledge reuse
- long artifacts
- truthful capability disclosure

without changing the one-agent core architecture.

## Mandatory reading

Read before edits:
1. `AGENTS.md`
2. root `README.md`
3. `src/zuaef_agent/core.py`
4. `src/zuaef_agent/config.py`
5. `src/zuaef_agent/profiles.py`
6. `src/zuaef_agent/composition.py`
7. `src/zuaef_agent/plugin_api.py`
8. `src/zuaef_agent/knowledge_capability.py`
9. `profiles/quant-decision.toml`
10. one representative production plugin
11. `.agents/skills/bmad-build/SKILL.md`
12. `.agents/skills/bmad-build-auto/SKILL.md`
13. this entire spec pack

## First principle

Do not build a new framework.

Reuse the existing ZUAEF core and released Pydantic AI/Harness primitives.

## Hard constraints

- no second agent loop
- no agent registry
- no second approval engine
- no new global generalist flag
- do not broaden `quant-decision`
- do not enable Shell or RepoContext in `general-knowledge-worker`
- no credential in profile config
- no vector database
- no custom web research engine
- no browser automation in this milestone
- preserve existing plugin composition
- preserve existing vertical profile behavior
- document I/O bounded and workspace-confined
- never claim an action ran unless the active tools actually ran it

## Search design

Use official Harness:
- `YouSearch`
- `YouResearch`

Do not compose conflicting core web tools in this profile.

Keep current Harness minor compatibility discipline. Do not do an unrelated broad upgrade.

## Document design

Thin deterministic layer only.

Supported:
- txt
- md
- json
- csv
- html
- pdf
- docx
- xlsx
- pptx

No OCR in v0.1.

## Development method

1. baseline
2. smallest working vertical slice
3. tests after each milestone
4. fix observed failures
5. preserve outcome-first behavior
6. prefer upstream capabilities
7. add regression tests for every field failure named here

## Final implementation report

Include:
- files changed
- profile composition
- plugin composition
- test results
- exact install/profile-check/run commands
- whether live You.com proof ran
- known limitations
- explicit Capability Truth test result
