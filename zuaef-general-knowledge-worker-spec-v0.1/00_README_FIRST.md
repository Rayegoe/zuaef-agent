# ZUAEF General Knowledge Worker Profile — Spec Pack v0.1

Status: READY FOR IMPLEMENTATION  
Target repository: `Rayegoe/zuaef-agent`  
Target runtime: existing ZUAEF Agent Core v0.1.1  
Primary surfaces: CLI / Telegram / Feishu  
Primary outcome: make ZUAEF a trustworthy general knowledge-work endpoint for ordinary Q&A, local documents, live web search, multi-source research, durable knowledge, and artifact delivery without adding a second agent runtime.

## 1. Why this exists

ZUAEF already has strong vertical deployments such as `quant-decision` and `stillevo-fde`, but it lacks a dedicated deployment whose product contract is:

> Ask a normal question, give it a file, give it a URL, ask it to search, compare, research, summarize, extract, or produce a durable knowledge artifact — and have the same ZUAEF runtime complete the work with the correct tools and evidence.

A real field conversation exposed a second gap. The bot described `bmad-build` / `bmad-build-auto` as if they were executable capabilities. In the repository they are Skills whose workflow requires command execution, while the active `quant-decision` profile does not authorize Shell or RepoContext.

This is not mainly an instruction-writing bug. It is a deployment-composition and capability-truth bug.

This pack establishes two rules:

1. **Knowledge work gets its own deployment profile.**
2. **Capability truth is mechanical:** the assistant must never claim it can execute an action merely because a Skill exists or a conceptual workflow is known.

## 2. Product shape

```text
User
  |
  v
CLI / Telegram / Feishu
  |
  v
Surface Gateway
  |
  v
profile = general-knowledge-worker
  |
  v
ONE existing ZUAEF Agent
  |
  +-- existing FileSystem
  +-- existing Knowledge
  +-- existing Planning
  +-- existing Skills
  +-- ToolSearch
  +-- Memory
  +-- ConversationSearch
  +-- Context controls
  +-- optional SubAgents
  |
  +-- zuaef-knowledge-worker plugin
        +-- YouSearch
        +-- YouResearch
        +-- generic document tools
        +-- knowledge-worker Skill guidance
```

No second loop. No agent registry. No new event bus. No duplicate approval system.

## 3. Main implementation decision

Create:

- `plugins/zuaef-knowledge-worker/`
- `profiles/general-knowledge-worker.toml`

The plugin returns released Harness capabilities plus a small deterministic document toolset.

Do **not** add a new global generalist flag. The current repository deliberately treats that list as closed. The new Harness capabilities are enabled through the plugin with `allow_capabilities = true`.

## 4. Search backend decision

For this profile, the default open-web backend is You.com through official Pydantic AI Harness:

- `YouSearch` for survey and page reading.
- `YouResearch` for cited direct answers and multi-step research.

The profile must **not** simultaneously enable the core `WebSearch` / `WebFetch` pair because of overlapping web tool names.

Recommended profile request:

```toml
[generalist]
web_search = false
web_fetch = false
tool_search = true
memory = true
conversation_search = true
context_controls = true
subagents = true
shell = false
repo_context = false
```

`YDC_API_KEY` stays in the host environment, never in a profile.

## 5. Scope v0.1

Included:
- ordinary direct Q&A
- current-information Q&A
- URL reading
- PDF/DOCX/XLSX/PPTX/HTML/Markdown/Text/CSV/JSON reading
- document search and comparison
- extraction and summarization
- multi-source research
- source-backed synthesis
- conversation lookup
- durable Knowledge read/write
- long artifact creation
- surface-neutral operation
- truthful disclosure of effective capability

Not included:
- autonomous source-code modification
- production deployment
- arbitrary host shell access
- changing quant strategy internals
- browser GUI automation
- OCR for image-only scans
- a new vector database
- a second RAG service
- a second research loop
- replacing ZUAEF Knowledge

## 6. Coding/deployment gap

Do not solve the earlier “I tell you a requirement, you modify and deploy it” need by turning this general knowledge profile into a shell-enabled coding bot.

That needs a separate supervisor-only deployment. See `08_SUPERVISOR_BUILD_FOLLOWON.md`.

The General Knowledge Worker may inspect requirements, research documentation, create specs and prepare handoffs, but must never claim code or deployment occurred unless the active deployment really owns those execution tools and they completed.

## 7. Acceptance headline

Release is complete when these literal tasks work through `general-knowledge-worker`:

1. `什么是 PIT？` → direct answer; no unnecessary web call.
2. `查一下 Pydantic AI Harness 最新的 Researcher 怎么组成` → web-backed answer with real sources.
3. `读 workspace/inbox/test.pdf，告诉我三个核心结论` → PDF handled through document tools.
4. `把 test.pdf 和 test.docx 对比，列出矛盾点` → cross-document comparison.
5. `深入研究这个主题，并保存一份 Markdown 报告` → multi-source research + durable artifact.
6. `帮我直接改 zuaef-agent 并部署` → does not pretend to have done so; states this profile lacks code/deploy execution and points to the supervisor-build seam.
