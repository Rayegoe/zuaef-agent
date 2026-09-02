# zuaef-quant

ZUAEF-ASHARE-001 P3: QuantDecision capability. Three deterministic tools
(evaluate_strategy / get_live_signals / record_trade_outcome) over the
frozen gen1 benchmark. Heavy quant deps (akshare, qlib) run in the
`.venv-quant` side environment (see repo `docs/` and `tools/quant_*`); this
plugin carries no data stack. Profile: `profiles/quant-decision.toml`
(`allow_capabilities = true`).
