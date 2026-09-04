# zuaef-quant

ZUAEF-ASHARE-001 P3: QuantDecision capability. Six deterministic tools
(evaluate_strategy / get_live_signals / record_decision_brief /
record_trade_outcome / get_trading_context / render_quant_business_artifact)
over the frozen gen1 benchmark, the canonical M1 trading state
(`workspace/artifacts/quant/trading/`) and business dashboard delivery
(`artifacts/quant/delivery/`). Heavy quant deps (akshare, qlib) run in the
`.venv-quant` side environment (see repo `docs/` and `tools/quant_*`); this
plugin carries no data stack. Profile: `profiles/quant-decision.toml`
(`allow_capabilities = true`).
