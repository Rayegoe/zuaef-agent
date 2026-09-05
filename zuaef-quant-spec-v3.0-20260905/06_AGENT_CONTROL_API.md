# 06 — Agent Control API

## Goal

Let ZUAEF-Agent operate the system through structured actions instead of scraping Dashboard HTML or shelling ad hoc into production state.

## Permission tiers

### L0 — Observe (enable first)

- status
- attention
- candidates
- triggers/decisions
- positions
- observations
- evidence health
- latest report/run metadata
- experiment/replay status

### L1 — Control

- run one scan/tick
- refresh permitted data
- generate report
- settle due observations
- start replay
- start sandbox experiment

### L2 — Decision support

Agent may request evaluation such as entry/exit/participation, but the returned decision is produced by deterministic gates.

### L3 — External execution

Real broker order/cancel is **not part of v3 default enablement**. It requires an explicit external-effect gate and separate acceptance work.

## Suggested CLI surface

```text
quant status --json
quant once --json
quant attention --json
quant candidates --json
quant decision [--symbol SYMBOL] --json
quant positions --json
quant observations --json
quant settle --json
quant replay ... --json
quant experiment ... --json
```

Existing command names should be reused when already present; aliases are acceptable. Do not break working scripts solely to match this spelling.

## Tool/API behavior

All action results should include:

- `schema_version`
- `run_id`
- `as_of`
- `mode` (`production|shadow|replay|scratch`)
- `strategy_version`
- `data_snapshot_id` where applicable
- explicit `status`
- machine-readable `reason_codes`

## Idempotency

Control actions that may be retried must have an idempotency key or deterministic run key. Re-sending a Telegram report must not accidentally create a new trading decision.

## Error taxonomy

At minimum distinguish:

- `MARKET_CLOSED`
- `INSUFFICIENT_EVIDENCE`
- `DATA_STALE`
- `PIT_BLOCKED`
- `NO_TRIGGER`
- `RISK_BLOCKED`
- `RUNTIME_ERROR`
- `EXTERNAL_EFFECT_REQUIRED`

## Agent policy

The Agent is allowed to reason broadly but must not:

- mutate production strategy config silently;
- edit frozen observations/settlements;
- convert experimental results directly into production;
- bypass a deterministic gate;
- issue a real order without the external-effect policy.
