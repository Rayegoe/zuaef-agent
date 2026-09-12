# P7 Semantic Surface Report — Minimal Legacy Retirement

Status: **P7_PARTIAL_STOP — TRADING_CONTEXT_RETAINED_WITH_EVIDENCE**

Baseline: `5bb2ad653af3f8fbc79eff7c04fcf43e4c712472`
Raw evidence: `P7_CANARY_RESULTS.json`
Model: `deepseek/deepseek-v4-flash-0731`

P7.1 and P7.2 are complete. P7.3 migrated real prompt callers, but its
production E2 canary reproduced a broad fallback when the narrow position
projection contained no current position. The explicit stop rule therefore
keeps `get_trading_context` deferred and prevents P7.4 from starting.

## P7.1 — watchlist aliases

### CALLERS BEFORE

`get_analysis_watchlist` and `update_analysis_watchlist` had no production,
operator or prompt callers. They duplicated `manage_watchlist` list/add/remove
semantics and the same scoped store.

### CALLER MIGRATION / PRE-CANARY / RETIREMENT / POST-CANARY

Tests and instructions moved to `manage_watchlist`. Real-model W1/W2/W3 used
the production `start_profile_run` seam with a bound `analysis_scope` and
isolated workspaces; list/add/remove all reached `manage_watchlist`, persisted
the scoped change and restored state. The aliases were deleted in
`4cd0a598706011ba80672508b35439b685e78b92`.

### VERDICT

**PASS — DELETE_OLD_PATH.** The original per-run metrics were not promoted
into the repository before this report; this report does not reconstruct
unknown numbers.

## P7.2 — live-signal alias

### CALLERS BEFORE

The documented daily-decision prompt required `get_live_signals`; the tool
shared `_live_scan_payload` with `run_live_scan` and had no distinct engine or
result contract.

### CALLER MIGRATION / PRE-CANARY / RETIREMENT / POST-CANARY

The daily prompt now performs one explicit `run_live_scan`, derives the
decision from that result, records one Decision Brief and stops. L1/L2/L3 and
the broad opportunity probe reached `run_live_scan` / `get_signal_board` with
zero legacy or generic escape. `get_live_signals` was deleted in
`5bb2ad653af3f8fbc79eff7c04fcf43e4c712472`; `_live_scan_payload` remains the
private implementation for `run_live_scan`.

### VERDICT

**PASS — DELETE_OLD_PATH.** The original per-run metrics were not promoted
into the repository before this report; no values are inferred.

## P7.3 — broad trading context

### CALLERS BEFORE

The P6 baseline named bridge E1/E2 `RUN_PROMPT` as the production caller.
Fresh discovery also found a current interactive caller omitted from that
baseline: the Quant Dashboard's `Ask Agent` prompt in
`zuaef_quant.dashboard.render` (and its generated `docs/quant/business.html`)
required `get_trading_context`. Plugin instructions, the quant-research skill,
CodeMode configuration, current docs/knowledge and tests also named it.

### CALLER MIGRATION

- Bridge prompts are event-specific: E1 starts with `get_signal_board`; E2
  starts with `get_positions`. Both keep the event JSON, interpretation-only
  boundary, non-blocking missing-state wording and no-delivery-authority rule.
- Dashboard `Ask Agent` starts with `get_symbol_context` and adds
  `get_positions` only when holdings/exit state is relevant.
- Quant instructions, skill, freshness contract, current docs and knowledge
  now name the narrow owners. Validation accounting comes from
  `get_validation_status`; opportunity freshness comes from
  `get_signal_board`; holdings freshness comes from `get_positions`.
- CodeMode is narrowed to `get_symbol_context` and `evaluate_strategy`.
  Explicit scans and trading projections remain on the Agent surface.

Historical reports, dated implementation notes, spec packs and
`_bmad-output` were not rewritten.

### PRE-RETIREMENT CANARY

| Case | Reality condition | Tool sequence | Verdict |
|---|---|---|---|
| T1 validation | isolated current artifacts | `search_tools → get_validation_status` | PASS |
| T2 positions | isolated current artifacts | `search_tools → get_positions` | PASS |
| T3 complete state | isolated current artifacts | `search_tools → get_validation_status → get_signal_board → get_positions` | PASS |
| E1 suppressed | READY fixture; recording sender | `search_tools → get_signal_board → get_positions → get_symbol_context` | PASS |
| E2 suppressed | EXIT_ALERT position fixture; recording sender | `search_tools → get_positions` | PASS |
| E1 real send | production projection has no current READY | `search_tools → get_signal_board → get_symbol_context` | PASS |
| E2 real send | production projection has no open position | `search_tools → get_positions → get_trading_context` | **SURFACE_GAP_STOP** |

All seven runs completed. Generic escapes and delivery-tool effects were zero.
Both real messages were sent once by the bridge and have matching canonical
event identity, `delivered_ids`, `bridge.jsonl` entry and receipt:

- E1 `NEW_READY:601799:2026-09-12T16:18:01+08:00`, run
  `6f8d0110b3fd44678a157d006b862592`.
- E2 `POSITION_EXIT_ALERT:601799:2026-09-12T16:27:09+08:00`, run
  `cda06485ef8d4dfa9c5094e492865f44`.

These are explicitly labelled canary events, not assertions of current
READY/position truth. The user-authorized sends are externally visible and
the canonical alert rows are intentionally retained as audit evidence.

### RETIREMENT

**NOT EXECUTED.** The production E2 trajectory loaded the broad tool only
after `get_positions` honestly returned no open position. The trace proves
that the current model-visible surface still treats the broad projection as a
fallback in this missing-state event shape. It does not prove which individual
broad-only field was decisive; `heartbeat_at`, `recent_material_events` and
`last_scan_market_date` therefore remain unresolved rather than being guessed
away.

`get_trading_context`, its contract tests and freshness coverage stay in the
tree, deferred through ToolSearch. Final inventory is 16 tools, not the
planned 15.

### POST-CANARY / VERDICT

No post-retirement run exists because no retirement occurred.

**TRADING_CONTEXT_RETAINED_WITH_EVIDENCE — KEEP.** Do not tighten the prompt,
add a host router, duplicate the event into another state layer, or repeat the
unchanged canary merely to manufacture a pass. A later retirement attempt
requires new evidence explaining the missing-state need and a narrow existing
owner that preserves the accepted E2 outcome.

### PARTIAL-STOP VERIFICATION

- Focused bridge/plugin/freshness/surface/disclosure/business suite: 89 passed,
  1 skipped.
- Remaining operator/production/replay/scan group: 38 passed, 2 skipped.
- Remaining market/symbol/trading/validation/watchlist group: 35 passed,
  5 skipped.
- Manifest integrity: 3 passed; `ruff check .`: passed.
- `test_quant_research.py`: 17 passed and the previously recorded mocked-feed
  failure remains (`TestMarketIntelAdapter...`, missing `count`).
- `test_quant_hydration.py` and `test_quant_v31.py` still cannot collect in
  the main `.venv` because pandas is absent; `.venv-quant` has pandas but does
  not install pytest. These are environment/pre-existing gates, not claimed
  as passing.

## P7.4 — final freeze

**NOT STARTED BY STOP RULE.** C1–C12/B1–B2, the exact 15-tool guard and the
`P7 complete; OPERATE mode` status transition are not claimed. There is no P8
authorization in this report.
