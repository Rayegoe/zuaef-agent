# Quant P5.8 — Production Authority Extraction Report

| Field | Value |
|---|---|
| Status | P5.8_FULL_PASS |
| Phase | P5.8 — remove remaining root-script production authority before P6 |
| Prerequisite | P5 operator surface proven |
| Tested tree | local working tree @ `cf581e50b62e` + P0–P5.8 patches |
| Model-visible surface | unchanged |
| Systemd lifecycle | unchanged (internal target changed to plugin authority) |

---

## 1. Mission Result

For the migrated production paths the call direction is now:

```text
Agent Tool ──────► zuaef_quant.scan_sidecar / zuaef_quant.monitor
zuaef-quant ─────► zuaef_quant.monitor / bridge / scan_sidecar
systemd ─────────► zuaef-quant ─────► zuaef_quant.*
root tools wrapper ─► zuaef_quant.*
```

No production monitor/bridge logic remains in root `tools/`.

## 2. Monitor Authority Moved

New production authority:

```text
plugins/zuaef-quant/zuaef_quant/monitor.py
```

Moved responsibilities:

- monitor cycle and market-hours decision;
- position lifecycle and exit evaluation;
- canonical trading-ledger mutation;
- summary projection and alert/event production;
- `.ledger.lock` transaction semantics;
- ack-buy / ack-sell / skip host operations;
- symbol-context host op and history prewarm;
- CLI parsing for legacy root callers.

Root compatibility wrapper:

```text
tools/quant_trading_monitor.py
```

It now only inserts the package path, star-imports
`zuaef_quant.monitor`, and forwards `main()`. It contains no business
constants, transition rules, ledger semantics or production mutation logic.

Agent tool migration:

```text
record_trade_outcome       -> _run_module("zuaef_quant.monitor", ...)
symbol-context             -> _run_module("zuaef_quant.monitor", ...)
watchlist prewarm          -> _run_module("zuaef_quant.monitor", ...)
```

Operator CLI migration:

```text
zuaef-quant monitor once  -> python -m zuaef_quant.monitor once
```

## 3. Shared Mechanics Moved

`tools/quant_core.py` was promoted to:

```text
plugins/zuaef-quant/zuaef_quant/quant_core.py
```

Root `tools/quant_core.py` is now a thin import wrapper. This keeps the
migrated monitor and scan sidecar from importing root implementation while
root tools/tests continue using the historical module name. The moved module
contains the same cache/history/market-rules/StrategySpec/replay mechanics; no
behavior was intentionally changed.

## 4. Bridge Authority Moved

New production authority:

```text
plugins/zuaef-quant/zuaef_quant/bridge.py
plugins/zuaef-quant/zuaef_quant/continuity.py
```

`bridge.py` owns the deterministic bridge tick and the explicit interpretation
boundary. Event selection, delivery identity, ordered checkpoint semantics,
fixed deterministic copies, Agent interpretation fallback behavior and dry-run
semantics are unchanged.

`continuity.py` owns the small session clock and M1 continuity verdict used by
the bridge so the plugin no longer imports the root dashboard renderer. The
verdict rule mirrors the dashboard's existing M1 verdict; the dashboard remains
a separate operator surface until P6.

Root compatibility wrapper:

```text
tools/quant_telegram_bridge.py
```

It only inserts the package path, star-imports `zuaef_quant.bridge`, and
forwards `main()`.

Operator CLI migration:

```text
zuaef-quant bridge once -> python -m zuaef_quant.bridge
```

Systemd units already call `zuaef-quant bridge once`; only the internal target
changed.

## 5. Import Direction Gate

For the migrated paths:

```text
tools/quant_live_scan.py          -> zuaef_quant.scan_sidecar
tools/quant_trading_monitor.py    -> zuaef_quant.monitor
tools/quant_telegram_bridge.py    -> zuaef_quant.bridge
tools/quant_core.py               -> zuaef_quant.quant_core
```

The reverse direction is not present for production monitor/bridge logic:
`zuaef_quant.monitor` and `zuaef_quant.bridge` do not import or spawn
`tools/quant_trading_monitor.py` / `tools/quant_telegram_bridge.py` or the root
renderer. A static authority regression test pins this.

## 6. Ledger and Lock Semantics

Unchanged:

- canonical trading-ledger writes still go through the monitor host authority;
- only `zuaef_quant.monitor.Store.transaction()` holds `.ledger.lock` across a
  read-modify-write;
- parallel ack-buy and session-cycle serialization behavior is preserved by the
  moved code and the existing transaction-lock tests;
- no second ledger writer or state store was introduced.

## 7. Parity Tests

Monitor:

```text
PYTHONPATH=.venv/lib/python3.13/site-packages .venv-quant/bin/python -m pytest \
  tests/test_quant_trading_monitor.py -q
-> 39 passed
```

This covers lifecycle, semantic gate, SYSTEM_UNAVAILABLE, exit evaluation,
transaction/ack behavior, market-phase boundaries, fixture isolation and
ledger lock behavior.

Legacy wrapper parity:

```text
python -m zuaef_quant.monitor --state-dir /tmp/... once
python tools/quant_trading_monitor.py --state-dir /tmp/... once
-> same JSON result {"status":"MARKET_CLOSED","events":[],"symbols":0}
```

Bridge:

```text
.venv/bin/python -m pytest tests/test_quant_telegram_bridge.py -q
-> 18 passed
```

This covers event selection, fixed copy, Agent interpretation, failures,
checkpoint-after-delivery, source reset and daily summary semantics.

Broader affected Quant suites:

```text
PYTHONPATH=.venv/lib/python3.13/site-packages .venv-quant/bin/python -m pytest \
  tests/test_quant_business.py tests/test_quant_trading_monitor.py \
  tests/test_quant_v31.py tests/test_quant_symbol_context.py \
  tests/test_quant_scan_engine.py -q
-> 200 passed, 1 skipped
```

## 8. Deployment Smoke

Safe real CLI smoke (no model calls, no production ledger mutation):

```text
zuaef-quant monitor once --state-dir /tmp/...  -> exit 0, MARKET_CLOSED
zuaef-quant bridge once --dry-run              -> exit 0, "Bridge tick completed"
zuaef-quant scan --json                        -> exit 0, real sidecar scan
```

`bridge once` preserves the P5 Class-B contract: deterministic dispatch and
event selection; no event → zero model requests; a material interpretation
event may invoke the existing explicitly authorized bridge Agent path.


Affected semantic smoke after the authority move (real model, real
GatewayService path): positions, explicit scan, watchlist add and watchlist
remove — expected tool 4/4, legacy broad 0, generic escapes 0, execution
failures 0. Raw evidence: `P5_8_SMOKE_RESULTS.json`. A full P3 matrix is not
re-run because P5.8 changes no tool name, description, defer flag or profile.

## 9. Tests

```text
agent-side targeted tests:
  tests/test_quant_ops_cli.py
  tests/test_quant_plugin.py
  tests/test_quant_semantic_surface.py
  tests/test_quant_telegram_bridge.py
  tests/test_quant_validation_accounting.py
  tests/test_quant_freshness.py
  tests/test_quant_scan_engine.py
  tests/test_manifest_integrity.py
  -> 118 passed, 1 skipped

quant-side pandas suites:
  tests/test_quant_business.py
  tests/test_quant_trading_monitor.py
  tests/test_quant_v31.py
  tests/test_quant_symbol_context.py
  tests/test_quant_scan_engine.py
  tests/test_quant_hydration.py
  tests/test_quant_replay.py
  -> 237 passed, 1 skipped
```

Static authority tests:

- plugin monitor/bridge sources must not mention/spawn the historical root
  implementation scripts;
- root wrapper sources must import the plugin implementation and must not
  define `run_cycle` / `run_tick` / `consume_alerts`;
- CLI monitor/bridge commands must use `-m zuaef_quant.monitor` /
  `-m zuaef_quant.bridge`.

## 10. Remaining Root Production Authority

After P5.8, the following root files still own production runtime behavior and
are the honest reason P6 is not yet authorized:

| Root file | P5.8 classification | Production caller |
|---|---|---|
| `tools/quant_render_business_dashboard.py` | PRODUCTION_AUTHORITY | operator CLI `dashboard render`, existing renderer service |
| `tools/quant_serve.py` | PRODUCTION_AUTHORITY | operator CLI `dashboard serve`, systemd dashboard unit |
| `tools/quant_build_candidates.py` | PRODUCTION_AUTHORITY | candidate-pool refresh |
| `tools/quant_market_context.py` | PRODUCTION_AUTHORITY | Agent `get_market_context` sidecar |
| `tools/quant_market_intel.py` | PRODUCTION_AUTHORITY | Agent `get_market_intelligence` sidecar |
| `tools/quant_eval_qlib.py` | PRODUCTION_AUTHORITY | Agent `evaluate_strategy` sidecar |

`tools/quant_live_scan.py`, `tools/quant_trading_monitor.py`,
`tools/quant_telegram_bridge.py` and `tools/quant_core.py` are now
THIN_COMPAT_WRAPPER.

## 11. P5.8 Verdict

```text
MONITOR AUTHORITY:    zuaef_quant.monitor (root wrapper thin)
BRIDGE AUTHORITY:     zuaef_quant.bridge + continuity (root wrapper thin)
SCAN AUTHORITY:       zuaef_quant.scan_sidecar (root wrapper thin)
LEDGER/LOCK:          unchanged, single writer authority
IMPORT DIRECTION:     root tools -> zuaef_quant for migrated paths
BUSINESS PARITY:      monitor/bridge/v31/symbol/scan suites pass
DEPLOYMENT SMOKE:     monitor once isolated + bridge dry-run + scan pass
SEMANTIC SURFACE:     unchanged; no new P3 matrix required by P5.8
P5.8 VERDICT:         P5.8_FULL_PASS
P6 READY:             NO — remaining production authorities listed above
```
