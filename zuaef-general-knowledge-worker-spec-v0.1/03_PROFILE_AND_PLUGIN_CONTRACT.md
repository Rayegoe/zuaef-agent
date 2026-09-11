# Profile and Plugin Contract

## Profile

File:
`profiles/general-knowledge-worker.toml`

Required generalist request:
- `tool_search = true`
- `memory = true`
- `conversation_search = true`
- `context_controls = true`
- `subagents = true`
- `web_search = false`
- `web_fetch = false`
- `shell = false`
- `repo_context = false`

Reason:
- search comes from the plugin
- code/deploy authority stays outside this profile

## Plugin

Package:
`plugins/zuaef-knowledge-worker`

Entry point:

`knowledge-worker = "zuaef_knowledge_worker.plugin:build_plugin"`

Bundle:
- capabilities: YouSearch, optional YouResearch
- toolsets: DocumentTools
- skill dirs: plugin-local Skills

Profile must set:
`allow_capabilities = true`

## Config contract

Allowed:
- `search_results: int` — 1..20
- `search_mode: "highlights" | "full_page"`
- `page_chars: int`
- `research_enabled: bool`
- `research_effort: "lite" | "standard" | "deep" | "exhaustive"`
- `finance_effort: "deep" | "exhaustive"`
- `document_chunk_chars: int`
- `document_max_bytes: int`
- `output_language: str`

No credential-like key is allowed.

## Structured source projection

YouSearch / YouResearch expose structured source metadata.

ZUAEF should preserve it at the host/presentation boundary where practical.

Suggested source record:

```json
{
  "title": "source title",
  "url": "https://...",
  "tool": "web_search|answer|research|finance_research",
  "run_id": "..."
}
```

Do not create a second source database.

## Capability Truth behavior

Prefer deriving execution truth from composed capabilities/toolsets instead of maintaining a parallel manual feature list.

Behavioral acceptance:
- if repo mutation tools do not exist, the bot does not claim repo mutation
- if deployment tools do not exist, the bot does not claim deployment
- if a Skill exists but cannot execute, the bot states the limitation accurately
