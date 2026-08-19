# ZUAEF Agent Core v0.1.1

A deliberately thin PydanticAI core: one outcome-owning agent, explicit Capability/Toolset composition, deferred Skills, bounded runs, file-native artifacts, evidence-first knowledge, bounded tool outputs, durable step evidence, and native approval for side effects.

## v1.1 in one sentence

Keep the loop thin, but make long-running work inspectable and recoverable enough to trust: **spill oversized tool results, persist step/tool-effect evidence, require native approval for external/destructive effects, and write one machine-readable receipt per run.**

## Architecture

```text
User Surfaces
CLI / Telegram
       |
       v
Surface Gateway                # transport, authorization, session binding,
       |                       # approval presentation, routing state
       v
Profile Composition            # build_profile_agent / frozen CompositionSnapshot
       |
       v
one PydanticAI Agent
       |
       v
Toolsets / Skills / Capabilities
       |
       v
Pause / Resume / Verification  # native approval, shared continuation seam,
       |                       # host-verified effects
       v
Artifacts + Knowledge + Receipts
```

> Gateway does not own an agent loop. It translates external interaction into the same ZUAEF runtime used by the CLI.

```text
workspace/                    # model-facing filesystem root
  artifacts/
  knowledge/
    index.md
    sources/
    concepts/
  inbox/telegram/             # gateway-downloaded attachments (workspace-relative)

.zuaef-state/                 # runtime-only sibling; not model-writable
  steps/                      # append-only step events + snapshots + tool-effect ledger
  tool-results/               # full spilled tool payloads; model receives a handle/preview
  receipts/                   # one compact JSON run receipt
  gateway.sqlite3             # gateway routing state only: sessions, cursors, token hashes
```

## Interactive Business Gateway (v0.3)

`zuaef-agent gateway start --surface telegram --profile wordpress-operator`
runs one blocking foreground process: Telegram long polling → normalized
`InboundEnvelope` → `GatewayService` → `build_profile_agent` →
`execute_run()`. A paused run renders an Approve/Deny card in Telegram; the
callback resolves an opaque approval token and resumes through the same
`resume_paused_run` seam the CLI uses. Every external write (WordPress
create/update/publish) is approval-gated by PydanticAI native
`requires_approval` and settles in the `RunReceipt`'s verified tool effects.

Required environment: `ZUAEF_TELEGRAM_BOT_TOKEN`,
`ZUAEF_TELEGRAM_ALLOWED_USERS` (comma-separated user ids — empty means fail
closed), `ZUAEF_WORDPRESS_USERNAME`, `ZUAEF_WORDPRESS_APP_PASSWORD`. The
`wordpress-operator` profile carries non-secret config only; credentials
never enter a profile, snapshot or receipt.

## Phase 2 — the product seam is one deployment (`stillevo-fde`)

Phase 2 does not expand the harness. It finishes the product: a real bound
customer conversation enters the Gateway, the one FDE agent owns a Case,
sees only a compact initial business surface, loads the relevant business
domain when needed, writes/updates from real customer material, respects
approval/side-effect policy, and carries the user's next-turn correction.

### Capability lifecycle: available ≠ authorized ≠ loaded ≠ invoked

```text
available   the upstream primitive exists in the platform (Memory, ToolSearch,
            SubAgents, WebSearch, … — this repo consumes, never reimplements)
authorized  effective deployment policy = host ceiling ∩ profile [generalist]
loaded      the model-visible tool surface at this step (progressive: deferred
            domains are hidden until ToolSearch discovers them)
invoked     a tool actually called this run
```

Profiles request capabilities in a `[generalist]` section; the host ceiling
(`AgentSettings` / `ZUAEF_ENABLE_*` env) is the outer guard. The composition
layer freezes `host ∩ request` into the `CompositionSnapshot`, so a
continuation after pause/resume reproduces the exact deployment authority
even if the profile file changed. Shell/RepoContext stay unauthorized in
business deployments.

### Business progressive disclosure

`profiles/stillevo-fde.toml` composes the FDE deployment: the Case orientation
plugin stays eager; client-service, ACE writing, budget and WordPress are
`defer_tools = true`, so their real tool schemas are hidden from the model
until it discovers the relevant domain through ToolSearch (`search_tools`).
Available ≠ loaded: on a writing task the model loads only the writing
domain; budget/WordPress stay dormant unless that work is actually requested.

### Gateway → Case binding (supervisor only)

A channel/thread is mechanically bound to one Customer Case — the model never
guesses identity. Two supervisor entrances write the same durable mapping:

```bash
# automation/scripts:
zuaef-agent gateway bind-case \
  --surface telegram --user 42 --channel 42 \
  --case stillevo-beauty --state-root ./.zuaef-state
```

```text
# the Telegram console (Phase 3A) — deterministic control, never the model:
/case              → card + buttons (Cases / New conversation / Unbind)
/cases             → recent cases as one-tap bind buttons
/case <id>         → bind now
/unbind            → remove the binding
```

Control commands and their inline buttons are pure gateway logic: they never
start a run, never consult the model, and ride a self-describing `zc:` callback
channel separate from approval tokens. Binding/unbinding is refused while a
run waits for approval — a resumed run must keep the Case it was bound to.

Conversation identity and Case identity stay separate: `conversation_id` is
the dialogue lifecycle, `case_id` the business work item; `/new` (and the New
conversation button) rotates the conversation but keeps the Case. Every
inbound run threads the bound `case_id` into `CoreDeps`, the receipts record
it, and the real Case tools reject any operation naming a different Case (a
cross-case `send_to_customer` is a blocked run, not an operator queue entry).

### Interaction contract: outcome-first, approval only at the boundary

Two rules govern every conversation turn:

1. **Work process is never approval-gated.** Reading, thinking, research,
   writing, revising and saving working artifacts are internal work. Only a
   true External Effect — sending to the customer, publishing, mutating
   production data — pauses for approval (`send_to_customer` stays the single
   customer-visible gate).
2. **Write/revise/analyze defaults to presenting the result to the current
   user** (the supervisor), not to delivering it to the business object. The
   full final text rides in the terminal `deliverable` and is rendered as the
   main reply; audit details (counts, effects, run internals) live in
   `/status` and the receipts.

A customer-visible send therefore looks like: "改写这篇文章" → the rewritten
article as the bot's reply, zero buttons; "发给客户" → an approval card that
shows the outbound draft content itself — the operator never approves unseen
text.

### Authoritative Phase-2 proof

```bash
uv run python tools/fde_two_turn_proof.py
```

runs the Golden Outcome (two literal turns, no hidden constraint reinjection)
through `GatewayService + profile=stillevo-fde + bound real Case + real model
+ real StepPersistence + real ACE materials`, then exercises approve/deny on
a customer-visible send through the shared `resume_paused_run` seam. Output
covers the model-visible surface before/after domain load, invoked/dormant
domains, Case reads/writes, artifacts, no-price scan, publish calls, pause/
approval receipts, and the Turn-2 prior-history proof. `--no-model` runs the
deterministic surface + approval evidence only.

The pre-Phase-2 FDE CLI proof (`examples/fde_loop.py`) is historical/
diagnostic only — the Gateway/stillevo-fde seam is the product authority.

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

The platform ABSORBS host primitives from PydanticAI / pydantic-ai-harness
(Memory, ConversationSearch, ToolSearch, WebSearch/WebFetch, planning, skills,
sub-agents, native approval, step persistence). This project does not contain
custom reimplementations of them:

- Agent registry or one agent class per business domain.
- Graph runtime or custom state machine.
- Custom checkpoint/durable runtime.
- A custom long-term-memory service (upstream Memory is used) — nor a second
  memory database alongside the Case store.
- Vector database/RAG service (lexical retrieval stays; add embeddings only
  after a measured failure).
- Custom multi-agent/team orchestration framework (upstream SubAgents
  capability is available; the one FDE Agent owns the outcome).
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

## Second vertical slice: EMTB budget (example2)

The production seam — `build_agent(settings, extra_toolsets=[...])` — is now
exercised by a second business domain without touching core.
`examples/budget_lib/` is a faithful extraction of zesenticai's finance_agent
deterministic commands (bilingual CSV parsing + summary / variance /
consistency / health / query / significant-change); `examples/budget_toolset.py`
adapts it to a PydanticAI `FunctionToolset`; `examples/budget_case.py` drives one
real core agent over one real EMTB budget CSV (Chinese + English headers).

Final proof run:

```text
model           deepseek-v4-flash
run             2639102722814111b9b9be253a50d8be
receipt         completed
artifacts       artifacts/…/emtb_budget-report.md (host-verified)
machine checks  all PASS
unknown         none
```

What this proved (and did not prove):

- A deterministic business domain composes through `extra_toolsets` with zero
  core changes; the host still owns artifact ownership (SHA-256 snapshot) and
  receipt settlement.
- Tool-effect refs: the host settles completed effects automatically; the
  slice's instructions teach the model to declare only `artifact:` refs.
- Not proved: multi-toolset composition, budget caps, pause/resume inside a
  budget run. Those stay deferred until a real run needs them.

## Stage 6A: EMTB budget as the second plugin (generalization proof)

The budget domain now ships as an installed distribution exposing the
`zuaef-emtb-budget` `zuaef.plugins` entry point
(`plugins/zuaef-emtb-budget/`), enabled by the example profile
`profiles/emtb-budget.toml`. `examples/budget_case.py --profile emtb-budget`
runs the real model through the Plugin Composition Layer — resolve profile →
freeze CompositionSnapshot → compose → execute — with the snapshot threaded
into the receipt.

Stage 6A proof run (`--profile emtb-budget`):

```text
model           deepseek-v4-flash
run             8a8a5b539cb14144994298edd455f4a7
receipt         completed
composition     present (plugins=[zuaef-emtb-budget])
artifact        emtb_budget-report.md (host-verified)
machine checks  all PASS
unknown         none
```

CLI surface (real entry points, no imports until enabled):

```text
$ zuaef-agent plugin list
ace-writing         0.1.0
zuaef-emtb-budget   0.1.0
$ zuaef-agent plugin inspect zuaef-emtb-budget
id: zuaef-emtb-budget   version: 0.1.0   entry_point: zuaef_emtb_budget:create_plugin
$ zuaef-agent profile check emtb-budget --config-root <repo>
…composition_id d4fcb62e…  plugins=[zuaef-emtb-budget]
```

Zero core change: `core.py`, `runtime.py`, `composition.py` untouched (diff
verified). The direct-toolset path stays as proof evidence and the plugin
toolset is tool-for-tool identical to it (parity test).

## Next

The shared seam is now proven on two business slices: writing (task-local
composition, external ACE engine) and EMTB budget (`extra_toolsets` through
`build_agent`). The remaining open question from v1.1 is unchanged: is the core
generic enough for a third slice without touching core? Candidates: a
Hardware Scout / WordPress adapter (business adapter swap, no new machinery), or
a second runtime through the same seam.
