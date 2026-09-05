# CLI Contract

The exact executable name may differ; preserve existing working commands and provide compatible aliases/adapters.

## Read actions

```text
quant status --json
quant attention --json
quant candidates --json [--limit N]
quant decision --json [--symbol SYMBOL]
quant positions --json
quant observations --json [--mode live|replay|shadow] [--since ...]
```

## Safe control actions

```text
quant once --json [--idempotency-key KEY]
quant settle --json [--mode live|replay|shadow]
quant replay run --from YYYY-MM-DD --to YYYY-MM-DD --strategy-version V --json
quant replay status --run-id ID --json
quant experiment run --experiment-id ID --mode replay|shadow --json
quant report --json [--mode production|replay|shadow]
```

## Common envelope

```json
{
  "schema_version": "1.0",
  "run_id": "...",
  "mode": "production",
  "as_of": "...",
  "strategy_version": "...",
  "status": "OK",
  "reason_codes": []
}
```

Actions must exit non-zero for true runtime/contract failure, but domain abstentions such as `MARKET_CLOSED` or `NO_TRIGGER` should remain structured results rather than Python tracebacks.
