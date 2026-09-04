# P0 — Data & Execution Truth

**Business question:** 我们今天看到、历史比较和持仓计算的，是否是同一个真实市场事实？

P0 is a supporting truth layer for the trading loop. It must block false opportunities and false position actions, but it must not become the product itself.

## P0.1 Volume + Live Timing Semantic Truth

Historical cached volume must use one defined internal meaning (`shares / 股`) after ingestion. Live quote volume must be converted to the same meaning before comparison.

The proof has two responsibilities and must not conflate them:

### Persistent ingest truth

Can current caches be trusted as canonical inputs?

- active universe fully covered;
- current cache contract satisfied;
- canonical volume meaning established;
- old/unqualified caches are invalidated/rebuilt rather than silently reused.

### Current quote health

Does today's quote look compatible with the expected live source semantics?

- detectable live anomaly => fail actionable evaluation;
- same-day EOD comparison not yet available during market hours may be `PENDING`, not automatically "historical semantics unknown";
- if persistent ingest truth itself is insufficient, fail closed.

Timing calculations must be aligned to the quote's effective trading date. A quote at T may not consume history later than T.

Any deliberately future-extended history must produce the same T-state as date-bounded history under the correct implementation.

## P0.2 Semantic Quality ≠ Coverage

Data quality dimensions remain separate:

- coverage;
- freshness;
- semantic integrity;
- source degradation;
- PIT.

`coverage=100%` never implies overall trust.

A trust failure must be translated into business consequence: current action unavailable, historical profitability untrusted, or both.

## P0.3 PIT

Historical research must explicitly review:

- index membership as-of;
- financial report period;
- announcement/effective date;
- historical valuation as-of;
- adjustment semantics.

States:

`PIT_CLEAN / PIT_PARTIAL / PIT_CONTAMINATED`

No announcement/effective availability proof means report period cannot be treated as the historical usable date.

A contaminated historical universe may still coexist with a valid current live universe. Do not collapse live and historical truth into one statement.

## P0.4 Scoped Anti-Leakage Behavior

Use behavioral/adversarial checks, not only source inspection.

### Historical replay invariance

Compare full-history execution with date-sliced/truncated execution and compare only facts that should already exist by historical date D:

- factor values;
- candidate membership where the candidate definition is historically reconstructable;
- entry intents;
- exit intents.

Removing future rows must not change past values.

### Production timing adversarial check

Pass a T quote to:

- history bounded at T;
- history containing extreme future rows.

The T result must remain identical.

The adversarial test must be able to fail a known tail-relative implementation; otherwise it has no evidentiary value.

### Scope honesty

A PASS proves only the tested surface. It does not erase PIT contamination, historically unreconstructable candidate ranking, unsupported market events or other untested paths.

## P0.5 Independent Execution + Portfolio Accounting Truth

Keep Qlib and `quant_core` as two different roles:

- Qlib = research efficiency;
- `quant_core` = independent A-share execution/accounting truth.

At minimum verify/implement real semantics for:

- T+1 / next-open execution;
- price limits;
- suspension/no-bar execution;
- board-lot sizing;
- commission/minimum commission;
- effective sell-side tax;
- slippage;
- total return measured from initial capital;
- no-bar position valuation using the last valid market close rather than reverting to entry cost;
- corporate actions either correctly accounted for or explicitly detected/excluded from trusted replay claims.

Dual-engine reconciliation is trade-level first. Differences are acceptable when they are explained by real A-share market rules or explicitly unsupported events. Do not force parity by weakening market truth.
