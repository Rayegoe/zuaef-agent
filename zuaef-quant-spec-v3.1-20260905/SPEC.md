# SPEC — ZUAEF Quant v3.1

Normative requirements are distributed across:
- `00_SOURCE_OF_TRUTH.md`
- `01_CURRENT_IMPLEMENTATION_CONTRACT.md`
- `03_ARCHITECTURE.md`
- `05_AGENT_SURFACE.md`
- `06_DATA_AND_PIT.md`
- `07_EVIDENCE_NAMESPACES.md`
- `09_PIT_SAFE_REPLAY.md`
- `10_MARKET_REGIME.md`
- `12_EXPERIMENT_SYSTEM.md`
- `14_OBSERVABILITY_TELEGRAM.md`
- `16_ACCEPTANCE.md`
- `17_SECURITY_AND_INVARIANTS.md`

Core non-negotiables:
1. preserve current live runtime;
2. six-tool gap audit before new model-visible tools;
3. Bridge remains single proactive delivery authority;
4. Workbench writes remain loopback-only;
5. market_no_trade is not Market Regime;
6. research != replay != shadow != live_forward;
7. strict replay blocks future data;
8. replay never changes production/live-forward state;
9. D+1/3/5/8 is the common forward horizon contract;
10. HUMAN_SKIP is first-class evidence;
11. existing evaluator is reused, not casually replaced;
12. real-money broker execution is out of scope.
