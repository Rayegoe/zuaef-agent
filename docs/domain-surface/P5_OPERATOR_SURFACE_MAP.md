# Quant Operator Surface Map (P5.0)

| Field | Value |
|---|---|
| Status | P5.0 inventory before/at CLI landing |
| Baseline | P4 engine consolidation complete |
| Scope | Deterministic operator commands only; zero model requests |
| Target binary | `zuaef-quant` (package entry point in `plugins/zuaef-quant/pyproject.toml`) |

P5 gives human/systemd/automation a deterministic entry to the same authorities the
Agent tools already use. It does not add semantic tools, a Core domain registry, a
command framework or a service manager.

## 1. Existing operator actions

| Operator intent | Current entry before P5 | Target CLI | Shared authority | Systemd caller | P5 migration status |
|---|---|---|---|---|---|
| Inspect Quant business/runtime state | ad-hoc reads of `state.json` / `positions.json` / `forward.json` | `zuaef-quant status` | read-only `toolset._read_trading_snapshot` projection (freshness + validation) | none | CLI added |
| Run today's scan | `tools/quant_live_scan.py` / `uv run --group quant python tools/quant_live_scan.py` | `zuaef-quant scan` | `zuaef_quant.scan_sidecar` + `zuaef_quant.scan` entry authority; Agent tool uses the same sidecar module | none | CLI added; root script is thin compatibility wrapper |
| Manage analysis watchlist | chat/model `manage_watchlist`; direct file inspection otherwise | `zuaef-quant watchlist list|add|remove --scope <existing>` | `zuaef_quant.watchlist.update_symbols_in` / `read_symbols_in` | none | CLI added |
| One monitor tick | `.venv/bin/python tools/quant_trading_monitor.py once` | `zuaef-quant monitor once` | same `quant_trading_monitor.py once` production host op | installer smoke | CLI added; monitor implementation still root until P6 |
| Inspect monitor state | `.venv/bin/python tools/quant_trading_monitor.py status` | `zuaef-quant monitor status` | canonical `state.json` + shared trading snapshot | none | CLI added |
| Render business dashboard | `python3 tools/quant_render_business_dashboard.py` | `zuaef-quant dashboard render` | same renderer entry point | none | CLI added |
| Serve dashboard/workbench | `.venv/bin/python tools/quant_serve.py` | `zuaef-quant dashboard serve` | same `quant_serve.py` transport entry | `zuaef-quant-dashboard.service` | CLI added; unit migrated |
| One Telegram bridge tick | `.venv/bin/python tools/quant_telegram_bridge.py` | `zuaef-quant bridge once` | same bridge one-shot entry | `zuaef-quant-bridge.service` + timer | CLI added; unit migrated |
| Long A-share monitor session | `.venv/bin/python tools/quant_trading_monitor.py session ...` | **not in P5 initial surface** | systemd owns the long-running process; P5 adds no start/stop | `zuaef-quant-monitor.service` + timer | intentionally not migrated; P6 candidate |

## 2. Command tree

```text
zuaef-quant status
zuaef-quant scan
zuaef-quant watchlist list|add|remove
zuaef-quant monitor once|status
zuaef-quant dashboard render|serve
zuaef-quant bridge once
```

Top-level commands: 6, all named by real operator intent. No `ask`, `analyze`,
`service`, `run-script`, stage-name or implementation-name command exists.

## 3. Authority rule

| Command | Shared authority after P5 | CLI must not own |
|---|---|---|
| `scan` | `zuaef_quant.scan_sidecar` (same module executed by `run_live_scan`/`get_live_signals`) | trigger clause, quote/history adapter decisions, JSON business schema |
| `watchlist` | `zuaef_quant.watchlist` | symbol normalization, scope slug, write/read-back |
| `monitor once` | `tools/quant_trading_monitor.py once` | cycle calculation, lifecycle, ledger write |
| `monitor status` | shared `_read_trading_snapshot` projection | freshness/validation accounting |
| `dashboard render/serve` | existing renderer/serve entry | HTML rendering and HTTP semantics |
| `bridge once` | existing bridge one-shot | event consumption/delivery semantics |
| `status` | shared read-only `_read_trading_snapshot` projection | P&L, freshness, validation, READY/NEAR calculation |

## 4. Scope decision for watchlist

The repository already has scoped analysis watchlists (bound case id, else chat
channel). There is no implicit operator chat/case scope, and P5 does not invent one.
The CLI therefore requires one of:

```text
--scope <existing-scope>
ZUAEF_QUANT_OPERATOR_SCOPE=<existing-scope>
```

The underlying scope string, file layout, normalization and write path are unchanged.

## 5. Output contract

- default: short human-readable lines only;
- `--json`: one bounded JSON object for automation;
- no default traceback, helper name or unbounded raw payload;
- exit codes: 0 success, 1 operation failed, 2 invalid usage/configuration
  (argparse usage errors already return 2).

## 6. P6 readiness classification

| Root script | P5 classification | Reason |
|---|---|---|
| `tools/quant_live_scan.py` | THIN_COMPAT_WRAPPER | delegates to `zuaef_quant.scan_sidecar`; legacy import/CLI wrapper only |
| `tools/quant_trading_monitor.py` | THIN_COMPAT_WRAPPER | P5.8 moved authority to `zuaef_quant.monitor`; root file forwards legacy args |
| `tools/quant_render_business_dashboard.py` | PRODUCTION_AUTHORITY | stdlib business renderer still implemented here; CLI/systemd share the entry |
| `tools/quant_serve.py` | PRODUCTION_AUTHORITY | operator transport/server still implemented here; CLI/systemd share the entry |
| `tools/quant_telegram_bridge.py` | THIN_COMPAT_WRAPPER | P5.8 moved authority to `zuaef_quant.bridge`; root file forwards legacy args |
| `tools/quant_build_candidates.py` | PRODUCTION_AUTHORITY | candidate-pool refresh/discovery remains an operator/research authority |
| `tools/quant_market_context.py`, `quant_market_intel.py` | PRODUCTION_AUTHORITY | reality adapters still root-owned; P6/P7 boundary |
| `tools/quant_eval_qlib.py` | PRODUCTION_AUTHORITY | isolated evaluator invocation; no root retirement yet |
| `tools/quant_pit_audit.py`, `quant_anti_leakage_check.py`, `quant_p05_reconcile.py`, `quant_p0_data_proof.py` | DEVELOPER_TOOL / BENCHMARK / DIAGNOSTIC | not daily operator surface; may stay in tools |

P6 remains gated because the renderer/serve, candidate discovery, market adapters and evaluator
still own production behavior in root `tools/`. The monitor, bridge, scan and shared quant-core
paths are now thin wrappers over `zuaef_quant`.


> **P5.8 update:** monitor and bridge production authority have since moved into
> `zuaef_quant` (`zuaef_quant/monitor.py`, `zuaef_quant/bridge.py`,
> `zuaef_quant/continuity.py`); the root `tools/quant_trading_monitor.py` and
> `tools/quant_telegram_bridge.py` files are now thin compatibility wrappers.
> See [`P5_8_PRODUCTION_AUTHORITY_REPORT.md`](./P5_8_PRODUCTION_AUTHORITY_REPORT.md).
