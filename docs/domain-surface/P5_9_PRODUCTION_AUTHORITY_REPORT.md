# Quant P5.9 — Production Authority Completion Report

| Field | Value |
|---|---|
| Status | P5.9_FULL_PASS |
| Phase | P5.9 — remaining production ownership moved out of root `tools/` |
| Prerequisite | `P5.8_FULL_PASS` |
| Tested tree | local working tree @ `cf581e50b62e` + P0–P5.9 patches |
| Real-model evidence | `P5_9_SMOKE_RESULTS.json` |
| Next gated phase | P6 Shadow Product Layer Retirement — **READY** |

---

## AUTHORITIES AT START

Exactly six root scripts still owned production runtime behavior after P5.8:

| # | Root authority | Observed production caller | Type |
|---|---|---|---|
| 1 | `tools/quant_market_context.py` | Agent `get_market_context` sidecar | Domain Reality Interface |
| 2 | `tools/quant_market_intel.py` | Agent `get_market_intelligence` sidecar | Domain Reality Interface |
| 3 | `tools/quant_build_candidates.py` | candidate-pool refresh / ranking input | Domain production pipeline |
| 4 | `tools/quant_eval_qlib.py` | Agent `evaluate_strategy` sidecar | Heavy deterministic evaluator |
| 5 | `tools/quant_render_business_dashboard.py` | `zuaef-quant dashboard render` | Domain presentation |
| 6 | `tools/quant_serve.py` | `zuaef-quant dashboard serve`, systemd dashboard | Domain transport |

No new external-engine fact appeared during execution, so no external engine
exemption was claimed. All six became `zuaef_quant` owners.

## TARGET OWNER

```text
zuaef_quant/
    market_context.py                   # domain engine: market-wide reality
    market_intel.py                     # domain engine: public-event reality
    candidates_sidecar.py               # sidecar: candidate discovery/ranking
    eval_sidecar.py                     # sidecar: frozen strategy evaluation
    dashboard/
        render.py                       # operator app: read-only projection → HTML
        serve.py                        # operator app: loopback HTTP transport
    runtime.py                          # stdlib deployment/path helper
    dump_bin.py                         # vendored upstream ingest dependency
```

Ownership classes remain distinct: market context and market intelligence stay
separate semantic surfaces; candidate build stays separate from live scan;
renderer stays separate from server; dashboard stays a projection, not a second
Quant state.

## AUTHORITIES MOVED

| Root authority | New production implementation | Migration character |
|---|---|---|
| `quant_market_context.py` | `zuaef_quant.market_context` | File copy with only module/provenance changes; contract and business fields unchanged |
| `quant_market_intel.py` | `zuaef_quant.market_intel` | File copy; bounded feed contract unchanged |
| `quant_build_candidates.py` | `zuaef_quant.candidates_sidecar` | Production pipeline moved; imports now package-relative (`quant_core`, `scan`, `scan_sidecar`) |
| `quant_eval_qlib.py` | `zuaef_quant.eval_sidecar` | Evaluator moved; `quant_core` package-relative; qlib upstream `dump_bin` vendored into package so no dynamic load of `tools/` remains |
| `quant_render_business_dashboard.py` | `zuaef_quant.dashboard.render` | Faithful renderer move (no UI rewrite); repo root resolved without `tools/` topology |
| `quant_serve.py` | `zuaef_quant.dashboard.serve` | Transport moved; scan/monitor commands now `-m zuaef_quant.scan_sidecar` / `-m zuaef_quant.monitor` |

Supporting ownership hardening:

- `plugins/zuaef-quant/zuaef_quant/runtime.py` owns repo/workspace and quant
  Python path resolution, stdlib-only; no root script marker is needed.
- `zuaef_quant.dump_bin` is the evaluator's vendored upstream ingest code
  (copied unchanged from the audited upstream file). This was required to close
  the last `zuaef_quant -> tools/` dynamic dependency. The root
  `tools/quant/upstream/dump_bin.py` remains a vendored reference asset.
- `toolset.py` no longer defines `TOOLS_DIR` or `QUANT_*_SCRIPT`; the five
  production routes use `_run_module(...)`:

```text
evaluate_strategy            -> zuaef_quant.eval_sidecar
get_market_intelligence      -> zuaef_quant.market_intel
get_market_context           -> zuaef_quant.market_context
render_quant_business_artifact -> zuaef_quant.dashboard.render
scan/monitor                  -> zuaef_quant.scan_sidecar / zuaef_quant.monitor
```

## ROOT WRAPPERS CREATED

All six root files were reduced to `THIN_COMPAT_WRAPPER` form: shebang,
docstring, package-path insertion, `from <plugin module> import *`, explicit
`main` forwarding, and `__main__` only. They define no business functions or
classes.

```text
tools/quant_market_context.py            -> zuaef_quant.market_context
tools/quant_market_intel.py              -> zuaef_quant.market_intel
tools/quant_build_candidates.py          -> zuaef_quant.candidates_sidecar
tools/quant_eval_qlib.py                 -> zuaef_quant.eval_sidecar
tools/quant_render_business_dashboard.py -> zuaef_quant.dashboard.render
tools/quant_serve.py                     -> zuaef_quant.dashboard.serve
```

The P5.8 wrappers (`quant_core`, `quant_live_scan`, monitor, bridge) remain
thin compatibility wrappers as before. P6 may delete any wrapper with no
remaining compatibility need.

## PRODUCTION REVERSE DEPENDENCIES REMOVED

Static guard tests
(`tests/test_quant_production_authority.py`) and the updated
`tests/test_quant_ops_cli.py` pin:

- no production plugin module names/imports/dynamically loads any of the six
  historical root scripts;
- `toolset.py` contains no `TOOLS_DIR`, no `QUANT_*_SCRIPT`, and routes the
  semantic sidecars to `zuaef_quant.*` modules;
- `ops.py` routes `dashboard render|serve` to
  `python -m zuaef_quant.dashboard.render|serve`;
- `dashboard/serve.py` routes scan/watchlist/ack work to
  `python -m zuaef_quant.scan_sidecar` and `python -m zuaef_quant.monitor`.

Repo-root independence probe: a temporary root containing only
`plugins/zuaef-quant/`, `benchmarks/quant/gen1/quant.toml` and an empty
`workspace/` (no `tools/` directory at all) successfully ran the market-intel,
candidate-sidecar and evaluator help paths plus a real dashboard render
(`75.0 KB` degraded-state HTML). No production operation needed
`repo/tools/quant_x.py`.

## SIDECAR ENVIRONMENT STATUS

- Heavy dependencies remain only in `.venv-quant`; the Agent environment still
  carries no pandas/akshare/qlib. Verified in `.venv`:
  `pandas loaded: False`, `qlib loaded: False` after importing the plugin.
- `toolset._run_module()` and the operator sidecs add the package parent to
  `PYTHONPATH`, so `.venv-quant/bin/python -m zuaef_quant.<module>` resolves
  the implementation without an installed wheel or a second distribution.
- Real evaluator execution in `.venv-quant` through
  `zuaef_quant.eval_sidecar` completed in `61.9s` with 8 artifacts, including
  `evidence.json`, `result.md`, intents, trades and both equity curves.
- No RPC service, daemon, socket protocol, registry/framework or new durable
  state was introduced.

## PARITY RESULTS

| Authority | Evidence | Result |
|---|---|---|
| Market context | `tests/test_quant_market_context.py` (complete fixture, bounded news, missing-stays-missing, fallback feeds) | 5 passed |
| Candidate discovery/ranking | `tests/test_quant_business.py` (universe fail-closed, scoring, sector cap, snapshot/degraded renderer, HTTP route map, ack argv) | 122 passed |
| Evaluator + engine mechanics | `tests/test_quant_scan_engine.py`, `tests/test_quant_replay.py`, quant-side suite `test_quant_business`, `test_quant_trading_monitor`, `test_quant_v31`, `test_quant_hydration` | 47 passed; 234 passed, 1 skipped |
| Model-surface ownership | `test_quant_plugin`, `test_quant_ops_cli`, `test_quant_semantic_surface`, `test_quant_tool_disclosure`, `test_quant_production_authority` | 64 passed |
| Architecture/package integrity | `tests/test_manifest_integrity.py` after manifest regeneration | 3 passed |

Business-code parity: the moved source bodies were copied, not rewritten.
Only imports, package paths, command strings, repo-root resolution and P5.9
provenance changed. Trading rules, evaluator semantics, candidate scoring and
dashboard business projections were not altered.

## REAL-MODEL SMOKE

Raw evidence: `docs/domain-surface/P5_9_SMOKE_RESULTS.json`.
Surface: real `zuaef-agent run --profile quant-decision` (all plugins, real
model, real sidecar execution, isolated `/tmp` workspaces). Model:
`deepseek/deepseek-v4-flash-0731`.

| Canary | Prompt | Tool sequence | Requests / tools | Result |
|---|---|---|---|---|
| 6 — Symbol | `分析一下002415现在的情况。` | `get_symbol_context` | 2 / 1 | PASS |
| 7 — Market-wide | `分析今天A股为什么大跌。` | `search_tools -> get_market_context` | 3 / 2 | PASS |
| 8 — Compositional | `分析今天A股为什么大跌，并告诉我这对现有持仓有什么影响。` | `search_tools -> get_market_context -> get_positions` | 3 / 3 | PASS |
| Market intelligence | `查一下 002415 最近的新闻和公告，最多5条。` | `search_tools -> search_knowledge -> get_market_intelligence` | 3 / 3 | PASS (expected intel path reached; no shell/repo escape) |
| Real evaluation | one `evaluate_strategy` child | `evaluate_strategy` | 2 / 1 | PASS |

Real evaluation facts: 54 frozen intents, 24 trades in both engines,
independent replay annualized `0.2031%`, vector stage `0.1843%`, consistency
diff `0.0188pp` vs `3.0pp` tolerance -> within tolerance; corporate-action gate
`PASS`. The evaluator was invoked through `zuaef_quant.eval_sidecar`; the model
made no filesystem, shell or repo fallback calls. Expected semantic tool hit,
generic escapes = 0, legacy substitution evidence = 0 for the affected
canaries.

## OPERATOR REGRESSION

| Command | Result |
|---|---|
| `zuaef-quant status --json` | exit 0, bounded canonical-artifact projection |
| `zuaef-quant scan --universe-file benchmarks/quant/gen1/legacy_watchlist.toml --json` | exit 0, 15 symbols / 15 quotes, volume gate `STALE` fail-closed |
| `zuaef-quant dashboard render --out ...` | exit 0, single-file self-contained HTML (`114.9 KB`) |
| `zuaef-quant dashboard serve --host 127.0.0.1 --port 19001` | starts; `GET /business`, `/engineering`, `/api/attention`, `/api/quant/now` all 200 |
| `zuaef-quant monitor once --state-dir /tmp/... --json` | exit 0, `MARKET_CLOSED`, no mutation |
| `zuaef-quant bridge once --dry-run` | exit 0, `Bridge tick completed` |

systemd dashboard and bridge units already point at `zuaef-quant`
(`tools/quant_serve.py` no longer appears in deployment wiring). The monitor
service continues to use its existing wrapper until P6; that wrapper now owns
no business logic and delegates to `zuaef_quant.monitor`.

## REMAINING PRODUCTION ROOT AUTHORITIES

**None.** For the P5.9 inventory question — “is there a `tools/quant_*` file
that owns production runtime authority?” — the answer is `NO`.

Root classifications after migration:

```text
tools/quant_market_context.py            THIN_COMPAT_WRAPPER
tools/quant_market_intel.py              THIN_COMPAT_WRAPPER
tools/quant_build_candidates.py          THIN_COMPAT_WRAPPER
tools/quant_eval_qlib.py                 THIN_COMPAT_WRAPPER
tools/quant_render_business_dashboard.py THIN_COMPAT_WRAPPER
tools/quant_serve.py                     THIN_COMPAT_WRAPPER
tools/quant_core.py                      THIN_COMPAT_WRAPPER
tools/quant_live_scan.py                 THIN_COMPAT_WRAPPER
tools/quant_trading_monitor.py           THIN_COMPAT_WRAPPER
tools/quant_telegram_bridge.py           THIN_COMPAT_WRAPPER
tools/quant_fetch_universe.py            DEVELOPER_TOOL / REALITY_PREP
tools/quant_validate_semantics.py        DEVELOPER_TOOL / DATA PROOF
tools/quant_pit_audit.py                 BENCHMARK / AUDIT
tools/quant_anti_leakage_check.py        BENCHMARK / AUDIT
tools/quant_p05_reconcile.py             BENCHMARK / RECONCILE
tools/quant_p0_data_proof.py             BENCHMARK / DATA PROOF
tools/quant_render_dashboard.py          DEVELOPER/OBSERVATION RENDERER
tools/quant_v31.py                       BENCHMARK / REPLAY
tools/quant_daily.sh                     OPERATOR CONVENIENCE SCRIPT
tools/quant/upstream/dump_bin.py         VENDORED UPSTREAM REFERENCE
```

The `zuaef_quant` production import direction is now:

```text
tools/thin wrappers ─► zuaef_quant
```

with no reverse import, subprocess path or dynamic load from `zuaef_quant`
into any `tools/quant_*.py` production authority.

## P5.9 VERDICT

`P5.9_FULL_PASS`

- Gate A: `get_market_context`, `get_market_intelligence`,
  `evaluate_strategy` no longer call root implementations. PASS.
- Gate B: candidate production refresh core logic is owned by
  `zuaef_quant.candidates_sidecar`; root is wrapper only. PASS.
- Gate C: `zuaef-quant dashboard render|serve` no longer depend on root
  implementation authority. PASS.
- Gate D: the six root files are `THIN_COMPAT_WRAPPER` only; no
  `PRODUCTION_AUTHORITY` remains. PASS.
- Gate E: production import/call direction is `plugin -X-> tools`. PASS.
- Gate F: affected P3 semantic behavior shows expected tool hit, generic
  escape `0`, legacy substitution `0`. PASS.
- Gate G: operator commands work (status, scan, monitor, dashboard, bridge). PASS.
- Gate H: heavy dependencies remain isolated in `.venv-quant`. PASS.
- Gate I: no framework/router/registry/daemon/service protocol added. PASS.

## P6 READY

**P6 READY: YES**

P6 is now small: delete/retain compatibility wrappers, classify developer
tools, update stale docs/deployment references, and remove stale imports.
No multi-thousand-line production migration remains.
