# Quant P5 Operator Surface Report

| Field | Value |
|---|---|
| Status | P5_FULL_PASS |
| Phase | P5 — Domain Operator Surface |
| Prerequisite | P4_FULL_PASS |
| Command entry | `zuaef-quant = "zuaef_quant.ops:main"` |
| Scope | deterministic operator commands; zero model requests by the CLI itself |
| Tested tree | local working tree @ `cf581e50b62e` + P0–P5 patches |


> **P5.8 update:** monitor and bridge production authority have since moved into
> `zuaef_quant` (`zuaef_quant/monitor.py`, `zuaef_quant/bridge.py`,
> `zuaef_quant/continuity.py`); the root `tools/quant_trading_monitor.py` and
> `tools/quant_telegram_bridge.py` files are now thin compatibility wrappers.
> See [`P5_8_PRODUCTION_AUTHORITY_REPORT.md`](./P5_8_PRODUCTION_AUTHORITY_REPORT.md).

---

## 1. COMMANDS ADDED

```text
zuaef-quant status
zuaef-quant scan
zuaef-quant watchlist list|add|remove
zuaef-quant monitor once|status
zuaef-quant dashboard render|serve
zuaef-quant bridge once
```

Top-level commands: **6**. No generic `ask`, `analyze`, `service` or
script-name command was added. The Core CLI (`src/zuaef_agent/cli.py`) was not
modified; Quant owns this binary through `plugins/zuaef-quant/pyproject.toml`.

| Command | Operator intent | Default output |
|---|---|---|
| `status` | current Quant business/runtime state | short key/value lines; `--json` bounded object |
| `scan` | refresh today's candidate scan now | bounded scan summary; `--json` full scan envelope |
| `watchlist` | list/add/remove scoped attention facts | verified mutation summary |
| `monitor once` | run one deterministic monitor tick | status/events summary |
| `monitor status` | inspect monitor runtime facts | market/last-tick/positions summary |
| `dashboard render` | regenerate business HTML | artifact path + renderer summary |
| `dashboard serve` | foreground workbench transport | HTTP server process |
| `bridge once` | one existing Telegram bridge tick | bridge output or completion |

---

## 2. SHARED AUTHORITIES

| Command | Shared production authority | CLI responsibility |
|---|---|---|
| `scan` | `zuaef_quant.scan_sidecar` | spawn side env, parse bounded JSON, format |
| Agent `run_live_scan` / `get_live_signals` | same `zuaef_quant.scan_sidecar` through `toolset._run_module` | model-facing payload + evidence scope |
| `watchlist add/remove` | `zuaef_quant.watchlist.update_symbols_in` + read-back | scope resolution + output |
| `monitor once` | `tools/quant_trading_monitor.py once` production host op | spawn/parse, map failure output |
| `monitor status` | shared `toolset._read_trading_snapshot` projection | bounded monitor fields |
| `dashboard render/serve` | existing `quant_render_business_dashboard.py` / `quant_serve.py` | subprocess orchestration |
| `bridge once` | existing `quant_telegram_bridge.py` one-shot tick | subprocess orchestration |
| `status` | shared `toolset._read_trading_snapshot` | aggregate bounded operator facts |

The scan migration is complete: `tools/quant_live_scan.py` is now a thin
compatibility wrapper that imports `zuaef_quant.scan_sidecar`; the Agent tools
and the operator CLI both execute that sidecar module. There is one scan
business authority.

Watchlist symbol normalization, scope slugging, cap enforcement, write and
read-back remain entirely in `zuaef_quant.watchlist`; the CLI does not carry a
second implementation. The operator scope is explicit (`--scope` or
`ZUAEF_QUANT_OPERATOR_SCOPE`) because there is no implicit operator
case/channel binding and P5 must not invent one.

---

## 3. ZERO-MODEL PROOF

The operator CLI itself performs no model request. It contains no model
import, no agent composition, no `ToolSearch`, no semantic routing and no
`ask`/`analyze` command.

| Command | Model request path |
|---|---|
| `status` | none — filesystem projection |
| `scan` | none — side-env scan sidecar |
| `watchlist` | none — local watchlist store |
| `monitor once` | none — deterministic monitor tick |
| `monitor status` | none — filesystem projection |
| `dashboard render/serve` | none — HTML/HTTP |
| `bridge once` | none in the CLI. The existing bridge preserves its production behavior: a material alert may start the existing interpretation-only bridge Agent run, exactly as the systemd timer does today. This is not a CLI-introduced model call, and an empty/non-material event stream performs zero model requests. |

Per-command subprocess contracts are bounded and deterministic. No command
creates a model turn; no operator command accepts a natural-language prompt.

---

## 4. SYSTEMD ENTRIES MIGRATED

| Unit | Before | After | Rationale |
|---|---|---|---|
| `zuaef-quant-dashboard.service` | `.venv/bin/python tools/quant_serve.py ...` | `.venv/bin/zuaef-quant dashboard serve ...` | operator deployment no longer needs repo script path |
| `zuaef-quant-bridge.service` | `.venv/bin/python tools/quant_telegram_bridge.py` | `.venv/bin/zuaef-quant bridge once` | same one-shot tick through the domain CLI |
| `zuaef-quant-monitor.service` | `.venv/bin/python tools/quant_trading_monitor.py session ...` | unchanged | the long A-share session is systemd-owned; P5 does not add start/stop/session-manager commands |
| installer smoke | direct monitor/bridge scripts | `.venv/bin/zuaef-quant monitor once` / `bridge once --dry-run` | deployment smoke uses the operator surface |

System service lifecycle (`systemctl --user ...`) remains systemd's job; the
CLI intentionally has no `service start/stop/restart`.

---

## 5. LEGACY SCRIPT ENTRYPOINTS REMAINING

| Entrypoint | P5 status | P6 note |
|---|---|---|
| `tools/quant_live_scan.py` | THIN COMPAT WRAPPER | import/CLI compatibility only; authority is `zuaef_quant.scan_sidecar` |
| `tools/quant_trading_monitor.py` | PRODUCTION AUTHORITY (monitor session, `once`, ack/skip, symbol-context) | move monitor engine under domain package before retiring |
| `tools/quant_telegram_bridge.py` | PRODUCTION AUTHORITY (delivery/consumption) | move/rename into domain-owned deployment entry before retiring |
| `tools/quant_render_business_dashboard.py` | operator entry, implementation root-owned | P6 candidate |
| `tools/quant_serve.py` | transport entry, implementation root-owned | P6 candidate |
| `tools/quant_build_candidates.py` | candidate-pool refresh, developer/operator | P6 classification |
| `tools/quant_market_context.py`, `quant_market_intel.py`, `quant_eval_qlib.py`, proof/audit scripts | adapters / developer / benchmark | not daily operator surface; may stay in `tools/` |

No legacy model-visible alias was removed or changed.

---

## 6. DAILY OPS STILL REQUIRING SCRIPT PATHS

After P5, normal daily Quant operations no longer require repository script
paths:

```text
status            -> zuaef-quant status
scan              -> zuaef-quant scan
watchlist         -> zuaef-quant watchlist ...
monitor tick      -> zuaef-quant monitor once
monitor facts     -> zuaef-quant monitor status
dashboard render  -> zuaef-quant dashboard render
dashboard serve   -> zuaef-quant dashboard serve
bridge tick       -> zuaef-quant bridge once
```

Remaining script-path operations are intentionally outside the operator
surface: long-session monitor service (systemd unit), candidate-pool refresh
(`quant_build_candidates.py`), evaluator, PIT/anti-leakage/data proofs,
reconcile and benchmark/diagnostic scripts. They are not daily operator
actions and P5 does not promote them into `zuaef-quant`.

---

## 7. TESTS

New tests:

```text
tests/test_quant_ops_cli.py
```

- command-tree shape and no forbidden command names;
- `status --json` bounded payload;
- `scan` delegates to `zuaef_quant.scan_sidecar` (`-m`, not the legacy root script);
- human scan output stays small;
- watchlist add/list/remove share the domain store and verify persistence;
- watchlist scope fails closed when unconfigured and works from the existing env;
- monitor once/status delegate to the shared projections;
- dashboard/bridge commands delegate to existing entry points;
- migrated systemd/install-smoke entries use the operator CLI.

Additional P5 adaptation:

- `tests/test_quant_plugin.py` and
  `tests/test_quant_semantic_surface.py` now assert the Agent scan tools call
  `_run_module("zuaef_quant.scan_sidecar", ...)` rather than the legacy script.

Regression suite results are recorded in §8.

---

## 8. P3 REGRESSION

P5 did not change the model-visible surface. The P4 non-blocking Canary 1
discovery observation remains as previously recorded and was not touched.

Affected real-model smoke canaries were re-run through the same
`GatewayService.handle()` + normalized Telegram `InboundEnvelope` + capture
`SurfaceAdapter` path, fresh `/new` + `/profile quant-decision`, real model
`deepseek/deepseek-v4-flash-0731`, real Quant side environment and real
workspace artifacts. Raw evidence: `P5_QUANT_SMOKE_RESULTS.json`.

| Canary | Expected | Actual | Requests | Legacy broad | Generic escape | Result |
|---|---|---|---|---:|---|---|---|
| 2 Positions | `get_positions` | `search_tools -> get_positions` | 3 | 0 | 0 | PASS |
| 4 Explicit scan | `run_live_scan` | `search_tools -> run_live_scan` | 3 | 0 | 0 | PASS |
| 7 Market-wide | `get_market_context` | `search_tools -> get_market_context` | 3 | 0 | 0 | PASS |
| 5a Watchlist add | `manage_watchlist(add)` | `search_tools -> manage_watchlist` | 3 | 0 | 0 | PASS |
| 5b Watchlist remove | `manage_watchlist(remove)` | `search_tools -> manage_watchlist` | 3 | 0 | 0 | PASS |

```text
EXPECTED TOOL HIT:   5/5
LEGACY BROAD:        0
GENERIC ESCAPES:     0
EXECUTION FAILURES:  0
WATCHLIST SCOPE:     restored to [] and canary file removed
```

This is the smallest smoke set required by the P5 gate (scan, positions,
market, watchlist mutation). P4 already ran the full 9-canary matrix after
engine consolidation.

## 9. TESTS

Deterministic verification run for P5:

```text
.venv targeted suite:
  tests/test_quant_ops_cli.py
  tests/test_quant_semantic_surface.py
  tests/test_quant_plugin.py
  tests/test_quant_validation_accounting.py
  tests/test_quant_freshness.py
  tests/test_quant_scan_engine.py
  tests/test_manifest_integrity.py
  -> 98 passed, 1 skipped (as of the final P5 verification run)

quant side environment + pandas suites:
  PYTHONPATH=.venv/lib/python3.13/site-packages .venv-quant/bin/python -m pytest \
    tests/test_quant_business.py tests/test_quant_trading_monitor.py \
    tests/test_quant_scan_engine.py -q
  -> 177 passed

targeted ruff:
  all P5-touched Python files -> pass

real CLI smoke:
  zuaef-quant scan --json  -> real sidecar scan, exit 0
  zuaef-quant status       -> bounded status, exit 0
  zuaef-quant watchlist    -> add/list/remove verified against a temp workspace
  zuaef-quant dashboard render --out /tmp/... -> renderer exit 0
```

P5 test adaptation note: `tests/test_quant_plugin.py` and
`tests/test_quant_semantic_surface.py` now pin the Agent scan path to
`_run_module("zuaef_quant.scan_sidecar", ...)`, matching the single authority.

## 10. P5 VERDICT

```text
COMMANDS ADDED:         6 top-level / 10 leaves
SHARED AUTHORITIES:     scan sidecar, watchlist store, monitor host op,
                        renderer/serve, bridge tick, read-only status projection
ZERO-MODEL:             CLI orchestration adds no model request; bridge once
                        preserves the existing bridge interpretation behavior
SYSTEMD MIGRATED:       dashboard service + bridge service + installer smoke
LEGACY ENTRYPOINTS:     tools/quant_live_scan.py is now a THIN_COMPAT_WRAPPER;
                        monitor/bridge still own production authority until P6
DAILY SCRIPT PATHS:     none for the seven daily operator actions; developer
                        proofs/benchmarks intentionally remain in tools/
TESTS:                  98 passed / 1 skipped agent-side; 177 passed quant-side;
                        targeted ruff pass; manifest pass
P3 SMOKE:               5/5 expected tools, 0 legacy broad, 0 generic escapes,
                        0 execution failures
P4 OBSERVATION:         untouched, still non-blocking
P5 VERDICT:             P5_FULL_PASS
```

---

## 11. P6 READY?

**NOT YET.** P5 removed the daily script-path dependency and demoted
`tools/quant_live_scan.py` to a thin wrapper. P5.8 then moved monitor and
bridge authority into `zuaef_quant` (`monitor.py`, `bridge.py`) and made the
root counterparts thin compatibility wrappers.

P6 remains gated because production behavior still lives in root `tools/` for
the business renderer/serve, candidate discovery, market adapters and
evaluator. P5.8's report lists the exact remaining files and callers. Developer/
benchmark scripts (PIT, anti-leakage, data proof, candidate scoring) may remain
in `tools/` or move independently; they are not P6 blockers unless a
production caller still depends on them.
