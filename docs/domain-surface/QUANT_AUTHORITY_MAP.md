# Quant Authority Map

| Field | Value |
|---|---|
| Status | P6 shadow product layer retired — `tools/` contains developer/audit/benchmark tooling only; zero root production authority and zero root compatibility wrappers |
| Baseline | `main@cf581e5` plus P2/P2.1 surface, P3 canary, P4 engine consolidation, P5 operator surface, P5.8/P5.9 authority extraction and P6 retirement |
| Date | 2026-09-12 |

Allowed classes:

```text
PRODUCTION_ENGINE   deterministic business logic that production depends on
REALITY_ADAPTER     external data / service / file adapter
MODEL_SURFACE       model-visible tool, instructions or deferred skill
OPERATOR_SURFACE    CLI / timer / daemon / renderer / service entry
BENCHMARK           proof, audit, replay, benchmark or diagnostic script
MIGRATION           temporary compatibility, vendored upstream, packaging
DELETE_CANDIDATE    no current authority and no required reference value
```

No `misc`, `utility` or `legacy-but-maybe-useful` classes are allowed. The goal is to make duplicate
authority, mixed responsibility and shadow runtime visible before any move.

---

## 1. Root `tools/quant_*` final classification (P6)

P6 starts from `PRODUCTION_AUTHORITY count = 0` and ends with zero unjustified
compatibility wrappers.  The six P5.9 wrappers and the four P5.8 wrappers were
deleted after their last code/doc/deployment/test callers migrated to the
plugin modules.

### Deleted compatibility wrappers

| Former path | Former wrapper target | Why deleted |
|---|---|---|
| `tools/quant_core.py` | `zuaef_quant.quant_core` | developer-tool/test imports migrated; no runtime or deployment caller |
| `tools/quant_live_scan.py` | `zuaef_quant.scan_sidecar` | tests and developer tools migrated; production uses the module |
| `tools/quant_trading_monitor.py` | `zuaef_quant.monitor` | systemd migrated to `.venv-quant/bin/python -m zuaef_quant.monitor session` |
| `tools/quant_telegram_bridge.py` | `zuaef_quant.bridge` | no caller; systemd already uses `zuaef-quant bridge once` |
| `tools/quant_market_context.py` | `zuaef_quant.market_context` | Agent toolset uses the module; tests migrated |
| `tools/quant_market_intel.py` | `zuaef_quant.market_intel` | Agent toolset uses the module; tests migrated |
| `tools/quant_build_candidates.py` | `zuaef_quant.candidates_sidecar` | candidate refresh uses the module; tests/docs migrated |
| `tools/quant_eval_qlib.py` | `zuaef_quant.eval_sidecar` | Agent toolset uses the module; tests/docs migrated |
| `tools/quant_render_business_dashboard.py` | `zuaef_quant.dashboard.render` | operator CLI uses `-m`; tests/docs migrated |
| `tools/quant_serve.py` | `zuaef_quant.dashboard.serve` | operator CLI/systemd use `zuaef-quant dashboard serve` |

### Retained engineering tooling

| Path | Final class | Production dependency |
|---|---|---|
| `tools/quant_anti_leakage_check.py` | BENCHMARK / AUDIT | none; imports `zuaef_quant` implementation directly |
| `tools/quant_fetch_universe.py` | DEVELOPER_TOOL / REALITY_PREP | none |
| `tools/quant_p05_reconcile.py` | BENCHMARK / RECONCILE | none |
| `tools/quant_p0_data_proof.py` | BENCHMARK / DATA PROOF | none |
| `tools/quant_pit_audit.py` | BENCHMARK / PIT AUDIT | none |
| `tools/quant_render_dashboard.py` | DIAGNOSTIC / OBSERVATION RENDERER | none |
| `tools/quant_v31.py` | BENCHMARK / REPLAY | none |
| `tools/quant_validate_semantics.py` | AUDIT / DATA-SEMANTICS GATE | none; consumes scan artifacts, does not own runtime |
| `tools/quant_daily.sh` | DELETED (P6 closure) | zero production/deployment caller; superseded by M1 monitor + bridge + the Agent §5.2 path |
| `tools/quant/upstream/dump_bin.py` | DELETED | vendored code now owns its single copy at `plugins/zuaef-quant/zuaef_quant/dump_bin.py` |

The current production direction is:

```text
Agent Tool ──────► zuaef_quant.*
zuaef-quant ─────► zuaef_quant.*
systemd ─────────► zuaef-quant / -m zuaef_quant.monitor
tools/ (developer) ─► zuaef_quant.*  (when a proof needs the real implementation)
```

No root Quant file is a production runtime authority or a retained wrapper.

---

## 2. `plugins/zuaef-quant/` inventory

| Path | Current authority | Target authority | Migration status |
|---|---|---|---|
| `plugins/zuaef-quant/zuaef_quant/plugin.py` | MODEL_SURFACE | MODEL_SURFACE (composition + policy only) | narrow semantic tools added in P2; file remains composition owner |
| `plugins/zuaef-quant/zuaef_quant/quant_core.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P5.8 new** — shared quant mechanics (cache/history/rules/replay/spec) moved out of root tools |
| `plugins/zuaef-quant/zuaef_quant/scan.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P4 new** — single frozen entry decision + clause-gap projection shared by scan CLI, monitor and candidate builder |
| `plugins/zuaef-quant/zuaef_quant/scan_sidecar.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P5 new** — full live-scan sidecar; Agent tools and operator CLI execute this module |
| `plugins/zuaef-quant/zuaef_quant/monitor.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P5.8 new** — canonical ledger writer, monitor cycle/session, ack/skip and symbol-context host op |
| `plugins/zuaef-quant/zuaef_quant/bridge.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P5.8 new** — deterministic bridge tick and optional interpretation boundary |
| `plugins/zuaef-quant/zuaef_quant/continuity.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P5.8 new** — session clock + continuity verdict projection shared by bridge |
| `plugins/zuaef-quant/zuaef_quant/trading.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | **P4 new** — single position P&L mark projection shared by monitor live/alert/close paths |
| `plugins/zuaef-quant/zuaef_quant/toolset.py` | MODEL_SURFACE | MODEL_SURFACE split by semantic group (`toolsets/observe.py`, `operate.py`, `record.py`, `research.py`) | P2 added narrow tools; P4 did not change the model surface; physical split remains P6/P7 |
| `plugins/zuaef-quant/zuaef_quant/freshness.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | shared host derivation, keep (single authority) |
| `plugins/zuaef-quant/zuaef_quant/validation.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | P4 extracted the canonical `forward_evidence_counts` projection now consumed by `get_validation_status` and the dashboard |
| `plugins/zuaef-quant/zuaef_quant/watchlist.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | single watchlist write/read path, keep |
| `plugins/zuaef-quant/zuaef_quant/research.py` | PRODUCTION_ENGINE | PRODUCTION_ENGINE | scoped research state, keep |
| `plugins/zuaef-quant/zuaef_quant/__init__.py` | MIGRATION | MIGRATION | lazy import boundary required by side env; keep |
| `plugins/zuaef-quant/skills/quant-research/SKILL.md` | MODEL_SURFACE | MODEL_SURFACE (deferred skill) | keep, update only when semantics change |
| `plugins/zuaef-quant/pyproject.toml` | MIGRATION | MIGRATION | packaging boundary; revisit when engine moves |
| `plugins/zuaef-quant/README.md` | MIGRATION | MIGRATION | docs; update with operator migration |

---

## 3. P2 semantic surface added

The first slice deliberately did **not** move the 500 KB Quant implementation. It added thin
semantic affordances over the existing deterministic implementation:

| Tool | Implementation source today | Reality scope | Side effect |
|---|---|---|---|
| `get_signal_board` | canonical `state.json` + freshness | CANDIDATE_POOL | none |
| `get_positions` | `state.json` live projection / `positions.json` | TRADING_ACCOUNT | none |
| `get_validation_status` | `validation.py` accounting + PIT limitation | TRADING_ACCOUNT | none |
| `run_live_scan` | same scan script/engine as `get_live_signals` | CANDIDATE_POOL | scan-side state update only |
| `manage_watchlist` | same `watchlist.py` write path as legacy alias | user attention facts | local verified write |

Legacy compatibility retained, now deferred from resident surface (P2.1-B):

```text
get_trading_context        broad mixed compatibility projection (deferred)
get_live_signals           broad scan evidence (deferred; same engine as run_live_scan)
get_analysis_watchlist     list semantics compatibility (deferred)
update_analysis_watchlist  add/remove alias delegating to the same write path (deferred)
```

The legacy tools are not removed and remain callable/tested in P2.1, but they no longer gain a
resident model-visibility advantage. They may be retired only after the P3 real-model canary proves
the narrow surface preserves outcome quality.

---

## 4. Authority defects found (P1 findings)

1. **Shadow Product Layer (retired in P5.8/P5.9):** the plugin previously imported/resolved root
   `tools/quant_*`; production authority now lives in `zuaef_quant` and the P6 wrappers were deleted.
2. **Scan engine had duplicate clause expressions:** `get_live_signals` and `run_live_scan`
   already called the same script through `_live_scan_payload`, but the scan CLI, monitor cycle
   and candidate builder each re-derived the frozen trigger clause. P4 moved that decision to
   `zuaef_quant.scan`; the semantic tools remain ToolSearch/deferred.
3. **Gateway knows a Quant artifact convention:** `artifacts/quant/briefs/last-reply.json` is read by
   generic Gateway code. This is a documented surface/domain boundary defect, not something to fix
   with another Quant branch.
4. **Market data/renderer plumbing (retired in P5.9/P6):** dashboards, serving and bridge now run
   from `zuaef_quant`; root wrappers were deleted after the last caller migrated.
5. **The vendored qlib `dump_bin` upstream code lives in the package:** its single canonical
   copy is `plugins/zuaef-quant/zuaef_quant/dump_bin.py`; the root duplicate was deleted in P6.
6. **PIT/profitability limitation is a static host fact** exposed in `get_validation_status`; when the
   PIT audit status changes, that tool and the domain docs must change together.

---

## 5. P1 exit condition

P1 is complete when every current Quant file has one of the allowed classes, every production
call site has a target owner, and every shadow authority is named. This document is that inventory;
the P2 semantic surface, P3 canary and P4 engine consolidation are recorded below and in the
respective reports.

P3 real-model canary was executed and recorded in
`P3_QUANT_CANARY_REPORT.md` / `P3_QUANT_CANARY_RESULTS.json`; it passed with
expected semantic paths and zero generic escapes. **P4 is authorized and has now been executed**
(see `P4_ENGINE_CONSOLIDATION_REPORT.md`): the frozen entry decision, the position P&L mark and
the forward-evidence count projection each have one production authority. The P4 work kept the
semantic surface, legacy compatibility tool names, model discovery topology and all user-visible
behavior unchanged. P5/P6/P7 remain gated.

## 6. P4 consolidation refresh

| Operation | Production authority after P4 | Duplicate authorities removed |
|---|---|---|
| live scan trigger | `zuaef_quant.scan.entry_trigger` | inline clause expression in `quant_live_scan`, monitor cycle and candidate ranking trigger |
| scan clause-gap projection | `zuaef_quant.scan.entry_clause_gaps` / `evaluate_entry` | private formula in monitor `clause_distances` became an adapter only |
| position mark-to-market P&L | `zuaef_quant.trading.position_pnl` / `mark_to_market` | four in-module monitor P&L formulas (live projection, exit alert, attention row, settlement) |
| validation forward counts | `zuaef_quant.validation.forward_evidence_counts` | dashboard's private `forward.json` settled-count parse |
| positions projection | `zuaef_quant.monitor._write_summary` state projection (single writer/projector); read surfaces (`get_positions`, `get_trading_context`, dashboard) consume the artifact | P5.8 moved implementation to domain package; no duplicate projection found |
| watchlist write | `zuaef_quant.watchlist.update_symbols_in` | none found; all add/remove aliases already delegate to it |
| market context | `zuaef_quant.market_context collect()` (P5.9 single adapter) | none found; root wrapper deleted in P6 |
| symbol context | `zuaef_quant.monitor symbol-context` host op | P5.8 moved implementation; root wrapper deleted in P6 |
| strategy evaluation / market intel | `zuaef_quant.eval_sidecar` / `zuaef_quant.market_intel`, bounded subprocess | P5.9 moved implementation; root wrappers deleted in P6 |

Engine boundaries in P4 are ordinary Python modules/functions, not a framework: no
`BaseQuantEngine`, registry, dispatcher, container or workflow layer was introduced.

P5 adds the package-owned operator CLI described in
`P5_OPERATOR_SURFACE_MAP.md` / `P5_OPERATOR_SURFACE_REPORT.md`. P5.8 adds the monitor/bridge
implementation extraction described in `P5_8_PRODUCTION_AUTHORITY_REPORT.md`; P5.9 adds the
remaining six production owners and P6 retires the zero-caller root wrappers. None of these
changes model-visible tools, discovery topology or profiles.

`ROOT TOOLS REMAINING` (after P6): only developer/audit/benchmark/diagnostic tools and the
operator convenience shell. Every production runtime path is owned by `zuaef_quant` or the
`zuaef-quant` operator CLI; root wrappers were deleted because their callers migrated. See
`P6_SHADOW_LAYER_RETIREMENT_REPORT.md` for the final inventory.

### P4 parity methodology

P4's real-model canary matrix is recorded in
`P4_ENGINE_CONSOLIDATION_REPORT.md` / `P4_QUANT_CANARY_RESULTS.json`:
expected tool 9/9, generic escapes 0, execution failures 0, one non-blocking
extra deferred `get_trading_context` read in Canary 1 (repeat runs show
model-side discovery variance, not a P4 surface change).

Every migrated projection is guarded by same-input parity tests and real-module identity checks:

- `tests/test_quant_scan_engine.py` pins the entry truth table, gap projection, near band,
  forward count views and the fact that live scan / monitor / candidate builder hold the shared
  engine function objects (not private copies).
- Existing monitor fixture tests keep the same READY/NEAR/WATCH fixtures and expected event
  sequences; the monitor now obtains them through `evaluate_entry`.
- Existing validation-accounting tests keep the same observation/settlement counts; the dashboard
  forward test fixtures keep the same `count`/`settled` payload, now sourced from the shared
  `forward_evidence_counts`.
- `test_quant_semantic_surface.py` remains the surface/scope freeze gate; P4 changed no tool name,
  description, defer flag or payload scope.
