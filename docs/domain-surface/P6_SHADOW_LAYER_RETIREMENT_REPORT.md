# Quant P6 — Shadow Product Layer Retirement Report

| Field | Value |
|---|---|
| Status | P6_FULL_PASS |
| Prerequisite | `P5.9_FULL_PASS` |
| Scope | Quant shadow production layer retirement only |
| Tested tree | local working tree @ `cf581e50b62e` + P0–P6 patches |
| Raw smoke evidence | `P6_SMOKE_RESULTS.json` |
| Next gated phase | P7 Legacy Semantic Surface Retirement — **READY** |

---

## ROOT FILES AT START

At P6 start the root Quant inventory contained no `PRODUCTION_AUTHORITY`; all
production owners were already in `zuaef_quant`.  The only remaining retired
runtime surface was a set of ten zero-value compatibility wrappers plus true
developer/audit tooling:

```text
compatibility wrappers
    quant_core.py
    quant_live_scan.py
    quant_trading_monitor.py
    quant_telegram_bridge.py
    quant_market_context.py
    quant_market_intel.py
    quant_build_candidates.py
    quant_eval_qlib.py
    quant_render_business_dashboard.py
    quant_serve.py

developer / audit / benchmark / diagnostic
    quant_anti_leakage_check.py
    quant_fetch_universe.py
    quant_p05_reconcile.py
    quant_p0_data_proof.py
    quant_pit_audit.py
    quant_render_dashboard.py
    quant_v31.py
    quant_validate_semantics.py
    quant_daily.sh
    quant/upstream/dump_bin.py
```

## FINAL CLASSIFICATION

| File | Final class | Real caller / reason |
|---|---|---|
| `quant_core.py` | `DELETE_CANDIDATE` | only lifted imports in tests/developer tools; migrated to `zuaef_quant.quant_core` |
| `quant_live_scan.py` | `DELETE_CANDIDATE` | only lifted imports in tests/developer tools; migrated to `zuaef_quant.scan_sidecar` |
| `quant_trading_monitor.py` | `DELETE_CANDIDATE` | only legacy deployment path; systemd now runs the module directly |
| `quant_telegram_bridge.py` | `DELETE_CANDIDATE` | no remaining caller; systemd uses `zuaef-quant bridge once` |
| `quant_market_context.py` | `DELETE_CANDIDATE` | only wrapper compatibility; Agent calls `zuaef_quant.market_context` |
| `quant_market_intel.py` | `DELETE_CANDIDATE` | only wrapper compatibility; Agent calls `zuaef_quant.market_intel` |
| `quant_build_candidates.py` | `DELETE_CANDIDATE` | only wrapper compatibility; refresh calls `zuaef_quant.candidates_sidecar` |
| `quant_eval_qlib.py` | `DELETE_CANDIDATE` | only lifted imports in tests/audit tools; migrated to `zuaef_quant.eval_sidecar` |
| `quant_render_business_dashboard.py` | `DELETE_CANDIDATE` | only wrapper compatibility; operator uses `zuaef-quant dashboard render` |
| `quant_serve.py` | `DELETE_CANDIDATE` | only wrapper compatibility; operator/systemd use `zuaef-quant dashboard serve` |
| `quant_anti_leakage_check.py` | `AUDIT_TOOL` | independent engineering proof; no production dependency |
| `quant_fetch_universe.py` | `DEVELOPER_TOOL` | universe/data preparation; imports `zuaef_quant.quant_core` directly |
| `quant_p05_reconcile.py` | `BENCHMARK_TOOL` | dual-engine reconciliation proof; no production dependency |
| `quant_p0_data_proof.py` | `BENCHMARK_TOOL` | real-data proof; no production dependency |
| `quant_pit_audit.py` | `AUDIT_TOOL` | PIT contamination audit; no production dependency |
| `quant_render_dashboard.py` | `DIAGNOSTIC_TOOL` | engineering/observation renderer; not used by production runtime |
| `quant_v31.py` | `BENCHMARK_TOOL` | offline replay/research tooling; no production dependency |
| `quant_validate_semantics.py` | `AUDIT_TOOL` | data-semantics proof consumer; no production runtime authority |
| `quant_daily.sh` | `DEVELOPER/OPERATOR CONVENIENCE` | calls Agent/operator modules; not scheduled by production systemd |
| `quant/upstream/dump_bin.py` | `DELETE_CANDIDATE` | duplicate vendored file; canonical copy is `zuaef_quant.dump_bin` |

## WRAPPERS DELETED

All ten wrappers were deleted after caller migration.  For each, the deletion
condition was `production callers = 0`, `deployment callers = 0`, and
`required external compatibility callers = 0`.

```text
tools/quant_core.py
tools/quant_live_scan.py
tools/quant_trading_monitor.py
tools/quant_telegram_bridge.py
tools/quant_market_context.py
tools/quant_market_intel.py
tools/quant_build_candidates.py
tools/quant_eval_qlib.py
tools/quant_render_business_dashboard.py
tools/quant_serve.py
tools/quant/upstream/dump_bin.py
```

The duplicate root vendored `dump_bin.py` was also deleted because the package
copy at `plugins/zuaef-quant/zuaef_quant/dump_bin.py` is the single canonical
production dependency and no developer/research caller used the root copy.

## WRAPPERS RETAINED

**None.**  No `THIN_COMPAT_WRAPPER` remains in root `tools/`.  This is the
strong branch allowed by P6 §6, not a failure: every former wrapper had zero
remaining real caller after tests, docs and deployment references migrated.

Compatibility imports in developer tools/tests still resolve the plugin
implementation directly:

```text
tests / tools/*.py  ->  zuaef_quant.quant_core / scan_sidecar / eval_sidecar
systemd monitor     ->  .venv-quant/bin/python -m zuaef_quant.monitor session
operator CLI        ->  python -m zuaef_quant.dashboard.render|serve
```

## DEVELOPER / AUDIT TOOLS RETAINED

Retained by the developer-tool admission test:

```text
Does deleting it keep production fully working?   -> YES
Does it still provide independent engineering value? -> YES
```

| Tool | Independent value |
|---|---|
| `quant_anti_leakage_check.py` | behavioral lookahead check for frozen intents |
| `quant_pit_audit.py` | survivorship/PIT contamination evidence |
| `quant_validate_semantics.py` | volume semantics + live-quote health proof |
| `quant_p0_data_proof.py` | live data-source proof and freshness evidence |
| `quant_p05_reconcile.py` | dual-engine market-rule reconciliation |
| `quant_v31.py` | offline replay/research benchmark |
| `quant_render_dashboard.py` | engineering/audit observation page renderer |
| `quant_fetch_universe.py` | one-off universe preparation |

None of these owns a production runtime path, and none is called by the
Agent, operator CLI, systemd, production dashboard, monitor or bridge.

## PRODUCTION REFERENCES REMOVED

Production reference sweep across `src/`, `plugins/`, `profiles/`, `ops/`,
`docs/quant`, `tests/`, `pyproject`, systemd units, shell scripts and
benchmark contracts removed current references to the retired wrappers.

- `toolset.py` has no `TOOLS_DIR` / `QUANT_*_SCRIPT` / root wrapper names.
- `ops.py` invokes `-m zuaef_quant.dashboard.render|serve`, `-m zuaef_quant.scan_sidecar`, `-m zuaef_quant.monitor`, `-m zuaef_quant.bridge`.
- `dashboard/serve.py` invokes only `-m zuaef_quant.scan_sidecar` / `-m zuaef_quant.monitor`.
- `systemd` units and `ops/quant-live-verification.md` point at the operator CLI or plugin module.
- Current docs (`README`, `docs/quant/README.md`, `QUANT_AUTHORITY_MAP.md`,
  `docs/architecture/*`, benchmark comments, generated dashboard pages) point
  at Agent / Operator / Developer surfaces; old paths remain only in dated
  historical reports and decision logs, explicitly allowed by P6 §22.
- Tests that used root implementation imports were migrated to `zuaef_quant`;
  remaining test strings only assert the absence of retired paths.

A package-level static guard (`tests/test_quant_production_authority.py`)
pins the final classification, the absence of retained wrappers, the
developer-only status of retained tools, and systemd module commands.

## SYSTEMD / OPS STATUS

| Unit | ExecStart after P6 |
|---|---|
| `zuaef-quant-monitor.service` | `.venv-quant/bin/python -m zuaef_quant.monitor session --interval 45 --minutes 150 --exit-on-close` |
| `zuaef-quant-dashboard.service` | `.venv/bin/zuaef-quant dashboard serve --host 127.0.0.1 --port 8787` |
| `zuaef-quant-bridge.service` | `.venv/bin/zuaef-quant bridge once` |

The monitor unit also exports
`PYTHONPATH=%h/zuaef-agent/plugins/zuaef-quant` and uses the isolated
`.venv-quant` Python; heavy dependencies stay out of the Agent environment.
`ops/install_orangepi_node.sh`, `ops/quant-live-verification.md` and
`ops/systemd/README.md` now describe the operator/module entry points, not
root wrappers.

## REPO-ROOT INDEPENDENCE

Final proof root: `/tmp/p6-rootless` containing only

```text
plugins/zuaef-quant/
benchmarks/quant/gen1/quant.toml
workspace/artifacts/quant/v31/
```

with **no `tools/` directory at all**.  All of these succeed:

```text
python -m zuaef_quant.market_context --help          OK
python -m zuaef_quant.market_intel --help            OK
python -m zuaef_quant.candidates_sidecar --help      OK
python -m zuaef_quant.eval_sidecar --help            OK
python -m zuaef_quant.dashboard.render --out ...     OK (75.0 KB honest degraded-state HTML)
```

Deterministic operator smoke in the real repo after wrapper deletion:

```text
zuaef-quant status --json                                  exit 0
zuaef-quant scan --universe-file legacy_watchlist.toml     exit 0
zuaef-quant monitor once --state-dir /tmp/... --json       exit 0, MARKET_CLOSED
zuaef-quant dashboard render --out /tmp/...                exit 0, 114.9 KB
zuaef-quant dashboard serve                               GET /business /engineering /api/* all 200
zuaef-quant bridge once --dry-run                          exit 0
```

## SEMANTIC SMOKE

P6 does not touch the model surface; three representative real-model runs
were executed after wrapper deletion.  Raw receipt fields are in
`P6_SMOKE_RESULTS.json`.

| Canary | Prompt | Observed tool sequence | Legacy broad substitution | Generic escape |
|---|---|---|---|---|
| Market-wide | `分析今天A股为什么大跌。` | `search_tools -> get_market_context` | 0 | 0 |
| Positions | `我现在持有什么？` | `search_tools -> get_positions` | 0 | 0 |
| Explicit scan | `重新扫描一下今天。` | `search_tools -> run_live_scan` | 0 | 0 |

All runs completed (`execution_state=completed`), reached the expected
semantic authority, and used no shell/repo/generic fallback.

## REMAINING PRODUCTION ROOT AUTHORITIES

**None.**  Answer to the P6 final question:

```text
Does tools/ still carry any Quant production runtime responsibility?
NO

Does tools/ still contain Quant files?
YES — developer / audit / benchmark / diagnostic tools only
```

## P6 VERDICT

`P6_FULL_PASS`

- Gate A — zero root production authority: PASS.
- Gate B — zero reverse production dependency: PASS.
- Gate C — zero unjustified wrappers: PASS (all wrappers had zero real caller and were deleted).
- Gate D — retained tools are developer-only: PASS.
- Gate E — current docs point at Agent / `zuaef-quant` / plugin modules: PASS.
- Gate F — deployment paths remain valid after wrapper deletion: PASS.
- Gate G — representative semantic smoke: PASS (expected tools, zero generic escapes/substitutions).
- Gate H — no new mechanism: PASS. The P6 diff is deletion, small import/command migrations, tests and docs; no compatibility package, legacy namespace, registry or framework was introduced.

## P7 READY?

**P7 READY: YES.**

P7 is now the model-visible semantic question only: whether legacy broad tools
(`get_trading_context`, `get_live_signals`, `get_analysis_watchlist`,
`update_analysis_watchlist`) still earn their place after the narrow surface
has run in production.  P6 deliberately did not modify that surface; it
removed runtime shadows so P7 can judge vocabulary on evidence rather than
directory structure.
