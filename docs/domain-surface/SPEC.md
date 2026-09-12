# ZUAEF Domain Semantic Surface Refoundation Spec

| Field | Value |
|---|---|
| Status | IMPLEMENTATION READY |
| Target | `Rayegoe/zuaef-agent` current `main` |
| Reference domain | Quant |
| Applicability | Any future ZUAEF domain |
| Date | 2026-09-11 |

> More affordances. Less machinery.

This spec is the domain-layer counterpart to
[`../architecture/NORTH_STAR.md`](../architecture/NORTH_STAR.md). The North Star owns
system/ownership boundaries; this spec owns the relationship between real domain capability,
model-visible semantic tools, and deterministic operator surfaces.

---

## Current implementation state in this repository

The first P2 slice has been implemented: `get_signal_board`, `get_positions`,
`get_validation_status`, `run_live_scan` and `manage_watchlist` are thin
semantic tools over the existing Quant implementation, deferred through
ToolSearch, with deterministic contract tests and bounded display vocabulary.

P2.1 closure is also implemented:

- `get_market_context()` exists and is discovered as the market-wide reality
  surface.
- Legacy broad/alias tools (`get_trading_context`, `get_live_signals`,
  `get_analysis_watchlist`, `update_analysis_watchlist`) remain callable and
  tested, but are now deferred compatibility-only; they no longer have a
  resident model-visibility advantage over the narrow surface.

P3 (real-model canary) has now been executed on the local tested tree through
the Gateway bridge seam and passed: **`P3_FULL_PASS`**. The record is in
[`P3_QUANT_CANARY_REPORT.md`](./P3_QUANT_CANARY_REPORT.md) with raw metrics in
[`P3_QUANT_CANARY_RESULTS.json`](./P3_QUANT_CANARY_RESULTS.json).

P4 (engine consolidation) was executed after that result. The frozen entry
decision, clause-gap projection, position mark arithmetic and forward-evidence
count projection now each have one production authority; semantic tools,
legacy compatibility names, defer flags and payload scopes are unchanged.
See [`P4_ENGINE_CONSOLIDATION_REPORT.md`](./P4_ENGINE_CONSOLIDATION_REPORT.md)
and raw matrix evidence [`P4_QUANT_CANARY_RESULTS.json`](./P4_QUANT_CANARY_RESULTS.json).
P4 reported one non-blocking model-side discovery observation (an extra
`get_trading_context` read in one Canary 1 attempt; expected narrow tool still
reached, no generic escape or substitution). P5 has since been executed (see
below); P6 (Shadow Product Layer retirement) is executed and closed; P7
(legacy tool deletion) is READY but not started. P4 did not redesign Runtime
or introduce a Domain
Framework / Action Registry / Workflow DSL.

P5 (deterministic operator surface) is now implemented: `zuaef-quant status |
scan | watchlist | monitor | dashboard | bridge` are owned by
`plugins/zuaef-quant`, make no model requests by themselves, and reuse the
same scan/watchlist/monitor/dashboard/bridge authorities as the Agent tools.
`zuaef_quant.scan_sidecar` is the scan authority; the P5 root wrapper was
retired in P6, and the dashboard/bridge systemd services use the operator CLI. See [`P5_OPERATOR_SURFACE_MAP.md`](./P5_OPERATOR_SURFACE_MAP.md)
and [`P5_OPERATOR_SURFACE_REPORT.md`](./P5_OPERATOR_SURFACE_REPORT.md) with raw
smoke evidence in [`P5_QUANT_SMOKE_RESULTS.json`](./P5_QUANT_SMOKE_RESULTS.json).
P5.8/P5.9 have since executed the production authority extraction: the monitor,
bridge, live-scan, shared quant mechanics, market context/intel, candidate
sidecar, evaluator sidecar and dashboard render/serve implementations now live
in `zuaef_quant`. See
[`P5_8_PRODUCTION_AUTHORITY_REPORT.md`](./P5_8_PRODUCTION_AUTHORITY_REPORT.md)
and [`P5_9_PRODUCTION_AUTHORITY_REPORT.md`](./P5_9_PRODUCTION_AUTHORITY_REPORT.md).
P6 has since retired the zero-caller compatibility wrappers; `tools/` now
contains developer/audit/benchmark tooling only (see
[`P6_SHADOW_LAYER_RETIREMENT_REPORT.md`](./P6_SHADOW_LAYER_RETIREMENT_REPORT.md)).
The P6 closure then deleted the last root product workflow (`quant_daily.sh`)
and removed the operator layer's reverse dependencies on the model-facing
layers (see [`P6_CLOSURE_REPORT.md`](./P6_CLOSURE_REPORT.md)). P7 (legacy
model-tool retirement) is READY but not started.

---

## 0. Executive decision

The current imbalance is:

```text
high internal implementation complexity
many domain scripts
many helper paths
many tests/proofs/compatibility paths

but:

user intent
    -> model-discoverable semantic tool
    -> real execution

is too thin.
```

Quant is the clearest case: it has real capability for market context, candidate scanning,
positions, trading ledger, strategy validation, PIT, market intelligence, watchlist, monitoring,
dashboards and Telegram bridging, while the Agent historically sees only a few highly aggregated
tools. The model then reuses those large tools, reads excess context, guesses semantics, or falls
back to shell/repo/code.

The relation must be inverted. Do not add more framework and do not expose more internal code. Make
the real capability enter the Agent through clearer, narrower, intent-oriented interfaces.

---

## 1. North Star

ZUAEF remains:

> Model owns intelligence. Harness owns execution. ZUAEF owns Minimal Reality Binding: the thinnest
> reliable connection between a concrete task, the reality materials the model must see, and the real
> actions available in the environment.

Therefore this refoundation does **not**:

- re-encode model intelligence;
- create a complete domain model in advance;
- create a Global Intent Router;
- create a Workflow DSL;
- design a complex future state system for possible problems;
- turn every internal function into a tool.

It optimizes:

```text
Intent -> Semantic Affordance -> Reality
```

For example:

```text
"今天市场为什么大跌?"
    -> get_market_context()

not:

"今天市场为什么大跌?"
    -> generic get_context()
    -> candidate pool
    -> symbol tools
    -> run_code
    -> repo script
    -> the model assembles reality by hand
```

---

## 2. Core problem: Semantic Surface Coverage

The problem is not simply "too few tools". A domain may have many internal capabilities while real
user intents have no first-class interface.

Examples:

- `策略验证到哪一步了?` should be `get_validation_status()`, not reading positions, READY, NEAR,
  alerts, validation, freshness and account state through one broad context.
- `把海康加入观察` should be `manage_watchlist(action="add", symbols=["002415"])`, not reading the
  whole trading context and finding the watchlist file.
- `重新扫描一下今天` should be `run_live_scan()`, not shell / repo / the retired root scan wrapper.

Internal code volume is not the product capability metric. The metric is:

> How many real user intents can directly land on a clear, controlled, real execution interface?

---

## 3. Architecture invariants

### INVARIANT 1 — Tool represents semantic affordance

A model-visible tool is an action whose invocation/arguments depend on semantic judgment.

Good: `get_market_context`, `get_symbol_context`, `run_live_scan`, `manage_watchlist`,
`evaluate_strategy`.

Bad: `read_json`, `load_cache`, `merge_rows`, `calculate_limit`, `write_temp_file`.

### INVARIANT 2 — Internal decomposition is not the external API

An implementation may fetch, normalize, validate, join, cache, calculate and persist internally.
Users and the model should see `get_market_context()`, not those steps.

### INVARIANT 3 — Rich surface does not mean rich framework

More semantic tools: yes. New Tool Registry Framework, Intent Router, Domain Action DSL, generic
Workflow Engine or Command Plugin Framework: no. Use existing PydanticAI `FunctionToolset`,
Capability, deferred tools and `ToolSearch`.

### INVARIANT 4 — Profile remains coarse routing

A profile answers which domain capabilities a deployment authorizes. It does not classify the
current sentence into an intent. Fine-grained discovery stays with the model + `ToolSearch`.

### INVARIANT 5 — Host operations remain deterministic

Timer scans, scheduled refresh, service start, dashboard serve, bridge ticks, health checks and
manual operator refresh do not start a model. They are the domain operator surface.

### INVARIANT 6 — Tool and CLI share implementation

One behavior must not have separate implementations in model tool, CLI, timer and dashboard. The
target is one deterministic domain engine with two access surfaces: semantic tool and operator
surface.

---

## 4. Target layer model

Each mature domain may have at most four layers:

```text
1. SEMANTIC SURFACE       model-visible tools; thin; intent-oriented
2. DOMAIN ENGINES         deterministic Python; reusable; no model; no user interaction
3. REALITY ADAPTERS       market API / DB / file / external service
4. OPERATOR SURFACE       CLI / timer / daemon / service; deterministic
```

Only Layer 1 is model-visible. Layer 4 is visible to humans and automation. Layers 2/3 are
implementation detail.

---

## 5. Tool admission rule

For any candidate action ask:

> If the host executed this automatically, could it make the wrong business decision because timing
> or arguments depend on semantic interpretation?

If **yes**, it is usually a model-visible semantic affordance (which symbol to analyze, whether to
evaluate a strategy, what to record, how to manage attention).

If **no**, it usually stays in the host (create directories, read cache, normalize codes, compute
change percentages, check file existence, refresh indexes, write receipts, update dashboard
snapshots).

A second test: would a user naturally ask for it with a business verb (look, analyze, scan, add to
watchlist, record fill, validate strategy, refresh)? If yes, it usually deserves a clear interface.

---

## 6. Forbidden tool designs

### Generic mega tool

```python
quant_action(action="market_context|scan|positions|watchlist|evaluate|...")
```

Forbidden: it hides an intent router inside a parameter.

### Generic context dump

```python
get_all_quant_context()
```

Forbidden as the default main interface: large payload + semantic ambiguity + scope confusion.

### Internal-step tools

`load_market_cache`, `normalize_quote`, `write_candidate_json`, `calculate_signal_clause` are not
model-visible tools.

### Script-name tools

`run_quant_v31`, `run_p05_reconcile`, `run_pit_audit_script` are not business language. The interface
must correspond to a real user intent.

---

## 7. Intent Surface Matrix

Before production admission, every domain maintains a lightweight engineering checklist. It is not
an ontology and not a runtime schema. See
[`QUANT_INTENT_MATRIX.md`](./QUANT_INTENT_MATRIX.md) for the Quant instance.

| User intent | Semantic tool | Reality source | Side effect |
|---|---|---|---|
| Current overall situation | `get_*_context` | current reality | no |
| Inspect one object | `get_*_context(id)` | reality source | no |
| Find related information | `search_*` | external source | no |
| Run analysis | `evaluate_*` | engine | bounded |
| Refresh / scan | `run_*` | engine | state update |
| Record user fact | `record_*` | durable store | local write |
| Modify attention set | `manage_*` | durable store | local write |

Record only intents with demonstrated demand. Do not invent interfaces to fill the table.

---

## 8. Quant target semantic surface

### Observe reality

- `get_market_context()` — bounded market-wide evidence for "why did the market fall today?"
- `get_symbol_context(symbol)` — single-symbol current context.
- `get_signal_board()` — READY/NEAR + freshness + scan metadata only.
- `get_positions()` — open positions + exit alerts + relevant current price fields only.
- `get_validation_status()` — validation age, observations, settlement, entries, exits, evidence
  status and PIT status only.
- `get_market_intelligence(...)` — bounded single-symbol/theme public information.

### Operate reality

- `run_live_scan()` — deterministic rescan of today's candidate universe; no shell/repo fallback.
- `manage_watchlist(action="add|remove|list", symbols=[...])` — bounded watchlist mutation.

### Evaluate

- `evaluate_strategy(spec)` — model chooses whether and with which bounded parameters; host owns
  data split, benchmark, cost, evaluation.

### Record

- `record_decision_brief(...)` — preserve.
- `record_trade_outcome(...)` — preserve, and only from an explicit human fill fact. Agent inference
  is forbidden.

---

## 9. Legacy surface retirement

`get_trading_context` and `get_live_signals` remain compatibility tools in the first phase. They are
resident but are no longer the default answer for a narrow intent.

Migration order:

```text
get_trading_context
    -> get_signal_board
    -> get_positions
    -> get_validation_status

get_live_signals
    -> run_live_scan
```

After a real-model canary proves the replacement, retire by:

```text
legacy tool
    -> hidden from model surface
    -> internal compatibility adapter
    -> delete when no caller remains
```

The goal is not more tools. It is: one user intent loads only the reality surface it actually needs.

---

## 10. Progressive disclosure

Do not inject all Quant tools at once. Use existing `ToolSearch` / `defer_loading` and semantic
groups:

```text
OBSERVE   get_market_context, get_symbol_context, get_signal_board,
          get_positions, get_validation_status
RESEARCH  get_market_intelligence, evaluate_strategy
OPERATE   run_live_scan, manage_watchlist
RECORD    record_decision_brief, record_trade_outcome
```

This is a grouping label only. Do not create `ObserveManager`, `ResearchManager`, `OperateManager`.
Use multiple `FunctionToolset` instances or existing deferred-tool mechanics.

Tool descriptions must contain real user vocabulary, letting the existing CJK `ToolSearch` discover
the tool. Do not add a hand-written keyword router.

Examples:

- `get_validation_status`: 策略验证, 验证进度, forward evidence, 样本, 结算, 交易天数, 是否证明,
  是否有效, PIT.
- `manage_watchlist`: 自选, 观察, 关注, 加入, 移除, watchlist.
- `run_live_scan`: 扫描, 刷新, 重新跑, 今天信号, READY, NEAR.

---

## 11. Domain engine refoundation

As the semantic surface becomes richer, the internals must become simpler. Quant must stop the
relation:

```text
one user function ~ one independent repo-root Python script
```

Target concept layout (reuse existing modules where they already fit; never rewrite stable code
merely to match a directory picture):

```text
plugins/zuaef-quant/
  zuaef_quant/
    engine/       market.py scan.py trading.py research.py
    adapters/     market_data.py external_intel.py
    toolsets/     observe.py research.py operate.py record.py
    ops/          cli.py
    skills/
```

### Reality adapter rule

`market_data.py` may fetch quote/index/sector/history. It must not decide BUY/READY/crash cause.
`scan.py` owns deterministic strategy calculation. The LLM owns interpretation.

### Side environment

Keep `.venv-quant` isolation and heavy dependencies (`akshare`, `qlib`). The current
`plugin -> repo root -> dozens of scripts -> subprocess` chain should converge to a small number of
domain-owned sidecar entry points (`quant-sidecar market`, `quant-sidecar research`,
`quant-sidecar trading`). That sidecar is host-internal CLI; it is not a model tool.

### Root `tools/` policy

After migration, `tools/` may hold benchmark, migration, one-off maintenance, developer diagnostics
and proof scripts. It may not hold core trading-state writes, core market logic, main scan
implementation, primary business API, or production domain runtime.

---

## 12. Operator surface

A rich model tool surface also needs deterministic command coverage. Quant may provide its own:

```text
zuaef-quant status
zuaef-quant scan
zuaef-quant watchlist
zuaef-quant monitor
zuaef-quant serve
zuaef-quant bridge
```

These commands perform `0` model calls and call the same domain engine as the corresponding tool:

```text
Natural language -> run_live_scan() -> scan engine
systemd timer   -> zuaef-quant scan -> same scan engine
```

Do not add a Core Domain CLI registry (`zuaef domain register`, generic domain CLI plugin system).
If Quant needs a CLI, `zuaef-quant` owns it. If another domain does not need one, add nothing.

---

## 13. Generic domain template

A new domain does not start with "which classes do I build?" It starts with an Intent Inventory of
5–15 real user requests, then asks which need model judgment and which are host operations, and only
then forms the tool surface.

Default admission sequence:

```text
real user intent
    -> minimum reality interface
    -> semantic tool
    -> real execution
    -> repeated deterministic implementation discovered
    -> extract engine
```

Forbidden:

```text
build complete domain engine first
    -> build model
    -> guess how users will use it
```

---

## 14. Tool surface quality

A good semantic tool is simultaneously:

- **Narrow** — returns only what the current intent needs.
- **Real** — connects directly to the real business source.
- **Bounded** — output has a deterministic upper bound.
- **Discoverable** — name and description contain the user's natural language.
- **Honest** — missing stays missing.
- **Composable** — complex tasks may call 2–3 independent affordances.

Do not optimize for one tool call. `分析今天大跌并说明对持仓影响` may correctly use
`get_market_context()` + `get_positions()` and answer. What is wrong is
`get_everything()` / 12 internal implementation tools.

---

## 15. Implementation sequence

| Phase | Work |
|---|---|
| P0 | Baseline before refactor: `QUANT_INTENT_BASELINE.md` |
| P1 | Authority inventory: `QUANT_AUTHORITY_MAP.md`; no code movement |
| P2 | Introduce semantic tools first, using current implementation through thin adapters |
| P3 | Real-model surface canary over the intent matrix |
| P4 | **Executed** — consolidate domain engines behind the P3-proven interface (report + raw canary evidence) |
| P5 / P5.8 | **Executed** — operator CLI plus monitor/bridge/scan/core production authority moved into `zuaef_quant` |
| P6 | **Executed + closed** — Shadow Product Layer retired; root daily workflow deleted; operator layer neutral (closure report) |
| P7 | READY (not started) — retire legacy model tools using the P7 caller baseline in `P6_CLOSURE_REPORT.md` |

P2 must not move 500 KB of Quant code first. Prove the interface, then refactor the implementation.

---

## 16. Acceptance gates

- **A — Market intent:** `分析今天A股大跌原因` discovers `get_market_context`; normally no repo
  tools, shell or generic file exploration.
- **B — Narrow validation intent:** `策略现在验证到什么程度?` discovers `get_validation_status`
  and does not default-load positions/READY/NEAR/watchlist/market context.
- **C — Position intent:** `我现在持有什么?` discovers `get_positions`; no broad trading context
  needed.
- **D — Explicit scan:** `重新扫描一下今天` discovers `run_live_scan`; no shell/repo script search.
- **E — Watchlist:** `把海康威视加入观察` discovers `manage_watchlist`; one bounded verified write.
- **F — Combined intent:** `分析今天A股为什么大跌，并告诉我对现有持仓有什么影响。` may use
  `get_market_context` + `get_positions`; compositional PASS, no mega-tool.
- **G — Operator parity:** `zuaef-quant scan` and `run_live_scan()` enter the same scan engine.
- **H — No Shadow Runtime:** production code does not depend on repo-root `tools/quant_*.py`
  business logic after migration.
- **I — Wrong domain:** a coding profile does not auto-route a Quant request just because Quant has
  a rich surface; it still fails fast. No cross-profile auto-routing.
- **J — Simple task remains simple:** richer ToolSearch inventory must not cause multi-round
  inventory, planning or tool browsing for one narrow question.

---

## 17. Metrics

Measure:

- **Intent Coverage:** number of golden intents with a native surface.
- **Path Depth:** model requests and tool calls from request to first real domain action.
- **Context Precision:** whether a narrow intent loads irrelevant business state.
- **Generic Escape Rate:** whether domain prompts fall back to shell/repo/generic file
  exploration/`run_code` for capability that already exists.
- **Authority Duplication:** same business action implemented in script, plugin, dashboard and timer.
- **Outcome Quality:** answers/execution must not regress as code is removed.

Do not use these as success proof: more tools, fewer files, prettier code, more abstraction, cleaner
classes, more uniform directories.

---

## 18. Tests

Suggested test files:

```text
tests/test_quant_semantic_surface.py
tests/test_quant_intent_discovery.py
tests/test_quant_operator_parity.py
tests/test_quant_authority_map.py
```

Minimum coverage: bounded output per tool; CJK discovery; narrow payload; scan parity; watchlist
mutation; validation-only payload; positions-only payload; no repo escape; no shell escape; legacy
surface compatibility.

Cross-domain proof: after Quant, use a small second domain (for example competitive intelligence
with `search_sources`, `read_source`, `produce_report`) and verify the method works without Core
changes. If it needs Core changes, stop and inspect the abstraction.

---

## 19. Explicit non-changes

Forbidden to add:

```text
Global Intent Router
Meta Agent
Domain Ontology
Domain State Machine
Workflow DSL
Generic Command Framework
Generic Domain Base Class
Generic Action Registry
Custom ToolSearch
Second Agent Runtime
Second Plugin System
```

Default do not modify `runtime.py`, `composition.py`, plugin ABI, approval model, receipt model or
Gateway session schema unless a real migration blocker is proven.

---

## 20. Required documentation and completion

Required docs:

```text
docs/domain-surface/
    SPEC.md
    QUANT_INTENT_MATRIX.md
    QUANT_AUTHORITY_MAP.md
```

Optional but required once P0 is executed: `QUANT_INTENT_BASELINE.md`.

Final completion reports must answer:

```text
INTENTS COVERED
TOOLS ADDED
LEGACY SURFACES RETIRED
DOMAIN LOGIC CONSOLIDATED
OPERATOR COMMANDS
GENERIC ESCAPES REMOVED
REAL-MODEL CANARY
CODE / AUTHORITY DELETED
REMAINING DUPLICATION
```

Not "how many classes were implemented" or "how many lines were added".

## Definition of Done

1. A high-frequency real intent has a short path: `Intent -> Semantic Tool -> Reality`.
2. Internal implementation no longer leaks through more scripts, special paths, Gateway branches
   or duplicated state.
3. The model sees business affordances, not implementation details.
4. The same reality operation has one owner and one implementation, callable by tool, CLI, timer and
   service.

Final principle:

> Do not build a complex domain world for the Agent; give it enough rich, thin business actions
> directly connected to reality.

Or:

> **More affordances. Less machinery.**
