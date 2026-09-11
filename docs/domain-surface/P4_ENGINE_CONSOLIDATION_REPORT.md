# Quant P4 Engine Consolidation Report

| Field | Value |
|---|---|
| Status | P4_FULL_PASS (one non-blocking discovery observation) |
| Phase | P4 — Domain Engine Consolidation |
| Tested tree | local working tree @ `cf581e50b62e` + P0–P2.1 patches + P4 patches |
| P3 prerequisite | `P3_FULL_PASS` (recorded in `P3_QUANT_CANARY_REPORT.md`) |
| Model-visible surface | unchanged — no tool renamed, added, removed, or re-described |
| Root runtime | not retired — P6 remains gated |

---

## 1. BASELINE AUTHORITIES

| Operation | Authority before P4 | Duplicate implementation locations |
|---|---|---|
| frozen entry trigger | ad-hoc clause expression in several callers | `tools/quant_live_scan.py`, `tools/quant_trading_monitor.py`, `tools/quant_build_candidates.py` |
| remaining clause gaps / NEAR projection | `tools/quant_trading_monitor.clause_distances` | private formula only, but reused by symbol-context and cycle paths |
| position P&L mark | repeated expression in `tools/quant_trading_monitor.py` | live projection, exit-alert conditions, attention rows, closed-position settlement |
| forward-observation counts | `plugins/.../validation.py` for tools; `tools/quant_render_business_dashboard.py` parsed `forward.json` again | two independent traversals with two distinct settled views |
| positions projection | `tools/quant_trading_monitor._write_summary()` | single producer; readers consume artifacts |
| watchlist write | `plugins/.../watchlist.update_symbols_in()` | single write/read-back path |
| market context | `tools/quant_market_context.collect()` | single market-wide adapter |
| symbol context | `tools/quant_trading_monitor.py symbol-context` | single host op |
| strategy evaluation / market intel | isolated side-env scripts | single bounded subprocess each |

No new framework, registry, dispatcher, container, durable state or model-visible capability was
introduced. The P4 modules are plain stdlib-only Python functions.

---

## 2. DUPLICATIONS FOUND

1. **Frozen trigger clause (real duplication).** The same three-clause expression existed in the
   scan CLI loop, the monitor opportunity layer and candidate-builder timing classification.
2. **Clause-gap formula (single private authority).** Only the monitor owned it, but the
   symbol-context path and the cycle path depended on a private implementation with no shared
   owner; it moved to the domain package and the monitor kept a compatibility adapter.
3. **Position P&L arithmetic (real duplication).** Four in-module copies converted entry
   price/quantity/current price into a ledger mark.
4. **Forward observation traversal (real duplication).** `forward.json` was parsed by the
   validation engine for the model tools and again by the business dashboard for its formal
   `count`/`settled` counters. The two settled definitions are intentionally different:
   dashboard `settled_all_kinds` counts every observation with a d8 window (including SKIP);
   validation accounting `settled_executed` counts only EXECUTED observations. They now share one
   parser and one explicit projection so the distinction is named, not accidental.
5. **Positions projection.** Premise check found no second reconstruction: `_write_summary()` is
   the single live projector and canonical writer; `get_positions`, `get_trading_context` and the
   dashboard read the projected artifact. Result: `NO_CONSOLIDATION_JUSTIFIED`.
6. **Watchlist.** Premise check found one verified write path and its read-back; both
   `manage_watchlist` and `update_analysis_watchlist` delegate to it. Result:
   `NO_CONSOLIDATION_JUSTIFIED`.
7. **Market/symbol/evaluation/intel.** Premise checks found single authorities. Result:
   `KEEP CURRENT IMPLEMENTATION`.

---

## 3. ENGINES CONSOLIDATED

### 3.1 Scan Engine (`plugins/zuaef-quant/zuaef_quant/scan.py`)

Single production authority for:

- `entry_trigger(...)` — the frozen three-clause boolean;
- `entry_clause_gaps(...)` — normalized distance to each clause;
- `evaluate_entry(...)` — trigger + clause gaps + monitor NEAR-band projection.

Consumers:

- `tools/quant_live_scan.py` uses `entry_trigger` for its production trigger boolean;
- `tools/quant_trading_monitor.py` uses `evaluate_entry` for READY/NEAR and delegates its legacy
  `clause_distances(spec)` adapter to `entry_clause_gaps`;
- `tools/quant_build_candidates.py` uses `entry_trigger` for its ranking TRIGGER state;
- `tools/quant_v31.py` continues through `monitor.run_cycle` and therefore the same engine.

### 3.2 Trading Engine helpers (`plugins/zuaef-quant/zuaef_quant/trading.py`)

Single production authority for position mark arithmetic:

- `position_pnl(position, price, shares=None)`;
- `mark_to_market(position, price)`.

`tools/quant_trading_monitor.py` now uses these for the live position projection, exit-alert
conditions, attention rows and `Store.close_position()` settlement. The monitor remains the one
canonical ledger writer and live projector; `get_positions` / `get_trading_context` keep reading
the projection instead of recomputing P&L.

### 3.3 Validation projection (`plugins/zuaef-quant/zuaef_quant/validation.py`)

`forward_evidence_counts()` is the single parse/count projection of `forward.json`. It exposes
both settled views by name; `compute_validation_accounting()` now derives its observation counts
from it, and `tools/quant_render_business_dashboard.py` imports the same function for its formal
forward cards. This removed the dashboard's private parse while preserving its existing
`settled` semantics (all observation kinds) and the model tool's strategy-executed semantics.

### 3.4 What was deliberately not built

No `BaseQuantEngine`, `EngineRegistry`, `DomainEngineProtocol`, `ActionDispatcher`,
`QuantServiceContainer`, `EngineManager`, workflow DSL or global router. The scan/trading/validation
module names are ordinary import paths; the compatibility adapter in the monitor keeps the old
`clause_distances(spec)` signature because existing tests and the symbol-context path use it.

---

## 4. PRODUCTION AUTHORITY MOVED

| Operation | Production authority after P4 | Callers now importing authority |
|---|---|---|
| frozen entry decision | `zuaef_quant.scan.entry_trigger` | scan CLI, monitor, candidate builder |
| clause-gap / NEAR projection | `zuaef_quant.scan.entry_clause_gaps` / `evaluate_entry` | monitor cycle, symbol-context, future operator surface |
| position mark P&L | `zuaef_quant.trading.position_pnl` / `mark_to_market` | monitor live/alert/settlement paths |
| forward evidence counts | `zuaef_quant.validation.forward_evidence_counts` | validation accounting, dashboard |
| positions projection | `quant_trading_monitor._write_summary` (unchanged) | `get_positions`, `get_trading_context`, dashboard (readers only) |
| watchlist write | `zuaef_quant.watchlist.update_symbols_in` (unchanged) | `manage_watchlist`, legacy alias |
| market / symbol / eval / intel | unchanged single authorities | thin tool model surface |

---

## 5. LEGACY WRAPPERS REMAINING

Deliberate compatibility wrappers after P4:

- `tools/quant_trading_monitor.clause_distances(pullback, ratio, strength, price, spec)` maps the
  frozen `StrategySpec` onto `entry_clause_gaps`; it contains no formula.
- The semantic tools `get_trading_context` and `get_live_signals` remain callable, deferred
  compatibility surfaces. P4 did not rename, remove or re-describe them.
- Root side-env scripts remain executable entry points for the existing plugin resolution path.

P7 remains the phase that retires legacy model tools.

---

## 6. ROOT TOOLS STILL AUTHORITATIVE

Honest P6 boundary — the following production authority still lives in `tools/`:

| Root path | Remaining authority |
|---|---|
| `tools/quant_live_scan.py` | quote fetch, history-cache adapter, side-env CLI/stdout contract, network retry |
| `tools/quant_trading_monitor.py` | canonical trading-ledger writer, state summary, session CLI, symbol-context host op |
| `tools/quant_build_candidates.py` | candidate discovery/scoring/ranking |
| `tools/quant_market_context.py` | market-wide reality adapter |
| `tools/quant_market_intel.py` | single-symbol structured news adapter |
| `tools/quant_eval_qlib.py` | isolated evaluator invocation |
| `tools/quant_serve.py`, `quant_render_business_dashboard.py` | operator serving/rendering surfaces |

P4 reduced duplicated business semantics behind the semantic surface. It did not claim
`root tools retired`; P6 owns that migration.

---

## 7. PARITY TESTS

New guard: `tests/test_quant_scan_engine.py`.

- frozen entry truth table and exact boundary cases;
- clause-gap arithmetic parity with the monitor compatibility wrapper;
- NEAR-band evaluation;
- forward-observation count projection, including the distinct settled views and absent-state
  honesty;
- real-module identity checks: live scan, monitor and candidate builder hold the shared engine
  function objects rather than private copies;
- dashboard holds the shared validation count projection;
- position P&L and mark-to-market projection behavior.

Retained regression suites:

- `tests/test_quant_trading_monitor.py` — fixture READY/NEAR/WATCH sequence, semantic gate,
  SYSTEM_UNAVAILABLE, exit lifecycle, ack boundary, transaction lock;
- `tests/test_quant_validation_accounting.py` — observation/settlement/lifecycle counts;
- `tests/test_quant_semantic_surface.py` — narrow scope, defer flags, watchlist verified write;
- `tests/test_quant_watchlist.py` — one write path, scope isolation, prewarm contract;
- `tests/test_quant_business.py` — renderer forward cards, candidate scoring, universe rules;
- `tests/test_manifest_integrity.py` — delivery manifest.

Commands run:

```text
.venv/bin/python -m pytest tests/test_quant_plugin.py tests/test_quant_scan_engine.py \
    tests/test_quant_validation_accounting.py tests/test_quant_freshness.py \
    tests/test_quant_semantic_surface.py tests/test_quant_watchlist.py \
    tests/test_manifest_integrity.py -q
# 88 passed, 2 skipped

# pandas-dependent monitor/business/engine suites under the production side environment,
# with the pure-Python pytest runner supplied from the agent venv:
PYTHONPATH=.venv/lib/python3.13/site-packages .venv-quant/bin/python -m pytest \
    tests/test_quant_trading_monitor.py tests/test_quant_business.py \
    tests/test_quant_scan_engine.py -q
# 177 passed

.venv-quant/bin/python <fixture parity script: run_cycle READY/NEAR + close_position P&L>
.venv/bin/ruff check plugins/zuaef-quant/zuaef_quant/scan.py \
    plugins/zuaef-quant/zuaef_quant/trading.py \
    plugins/zuaef-quant/zuaef_quant/validation.py \
    tools/quant_live_scan.py tools/quant_trading_monitor.py \
    tools/quant_build_candidates.py tools/quant_render_business_dashboard.py \
    tests/test_quant_scan_engine.py
```

`test_quant_watchlist.py` is skipped in the default `.venv` because pandas is absent; it requires
both pandas and pydantic_ai, which live in separate environments. Its one-write-path and scope
semantics are additionally pinned by `tests/test_quant_semantic_surface.py` (passed) and the
watchlist module was not modified by P4. The real-model matrix below is the final integration
parity.

---

## 8. AFFECTED P3 CANARIES

Affected by Scan consolidation: Canary 3 (`get_signal_board`), Canary 4 (`run_live_scan`), and
legacy `get_live_signals` compatibility. Affected by position mark: Canary 2 (`get_positions`) and
Canary 8 (`get_positions` composition). Affected by validation projection: Canary 1
(`get_validation_status`).

The complete near-neighbor matrix was re-run after P4 because the semantic surface is frozen and
the final acceptance gate is not optional.

---

## 9. FULL P3 REGRESSION

Executed after all P4 code changes on the local tested tree through the
`GatewayService.handle()` + normalized Telegram `InboundEnvelope` + capture
`SurfaceAdapter` path, fresh `/new` + `/profile quant-decision` per canary,
real model `deepseek/deepseek-v4-flash-0731`, real Quant side environment and
real production workspace artifacts. Raw evidence:
`P4_QUANT_CANARY_RESULTS.json`.

| Canary | Expected | Actual tool sequence | Requests | Tool calls | Wall | Legacy broad | Generic escape | Expected hit | Execution |
|---|---|---|---|---:|---:|---:|---|---|---|---|
| 1 Validation | `get_validation_status` | `search_tools -> get_trading_context -> get_validation_status` | 3 | 3 | 48.1s | **extra read** | no | yes | completed |
| 2 Positions | `get_positions` | `search_tools -> get_positions` | 3 | 2 | 15.2s | no | no | yes | completed |
| 3 Signal board | `get_signal_board` | `search_tools -> get_signal_board -> get_signal_board` | 4 | 3 | 48.1s | no | no | yes | completed |
| 4 Explicit scan | `run_live_scan` | `search_tools -> run_live_scan` | 3 | 2 | 55.3s | no | no | yes | completed |
| 5a Watchlist add | `manage_watchlist(add)` | `search_tools -> manage_watchlist` | 3 | 2 | 13.4s | no | no | yes | completed |
| 5b Watchlist remove | `manage_watchlist(remove)` | `search_tools -> manage_watchlist` | 3 | 2 | 12.1s | no | no | yes | completed |
| 6 Symbol | `get_symbol_context` | `get_symbol_context` | 2 | 1 | 122.6s | no | no | yes | completed |
| 7 Market-wide | `get_market_context` | `search_tools -> get_market_context` | 3 | 2 | 161.3s | no | no | yes | completed |
| 8 Compositional | market + positions | `search_tools -> get_market_context -> get_positions` | 3 | 3 | 166.5s | no | no | yes | completed |

Aggregate:

```text
EXPECTED TOOL REACHED:   9/9
GENERIC ESCAPES:         0
EXECUTION FAILURES:      0
LEGACY BROAD SUBSTITUTE: 0
LEGACY BROAD EXTRA READ: 1/9 primary runs (Canary 1)
```

### Non-blocking discovery observation — Canary 1

The primary Canary 1 trajectory called the deferred broad `get_trading_context`
once before calling the expected narrow `get_validation_status`. The expected
tool was still reached, the narrow tool produced the terminal answer, no
generic escape or broad substitution occurred, and no execution failure
followed. This is model-side discovery variance inside the frozen P2.1/P3
surface, not a P4 interface leak: P4 changed no tool name, description,
defer flag, capability list or profile topology, and the deterministic surface
tests freeze those facts.

Canary 1 was repeated to characterise the variance rather than hide it. Across
the recorded primary + repeat attempts, the expected `get_validation_status`
path was reached every time; some attempts were clean and some added one extra
`get_trading_context` read. The variance is non-blocking
for P4 because it is orthogonal to engine consolidation and does not replace
the expected narrow path. It remains a candidate for a future surface-quality
task, but it is not a P4 code change.

### Performance/requests

P4 did not aim at model-performance improvement. Request counts stayed in the
expected 2–4 range; Canary 3 added one duplicate narrow call and Canary 6/7/8
showed the same order of magnitude as the P3 record despite live-model and
network variance. No P4-induced tool sequence or payload change was observed:
the expected semantic path was reached in every canary and the engine changes
were invisible to the model.

### Watchlist restoration

The isolated canary scope `p4gw-canary-watchlist` was restored to `[]` by the
5a/5b pair; the runtime scope file was then removed. No production scope or
candidate-pool state was touched.

---

## 10. DELETED CODE

No file was deleted in P4. Deleted duplicate authority:

- three live copies of the frozen trigger expression;
- four copies of position P&L arithmetic;
- one private clause-gap formula (replaced by adapter + engine);
- one dashboard-private `forward.json` count traversal;
- two pre-existing monitor lint defects surfaced by the changed import block/ruff run
  (`market_date_of` unused import; unnecessary `int(len(...))` casts), with no behavior change.

No semantic tool, capability, profile or durable state was removed.

---

## 11. REMAINING DUPLICATION

- `market_phase()` remains a documented stdlib mirror between the monitor and the read-only
  renderer. It is a session-clock projection, not a scan/position/validation business authority,
  and P4 deliberately did not create a session engine for it under STOP-4.
- Root side-env scripts still contain production data plumbing (fetch, parse, render) pending P6.
- Engine boundaries are modules/functions, not classes. Future consolidation should extend the
  existing module authorities only when a real duplicate caller appears.

---

## 12. P5 READY?

**YES for deterministic engine work.** P4 now exposes callable scan/position-mark/validation
projections that a future operator CLI can share. P5 must still not create a Core domain command
registry and must not change the semantic tools. P6 owns moving root side-env scripts under the
domain owner; P5 can build the operator surface on top of the shared engine without treating P4 as
retirement of the root scripts.

## 13. P6 READY?

**NOT YET.** Root `tools/` still holds production runtime authority listed in §6. P4 reduced root
dependence for the duplicated business semantics but did not migrate quote/history fetch, the
canonical writer, evaluator or operator surfaces. P6 must separately prove those moves and preserve
the trading-ledger single-writer guardrail.

---

## 14. Gate Status

| Gate | Status | Evidence |
|---|---|---|
| A Semantic surface frozen | PASS with non-blocking observation | P3 matrix re-run: expected tools 9/9, generic escapes 0, no broad substitution; one extra deferred broad read recorded and characterised in §9 |
| B Single scan authority | PASS | `zuaef_quant.scan.entry_trigger/evaluate_entry` shared by CLI, monitor, builder |
| C Single position projection | PASS (NO_CONSOLIDATION_JUSTIFIED) | monitor remains one writer/projector; readers consume artifact; P&L arithmetic now one authority |
| D Single validation projection | PASS | `forward_evidence_counts` used by both validation accounting and dashboard |
| E Single watchlist write path | PASS (NO_CONSOLIDATION_JUSTIFIED) | `watchlist.update_symbols_in`; aliases delegate; verified read-back |
| F No behavioral drift | PASS | parity tests, deterministic surface/scope tests, and full P3 matrix; outcomes completed with the expected narrow tool path and preserved freshness/unknown semantics |
| G No new framework | PASS | plain modules; no registry/dispatcher/workflow/container |
| H No new model complexity | PASS | no tool added/renamed/re-described; defer flags unchanged |
| I Production authority reduced | PASS | four duplicate authorities replaced by shared engine modules |
| J Full regression | PASS | targeted engine/parity suites + manifest/integrity + lint + full real-model P3 matrix (`P4_QUANT_CANARY_RESULTS.json`) |

---

## 15. Completion Report

```text
TREE TESTED:          cf581e50b62e + local P0–P4 patches
P4 ENGINE GATES:      B–I PASS (single scan / position mark / validation authority, no framework,
                      no model-surface change, authority reduced)
P3 MATRIX:            expected tool path 9/9, generic escapes 0, execution failures 0
LEGACY BROAD:         0 substitutions; 1 non-blocking extra read in Canary 1 primary run
AFFECTED PARITY:      scan (C3/C4), positions+mark (C2/C8), validation counts (C1) all pass
REQUESTS/TOKENS:      recorded in P4_QUANT_CANARY_RESULTS.json
ROOT TOOLS RETIRED:   NO (P6 still gated)
P5 READY:             YES (shared deterministic engines are callable)
P6 READY:             NOT YET (root side-env production authority remains)
P4 FAILURE CLASS:     none for engine consolidation; Canary 1 discovery variance is non-blocking
P4 VERDICT:           P4_FULL_PASS with one non-blocking discovery observation
```
