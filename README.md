# ZUAEF Agent Core v0.1.1

A deliberately thin PydanticAI core: one outcome-owning agent, explicit Capability/Toolset composition, deferred Skills, bounded runs, file-native artifacts, evidence-first knowledge, bounded tool outputs, durable step evidence, and native approval for side effects.

## v1.1 in one sentence

Keep the loop thin, but make long-running work inspectable and recoverable enough to trust: **spill oversized tool results, persist step/tool-effect evidence, require native approval for external/destructive effects, and write one machine-readable receipt per run.**

## Architecture

```text
User / CLI / Telegram
        |
        v
  one PydanticAI Agent
        |
  +-----+---------------------------+
  | Capabilities                    | Toolsets / Skills
  |                                 |
  | FileSystem                      | business tools
  | ToolOutputLimits                | ingestion tools
  | StepPersistence                 | deferred domain skills
  | Knowledge                       |
  | Planning                        |
  +-------------+-------------------+
                |
                v
workspace/                    # model-facing filesystem root
  artifacts/
  knowledge/
    index.md
    sources/
    concepts/

.zuaef-state/                 # runtime-only sibling; not model-writable
  steps/                      # append-only step events + snapshots + tool-effect ledger
  tool-results/               # full spilled tool payloads; model receives a handle/preview
  receipts/                   # one compact JSON run receipt
```

## Why this shape

The core is intentionally not a business-agent registry. A business domain should normally arrive as a deferred Skill or a Toolset. A Capability is reserved for cross-domain behavior that legitimately bundles tools/instructions/hooks/settings. Knowledge remains Markdown + YAML frontmatter with source provenance; it is an OKF-compatible local profile rather than a fork of Google's reference agent.

v1.1 borrows operational invariants from mature harness designs without copying their runtime architecture:

- **Large tool output != model context.** Full payloads spill to `.zuaef-state/tool-results/`; the model progressively reads them through the Harness-provided `read_tool_result` tool.
- **Agent run != durable execution record.** `StepPersistence` owns step events, snapshots, and tool-effect records. `RunReceipt` is only a small index over those facts.
- **Model intent != authorization.** Business tools classify side effects and use PydanticAI's native `requires_approval=` / deferred-tool flow. There is no custom human-gate runtime.
- **Knowledge truth != current prompt.** Search/index/read remains progressive; do not load the whole knowledge corpus by default.

## Install

```bash
uv venv
uv sync
cp .env.example .env
```

Set a provider credential supported by the selected PydanticAI model. For an OpenAI-compatible endpoint, set `ZUAEF_OPENAI_BASE_URL`, `ZUAEF_OPENAI_API_KEY`, and `ZUAEF_COMPAT_MODEL`.

## Run

```bash
uv run zuaef-agent run "Read the available project material, identify the highest-impact next action, execute what is safe, and persist any long artifact."
```

The returned JSON includes `run_id` and `receipt`. The receipt points back to the step store, spill store, artifacts, knowledge updates, usage, and terminal summary.

## Native approval boundary

Do not build a second approval engine. Mark external/destructive tools with PydanticAI native approval:

```python
from pydantic_ai import FunctionToolset
from zuaef_agent.effects import EffectClass, requires_approval

woo = FunctionToolset()

@woo.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
def publish_product(product_id: int) -> str:
    ...
```

Default policy:

| Effect | Default |
| --- | --- |
| `observe` | automatic |
| `local_write` | automatic |
| `external_write` | approval required |
| `destructive` | approval required |

This is a model-action safety gate, not an authentication/authorization boundary. Sensitive tool bodies still enforce real credentials and permissions.

## Extension rule

Do not edit `core.py` to add a business domain. Compose it explicitly:

```python
from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent

settings = AgentSettings.from_env()
agent = build_agent(settings, extra_toolsets=[my_domain_toolset])
```

For instruction-heavy domains, add `.agents/skills/<domain>/SKILL.md`; the harness exposes each skill as a deferred capability instead of injecting every skill body into the initial prompt.

## Knowledge profile

`Knowledge` provides `list_knowledge`, `search_knowledge`, `read_knowledge`, and `write_knowledge`. The store writes `workspace/knowledge/**/*.md`, updates `knowledge/index.md`, rejects traversal outside the knowledge root, and records the `run_id` that generated each node. Run receipts can therefore list knowledge changes without a second database.

The current search is lexical on purpose. Add embeddings only after a measured retrieval failure.

## What v1.1 still does not contain

- Agent registry or one agent class per business domain.
- Graph runtime or custom state machine.
- Custom checkpoint/durable runtime.
- Long-term-memory service.
- Vector database/RAG service.
- Multi-agent/team orchestration.
- A generic source-ingestion framework.
- A custom steering/inbox runtime.

## Proven vertical slice

The **Harness-neutral Context Delivery Proof** has PASSED and is fixed repo fact,
not a design conclusion. `examples/writing_case.py` runs one real autonomous ZUAEF
agent against `examples/writing_toolset.py`, a thin adapter over ACE capabilities
(`list_materials`, `read_material`, `retrieve_exemplars`, `retrieve_knowledge`,
`check_claim`, `save_artifact`). The gate proved the running agent actually pulls
raw material, writing corpus, knowledge/evidence policy, and claim validation from
ACE — with receipts — rather than merely finishing an article.

Final proof run:

```text
model           deepseek-v4-flash
run             c58bf8cc62534cb3b991d47b6b5f404c
requests        22
receipt         completed
machine checks  all PASS
```

```text
Agent
  ↓ pull
ACE Context Engine
  ↓ receipts
ZUAEF Harness
  ↓ settlement
Artifact
```

Convergence fixes proven in this run:

- **Resume-safe quota** — `BudgetedWritingToolset` seeds per-run delivery counts from
  this run's ACE receipts (durable truth, read once per process); a rebuilt toolset
  after pause/crash/resume re-reads the receipts, so quota is never reset by process
  reconstruction.
- **Tool withdrawal** — exhausted tools are refused at call time AND withdrawn from
  the next model step's action space via `get_tools()`.
- **Run isolation** — budgets are enforced per `(run_id, tool)`; prior runs can no
  longer exhaust a new run's budget or satisfy its acceptance.
- **Probe non-authoritative** — the `integration_probe` can never trigger another
  save.

An earlier run (`article_id=vs-hw951-20260815`,
`run_id=bd023f87347f4ef98b50485c00c22ebe`) proved the basic writing + evidence gate
path and is retained as comparison evidence. CAP-1..CAP-4, the receipt requirements,
and the stop rule are fixed in `spec/writing-slice-gate.md`.

## Next

The contract is proven on one business slice via task-local composition
(`examples/writing_case.py` builds its own minimal Agent). The production
extension seam — `build_agent(settings, extra_toolsets=[...])` — is not yet
exercised by a business domain. Before adding any more Harness machinery,
**repeat the same contract with a second business slice or a second runtime
through the `extra_toolsets`/Skill seam, without touching core**, to test
whether the core is actually generic.
