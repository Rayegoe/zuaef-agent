# Source node: ZUAEF-ASHARE-001 (zuaef-quant) project corpus

Observed 2026-09-02. All resources are in-repo files; evidence locators below are
file paths + section/line references. Nothing in this corpus is inferred — every
claim in the concept nodes traces to one of these resources.

## Canonical resources (fully read)

| Resource | Role | Key evidence |
| --- | --- | --- |
| `docs/quant/README.md` | Implementation summary + 实操指南 (authoritative) | §2 development chain U0–P5.5; §3 architecture/data flow/frozen authority map; §4 honest implementation list; §5 daily operation; §6 restart admission rules & 禁改清单; §7 command cheatsheet & troubleshooting |
| `zuaef-ashare-decision-agent-spec-v1.0-final/00_README.md` | Spec pack entry: definition, objectives, build order | "One-sentence definition"; "Highest-priority rule: Do not build a quant platform"; business outcomes = Decision Brief + Strategy Result only |
| `zuaef-ashare-decision-agent-spec-v1.0-final/02_ARCHITECTURE.md` | Authority boundaries, historical/live paths, forbidden second runtime | §1 authority boundaries; §3 live path "No candidate → no LLM request"; §8 no QuantRuntime/StrategyManager/GateManager |
| `zuaef-ashare-decision-agent-spec-v1.0-final/04_DATA_AND_MARKET.md` | Data principle, cache, A-share execution truth | §1 AKShare not an SLA; §2 P0 smoke; §5 survivorship/PIT; §7 minimum execution truth; §8 never trade on adjusted synthetic price; §9 live 60s poll; §10 data honesty |
| `zuaef-ashare-decision-agent-spec-v1.0-final/05_STRATEGY_AND_EVALUATION.md` | StrategySpec, evaluator, replay, anti-overfit protocol | §1 Strategy = Universe+Entry+Exit+Holding+Risk+Sizing; §4 one material mutation; §6 metrics; §7 independent replay; §9 research/promotion/holdout/forward windows; §10 robustness minimum; §11 no RL |
| `benchmarks/quant/gen1/quant.toml` | Frozen market rules/costs/window dates | execution block (T+1, next_open, slippage 10bps, commission 0.025% min ¥5, lot 100); effective-dated stamp duty & price limits; research/promotion/holdout windows; consistency ≤3pp |
| `benchmarks/quant/gen1/strategy.toml` | gen1 baseline strategy (defaults source) | `volume_pullback_reversal` entry/exit expressions; mutatable fields |
| `benchmarks/quant/gen1/active.toml` | DEMO_ACTIVE_STRATEGY = s3_longer_hold (frozen) | provenance of baseline/S1/S2/S3 annualized numbers; all params |
| `benchmarks/quant/gen1/STATUS.md` | Four-proof state + freeze decisions | P5.5 ENGINEERING FREEZE 2026-09-02; proof table; frozen decisions; known limitations |
| `profiles/quant-decision.toml` | Agent profile | plugin `quant`, allow_capabilities = true; env var contract |
| `data/quant-cache/universe/csi500_subset.meta.json` | Live universe manifest (gitignored) | 37 symbols, selection "sorted codes stride 10", PIT limitation note, excluded lists |
| `tools/quant_live_scan.py` (lines 55–145) | Live scanner internals | universe read from csi500_subset.meta.json; qt.gtimg.cn batch quotes; needs ≥25 daily bars |
| `tools/quant_core.py` (lines 72–165) | History fetch + cache + rules | `fetch_history(symbol, adjust, start_date=20180101)`; cache key `<symbol>_<qfq | raw>`; sidecar meta;`fetch_csi500_constituents` (CSIndex 000905) |
| `tools/quant_eval_qlib.py` (lines 82, 232–235) | Eval pipeline universe usage | rewrites `csi500_subset.txt` from meta; reads symbols from meta |
| `tools/quant_fetch_universe.py` | Universe builder | stride sampling of sorted CSI500 codes; ST & insufficient-lookback exclusion |
| `plugins/zuaef-quant/zuaef_quant/toolset.py` (lines 29–271) | Plugin tools | `_run` subprocess isolation; evaluate_strategy/get_live_signals/record_decision_brief/record_trade_outcome |

## Resources partially observed

| Resource | What was observed | Not observed |
| --- | --- | --- |
| `zuaef-ashare-decision-agent-spec-v1.0-final/01/03/06/07/08/09/10/11/12/13_*.md` | file inventory + README table of contents | full contents — concepts cite 00/02/04/05 only |
| `docs/quant/dashboard.html` | header/title (observation board, self-contained, 72KB) | full page body |
| `tools/quant_render_dashboard.py` | dashboard renderer (moved from workspace/artifacts; committed for cross-host portability) | full body not read
| `tools/quant_core.py` / `quant_eval_qlib.py` full bodies | key functions cited above | full source |

## Verification notes

- Numbers quoted in concepts (annualized returns, trade counts, latencies, bar counts) come from
  `active.toml` provenance block, `STATUS.md`, README §2/§4 — not recomputed here.
- "Quant basics" concepts are the project's own principles (spec 04/05, README §5.5/§6), stated as
  they appear in sources; general-quant definitions beyond the corpus are marked as such.
