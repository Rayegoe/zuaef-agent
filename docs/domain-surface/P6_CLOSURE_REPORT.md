# P6 Closure Report — Pre-P7 Boundary Cleanup

Status: **P6_STRICT_FULL_PASS — P7 READY: YES**
Spec: "ZUAEF Quant P6 Closure — Pre-P7 Boundary Cleanup Spec v0.1"
Prerequisite: `P6_FULL_PASS` (`P6_SHADOW_LAYER_RETIREMENT_REPORT.md`)
Raw smoke evidence: `P6_CLOSURE_SMOKE_RESULTS.json`

---

## QUANT_DAILY_CALLER_RESULT

**0 real production / deployment / operator callers.** Full-repo inventory:

| Class | Hits |
|---|---|
| REAL PRODUCTION CALLER (systemd/cron/code) | **0** — repo units (`ops/systemd/*`) and installed user units never reference it; no crontab entries; zero code/test callers; not in `BUILD_MANIFEST.json` |
| CURRENT DOC | `docs/quant/README.md` (convenience pointer + artifact provenance + invariant line), `ops/systemd/README.md` ("superseded, do NOT schedule"), `ops/install_orangepi_node.sh` ("do NOT schedule"), `QUANT_AUTHORITY_MAP.md` (classification row) |
| HISTORICAL DOC | `benchmarks/quant/gen1/STATUS.md` (dated checkpoint), P6/P5.9 reports, spec packs, M1/baseline artifacts — left untouched |

## QUANT_DAILY_ACTION

**deleted** (`git rm tools/quant_daily.sh`). Case A: the monitor + bridge systemd loop and the documented Agent path (README §5.2) fully replace it; its unique automations (observation-log append, engineering dashboard render) are already documented as manual/standalone. The last writer of `workspace/artifacts/quant/business/last_scan.json` is gone by design; `last_scan_at` now resolves via the designed monitor-soak fallback (`trading._resolve_last_scan_at`), documented in `docs/quant/README.md`.

## DOUBLE_SCAN_STATUS

**eliminated** (Gate B trivially): no external workflow pre-runs Scan A anymore. One daily decision = one Agent-owned scan (`get_live_signals` → `zuaef_quant.scan_sidecar`) → one Decision Brief → manual observation-log line (README §5.3).

## OPERATOR_REVERSE_DEPENDENCIES

- **before**: `ops → toolset._read_trading_snapshot` (ops.py:144-147) and `ops → plugin.resolve_quant_python` (ops.py:77-80).
- **after**: `ops → zuaef_quant.trading.read_trading_snapshot` and `ops → zuaef_quant.runtime.resolve_quant_python` (with a loud `OperatorError` when the side env is missing — previously a `CompositionError` traceback leaked through the CLI).
- Guard: `test_operator_layer_has_no_model_layer_reverse_dependency` (static, `tests/test_quant_production_authority.py`). Gate C: `ops -X-> toolset`, `ops -X-> plugin`; `ops → runtime/trading/watchlist/sidecars` holds.

Also removed the mirror-image reverse dependency `plugin → toolset.REPO_ROOT`: plugin's resolver is now a thin validation adapter over `runtime.resolve_quant_python()` (same `CompositionError` composition semantics, spec §16-17).

## TRADING_SNAPSHOT_AUTHORITY

**`zuaef_quant.trading.read_trading_snapshot`** — moved (not copied) from `toolset._read_trading_snapshot` together with its exclusive private readers (`_read_json`, `_read_jsonl_tail`, `_read_jsonl`, `_resolve_last_scan_at`). Consumers: toolset (4 observe tools) and ops (`status`/`monitor status`). No second implementation (Gate D guard: `test_trading_snapshot_and_path_rules_have_one_authority`). `trading.py` remains stdlib-only/side-env importable; the arithmetic helpers keep their no-I/O contract, and the module docstring now scopes `read_trading_snapshot` as the one bounded reader.

## QUANT_PYTHON_RESOLUTION_AUTHORITY

**`zuaef_quant.runtime.resolve_quant_python`** owns the path rules (`ZUAEF_QUANT_PYTHON`, `.venv-quant/bin/python`); `plugin.resolve_quant_python()` only translates an unavailable interpreter into `CompositionError`; `ops._quant_python()` translates it into `OperatorError`. The duplicated constants in plugin.py were deleted (single definition in runtime).

**Incident found by the Gate J smoke**: `runtime` applied `Path.resolve()` to the env-configured interpreter. A symlinked uv venv python (`.venv-quant/bin/python` → base cpython) lost its `pyvenv.cfg` context when resolved, and the bare base interpreter cannot import pandas — the explicit-scan run failed. Fixed: `expanduser()` only, never `resolve()` (this also fixes the same latent bug in `dashboard/serve.py` when `ZUAEF_QUANT_PYTHON` is set). Verified by clean real-model reruns.

## ROOT QUANT INVENTORY

Guard now scans `tools/quant_*` of **all file types** (spec §23) and asserts equality with an explicit allowlist — no generic classifier (spec §25):

`quant_anti_leakage_check.py` (BENCHMARK/AUDIT), `quant_p05_reconcile.py` (BENCHMARK), `quant_p0_data_proof.py` (BENCHMARK), `quant_v31.py` (BENCHMARK), `quant_pit_audit.py` (AUDIT), `quant_validate_semantics.py` (AUDIT), `quant_fetch_universe.py` (DEVELOPER), `quant_render_dashboard.py` (DIAGNOSTIC, now standalone since the daily script is gone).

Note: `tools/quant_render_dashboard.py` still renders a stale "cannot locate repository quant tooling" troubleshooting row into the engineering page; it is out of this closure's declared scope and is recorded here as residual cleanup for its next touch.

## STALE CURRENT REFERENCES REMOVED

- Wrapper docstrings → current facts: `bridge.py`, `market_context.py`, `candidates_sidecar.py`, `toolset._live_scan_payload` ("root tool path is only a legacy import wrapper" removed).
- `docs/quant/README.md`: `一键版 bash tools/quant_daily.sh` pointer removed; `last_scan.json` provenance corrected; empty-universe invariant re-worded to `zuaef-quant scan` / `/api/scan`; the nonexistent "quant plugin cannot locate the repository quant tooling" failure row replaced with the real `required command is unavailable` semantics.
- `ops/systemd/README.md` + `ops/install_orangepi_node.sh`: "do not reintroduce" wording updated to the deletion fact.
- `QUANT_AUTHORITY_MAP.md`: `tools/quant_daily.sh` row → DELETED (P6 closure).
- Knowledge nodes (current, Gate F): `quant-live-ops.md` (monitor CLI → `-m zuaef_quant.monitor`, quick-look → `zuaef-quant scan`, stale error row, source frontmatter), `quant-telegram-workbench.md` (frontmatter + diagram module names), `quant-strategy-mechanics.md`, `quant-data-plane.md` (scan/eval sidecar refs, stale error string), `zuaef-quant-overview.md`, `sources/zuaef-quant.md` (wrapper paths → current `zuaef_quant.*` locations, with a dated update note). Historical/spec-pack references untouched.
- Status refresh: `AGENTS.md`, root `README.md`, `docs/domain-surface/SPEC.md` (§ status + §15 phase table), `docs/architecture/CONSOLIDATION_SPEC.md`, `QUANT_INTENT_MATRIX.md` — all now state: P6 executed + closure complete; P7 READY, not started.

## LEGACY SEMANTIC TOOL CALLER BASELINE

Classification per spec §29-30 (model registration ≠ production caller; tests/old reports are not retention evidence):

| Tool | MODEL TOOL REGISTRATION | REAL PRODUCTION CALLER | OPERATOR CALLER | TESTS | CURRENT DOC | HISTORICAL DOC |
|---|---|---|---|---|---|---|
| `get_trading_context` | toolset (deferred); code_mode sandbox list | **bridge E1/E2 agent-run prompt** ("First call get_trading_context", `bridge.py`) + `QUANT_INSTRUCTIONS` usage guidance | none (ops reads `trading.read_trading_snapshot` directly) | freshness / plugin / semantic_surface / telegram_bridge / tool_disclosure | README §3/§4/§5, plugin README, quant-research SKILL, knowledge nodes | P3/P4 reports, m2 evidence, spec packs, `_bmad-output` reviews |
| `get_live_signals` | toolset (deferred); code_mode sandbox list | **the documented daily decision prompt** (README §5.2 and knowledge `quant-live-ops.md` require it as FIRST tool call) | none (`zuaef-quant scan` runs the sidecar directly) | plugin / semantic_surface (same-engine proof) / tool_disclosure | README §4/§7, AUTHORITY_MAP, INTENT_MATRIX, SPEC | P3/P4 reports, m2 evidence, spec packs |
| `get_analysis_watchlist` | toolset (deferred alias of `manage_watchlist` list semantics); sandbox list | **none** | none (`zuaef-quant watchlist` → `watchlist_store` directly) | watchlist / semantic_surface / tool_disclosure | SPEC, INTENT_MATRIX, AUTHORITY_MAP, SKILL fallback mention | m2 evidence |
| `update_analysis_watchlist` | toolset (deferred alias of `manage_watchlist` writes); sandbox list | **none** | none | watchlist (6 call sites) / semantic_surface / tool_disclosure | SPEC, INTENT_MATRIX, AUTHORITY_MAP | m2 evidence |

**§31 answer** — "besides the model itself, does any current production system require the legacy semantic tools?" Two documented prompt-level dependencies exist: the **daily decision prompt requires `get_live_signals`** and the **bridge E1/E2 prompt requires `get_trading_context`**. The two watchlist aliases have **zero** non-registration callers anywhere. P7 must therefore treat prompt re-authoring as part of any retirement of the first two; the aliases are pure vocabulary decisions.

## TESTS

- Full suite (`uv`-less venv run): **1192+ passed** across the quant sweep + manifest + integrity + architecture guards, including the new/extended P6-closure guards (all-file-type root inventory, daily-workflow absence, operator-layer neutrality, one-authority). Test fallout fixed where the projection moved: `test_quant_freshness.py`, `test_quant_semantic_surface.py` (monkeypatch now targets `zuaef_quant.trading.now_market`), `test_quant_plugin.py` (resolver signature).
- Lint: `ruff check` clean on all changed files.
- Manifest: surgical bytes+sha256 updates for every changed tracked file; also repaired a **pre-existing** `.gitignore` entry drift left by `22dacd3` (it blocked the integrity gate).
- Pre-existing failures on HEAD, unrelated to this closure, left as-is: `tests/test_quant_hydration.py` / `tests/test_quant_v31.py` cannot collect in the main venv (`No module named 'pandas'`); `tests/test_quant_research.py::TestMarketIntelAdapter::test_bounded_items_with_source_and_time` fails identically with the change stashed (mocked feed needs a pandas-shaped frame).

## REAL-MODEL SMOKE

3/3 completed, expected narrow tool each, 0 legacy substitution, 0 generic escape, 0 execution failure (model `deepseek/deepseek-v4-flash-0731`, isolated /tmp workspaces):

| Key | Tool sequence |
|---|---|
| Positions | `search_tools → get_positions` |
| Explicit Scan | `search_tools → run_live_scan` (after the resolve() fix; 1 failed attempt pre-fix, recorded honestly in the smoke JSON) |
| Market-wide | `search_tools → get_market_context` |

Operator smoke (Gate I): `status` / `scan` (50/50 quotes, volume semantics PASS) / `monitor once` (MARKET_CLOSED tick) / `dashboard render` / `bridge once --dry-run` — all exit 0.

## P6 CLOSURE VERDICT

- Root tools product workflow = 0 (deleted + guarded) ✅
- Double scan = 0 ✅
- `ops → toolset` reverse dependency = 0 ✅
- `ops → plugin` runtime dependency = 0 ✅
- Root quant inventory completely classified (all file types) ✅
- Current docs match current architecture ✅
- Model semantic surface unchanged (names, count, defer topology) ✅

**P6_STRICT_FULL_PASS**

## P7 READY

**P7 READY: YES.** No hidden mechanism makes a legacy semantic tool look undeletable: the two real dependencies are explicit prompt texts (re-authorable in P7), the alias tools have no callers, and the caller baseline above is the P7 input. Per spec §46, P7 may now judge `get_trading_context` / `get_live_signals` / `get_analysis_watchlist` / `update_analysis_watchlist` on Intent, Reality coverage and model behavior.
