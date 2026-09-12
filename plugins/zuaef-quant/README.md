# zuaef-quant

ZUAEF-ASHARE-001 P3: QuantDecision capability. Deterministic tools
(evaluate_strategy / run_live_scan / get_market_context /
get_signal_board / get_positions / get_validation_status / manage_watchlist /
record_decision_brief / record_trade_outcome / get_trading_context /
render_quant_business_artifact, plus deferred research tools) over the frozen
gen1 benchmark, the canonical M1 trading state
(`workspace/artifacts/quant/trading/`) and business dashboard delivery
(`artifacts/quant/delivery/`).

Semantic-surface ownership and migration sequencing are tracked in
`docs/domain-surface/SPEC.md`, `QUANT_INTENT_MATRIX.md` and
`QUANT_AUTHORITY_MAP.md`. The narrow intent tools are deferred and discovered
through ToolSearch. Legacy broad/alias tools remain callable and tested but
are deferred compatibility-only, so they do not hold a resident visibility
advantage over the narrow semantic surface.
P5 adds the deterministic operator CLI owned by this package:

```text
zuaef-quant status
zuaef-quant scan
zuaef-quant watchlist list|add|remove --scope <existing-scope>
zuaef-quant monitor once|status
zuaef-quant dashboard render|serve
zuaef-quant bridge once
```

It makes zero model requests by itself and reuses the same scan/watchlist/
monitor/dashboard/bridge authorities as the Agent tools. P5.9 moved the
remaining production authorities (market context/intel, candidate sidecar,
evaluator sidecar, dashboard render/serve) into this package; root
`tools/quant_*` now contains only developer/audit/benchmark tools; production
compatibility wrappers were retired in P6.

Heavy quant deps (akshare, qlib) run in the `.venv-quant` side environment;
the plugin package is the production implementation owner and carries no
data stack in the Agent environment.
Profile: `profiles/quant-decision.toml` (`allow_capabilities = true`).
