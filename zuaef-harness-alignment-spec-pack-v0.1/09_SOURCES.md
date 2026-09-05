# Source Anchors

This pack was prepared against repository/upstream state inspected on 2026-09-05.

## ZUAEF

- `Rayegoe/zuaef-agent/AGENTS.md`
- `Rayegoe/zuaef-agent/pyproject.toml`
- `Rayegoe/zuaef-agent/src/zuaef_agent/core.py`
- `Rayegoe/zuaef-agent/src/zuaef_agent/composition.py`
- `Rayegoe/zuaef-agent/src/zuaef_agent/config.py`
- `Rayegoe/zuaef-agent/src/zuaef_agent/runtime.py`
- `Rayegoe/zuaef-agent/src/zuaef_agent/continuation.py`
- `Rayegoe/zuaef-agent/src/zuaef_agent/plugin_api.py`
- `Rayegoe/zuaef-agent/tests/test_generalist_activation.py`
- `Rayegoe/zuaef-agent/tests/test_writing_codemode_skills.py`
- `Rayegoe/zuaef-agent/.agents/skills/zuaef-runtime-coach/SKILL.md`
- `Rayegoe/zuaef-agent/docs/runtime-refoundation/CAPABILITY_ADMISSION.md`
- `Rayegoe/zuaef-agent/docs/runtime-refoundation/TASKS.md`

## Upstream

- `pydantic/pydantic-ai-harness/README.md`
- `pydantic/pydantic-ai-harness/pyproject.toml`
- Harness release v0.28.0 — released 2026-08-31
- Harness release v0.29.0 — released 2026-09-04

## Key upstream facts used

- Harness is the official capability/harness library built on PydanticAI.
- Its design is capability composition rather than a separate run-loop framework.
- Current upstream includes 50+ capabilities/harness stacks, including Coder, Researcher, FileSystem, Shell, Planning, SubAgents, DynamicWorkflow, CodeMode, ToolOutputLimits, Memory, ConversationSearch, Skills, RepoContext, Guardrails and PromptInjectionDefender.
- Current upstream project floor is `pydantic-ai-slim>=2.38.0`.
