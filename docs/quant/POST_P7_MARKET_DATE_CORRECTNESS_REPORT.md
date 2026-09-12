# Post-P7 Market Date Correctness Report (R1)

Status: **MARKET_DATE_CORRECTNESS_PASS**
Spec: ZUAEF Quant Post-P7 Production Reliability Closure Spec v0.1, Part I
Commit: `55b8f26` (`fix(quant): distinguish non-trading days and incomplete scans`)
Raw evidence: `docs/quant/POST_P7_RELIABILITY_RESULTS.json`
Model: `deepseek/deepseek-v4-flash-0731` (production `.env`), real wall clock
Saturday 2026-09-12 over controlled Friday-end fixtures.

## REPRODUCED FAILURE

On 2026-09-12 (Saturday) a production Feishu run answered
`重新扫描一下今天的候选池` with wording equivalent to "今天的数据还没有进入缓存，
等 9-12 收盘数据落地后再扫描". 2026-09-12 is a non-trading day; that closing
dataset will never exist. A second answer read `READY=[] NEAR=[]`
`symbols_scanned=0 data_trust=UNKNOWN` as a proven zero-trigger conclusion.

## ROOT CAUSE

The system exposed dates and freshness but never projected the
market-calendar fact. `freshness.py::_is_weekday` (the deterministic
weekday rule, mirroring `monitor.market_phase`'s weekend branch) was private
and its verdict reached no model-facing payload. `derive_freshness` returned
`STALE` on a Saturday with a reason ("latest market data is from …, before
the requested day") that invites the "today's data is delayed" inference.
Scan completeness (`symbols_scanned` × `data_trust` × scan-record
visibility) was left for the model to conjoin, and the production run
proved it does not.

## EXISTING AUTHORITY REUSED

- `monitor.market_phase` weekend rule (`weekday() >= 5 → MARKET_CLOSED`) —
  promoted to a public, agent-side, stdlib fact; no holiday calendar exists
  in this deployment, so a weekday holiday honestly reads as a trading day
  whose data has not arrived.
- `derive_freshness` — the single freshness derivation; extended, not
  replaced. `get_signal_board` / `get_positions` / `get_trading_context` /
  monitor `symbol-context` project it unchanged.
- `state.json` scan facts (`symbols_scanned`, `data_trust`) and
  `last_scan_at` resolution — now conjoined by the host instead of the model.

## FIELDS / SEMANTICS CHANGED

- `freshness.market_day_status(date) → TRADING_DAY | NON_TRADING_DAY`
  (new public derivation over the existing weekday rule; no new
  model-visible tool).
- `derive_freshness` result gains `requested_market_day_status`; on a
  non-trading day the STALE reason states the calendar fact and names the
  latest valid market day instead of implying a data delay. Freshness and
  calendar remain separate dimensions (STALE on a weekend is intentional).
- `get_signal_board` and `get_trading_context` payloads gain
  `requested_market_day_status`; `run_live_scan` returns a bounded
  refusal on a non-trading day: `status=NON_TRADING_DAY`,
  `scan_executed=false`, requested/latest/last-scan dates. An explicit
  `用最新有效行情重新算` request uses
  `run_live_scan(recalculate_latest=true)` and the result is labeled
  `RECALCULATION_ON_LATEST_VALID_MARKET_DATA` — a diagnostic operation over
  the payload's quote dates, never a same-day scan.
- Monitor `symbol-context` scan block carries
  `requested_market_day_status` for operator parity.

## ZERO-OBSERVATION FIX

`read_trading_snapshot` (the single projection read) now derives
`scan_conclusion`:

- `COMPLETED_ZERO_TRIGGER` / `COMPLETED_WITH_TRIGGERS` require a visible
  last-scan record, `symbols_scanned > 0`, and `data_trust == "PASS"`;
- `data_trust` FAIL/UNKNOWN (volume gate suppression) and any
  missing/zero-scan evidence yield `NO_VALID_SCAN_EVIDENCE`.

Empty READY/NEAR alone can no longer be read as a proven zero-trigger
result; the board and context payloads project the conclusion and their
`limitations` state the rule.

## TEST MATRIX (deterministic, injected clocks/fixtures)

Saturday, Sunday (calendar fact + STALE reason content), weekday
TRADING_DAY, trading day before scan window (MARKET_NOT_OPEN, still
TRADING_DAY), after-close stale, stale with invisible scan record,
completed-scan zero trigger, zero-scanned symbols (`NO_VALID_SCAN_EVIDENCE`),
`data_trust=FAIL` suppression, completed scan with triggers, non-trading-day
scan refusal, `recalculate_latest` labeling, instruction-contract pins.
All in `tests/test_quant_freshness.py` + `tests/test_quant_semantic_surface.py`.
Full sweep: 169 passed / 6 skipped; ruff clean; manifest integrity green.
Pre-existing unrelated failures (pandas-dependent collections, one
market-intel adapter test) are identical on the pre-change tree and remain
documented in the results JSON.

## REAL-MODEL CANARIES (fresh sessions, real clock Saturday)

- **M1 `今天有什么机会？` → PASS** — "今天（9月12日）是非交易日，本身不会有当天
  的扫描结果。最近一个有效交易日是9月11日…"， zero triggers attributed to the
  completed Friday scan (scan_conclusion), recalc offered as a labeled
  option, no wait-for-close wording.
- **M2 `重新扫描一下今天。` → PASS** — `run_live_scan` returned the refusal
  (`scan_executed=false`, no sidecar execution); answer: "没有可执行的当日
  扫描——系统不会把上一个交易日的行情当成今天的扫描结果".
- **M3 `那就用最新有效行情重新算一下。` → PASS** — model passed
  `recalculate_latest=true`; the real sidecar scanned Friday quotes; answer
  labeled it "诊断性重算…不是今天的扫描", reported per-clause facts, no
  fabricated signals.

## VERDICT

**MARKET_DATE_CORRECTNESS_PASS** — the R1 gate holds: non-trading days are
explicit; the system never waits for a weekend/holiday close; zero scan
evidence cannot pass for a zero-trigger result; stale recomputation is
labeled honestly; no new model tool was added; strategy, scan, ledger and
PIT semantics are unchanged.
