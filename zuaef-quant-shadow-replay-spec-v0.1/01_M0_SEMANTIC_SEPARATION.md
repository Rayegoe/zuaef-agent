# 01 — M0: Semantic Separation (priority over Shadow PnL)

Goal: make F1 impossible to reproduce. Small, surgical, no architecture
change. Ships before M1.

## M0.1 — Explicit provenance fields

`tools/quant_trading_monitor.py` (the only canonical-ledger writer):

- every position record gains `intent_origin`, `authorization`, `venue`
  (values per 00 §separation);
- every `alerts.jsonl` event gains the same three fields;
- `open_position()` / ack-CLI arguments are extended so the caller must
  state them; default for the ack path is
  `intent_origin=user, authorization=user_ack, venue=paper` (preserves
  current legitimate behavior);
- there is no code path that writes `authorization=user_ack` without the
  ack-CLI; the autonomous path can only produce
  `authorization=autonomous_shadow, venue=shadow` records, and those go
  to Shadow artifacts, never to positions.json.

## M0.2 — Migration of the three existing positions

Empirical disposition (facts as found on 2026-09-09):

- 600519 p-0001 + p-0003: duplicate registrations (补登) of the same
  historical position, no frozen-strategy READY event behind them;
- 601799 p-0001: historical registration, same class;
- 000807 p-0002: historical registration; its 09-07 EXIT_ALERT already
  demonstrates arithmetic corruption (F2: +121% labeled take_profit 6%).

Procedure:

1. rewrite each record's label from `"user BUY acknowledged"` to the
   truth (`note` already says 历史持仓登记/补登): set
   `intent_origin`/`authorization` per what the evidence supports
   (expected: `authorization=none` or `user_ack` only where a real ack
   exists; keep `venue=paper`);
2. deduplicate 600519 (p-0001/p-0003 → one record, other archived);
3. mark all three `legacy_validation_record=true`,
   `admissible_to_shadow=false` — they have no frozen-strategy decision
   provenance, so Shadow must NOT replay them into performance;
4. keep them queryable for audit (never delete canonical history).

If a future audit finds a genuine READY event for a legacy position, it
may be re-admitted as a `shadow legacy replay candidate` with explicit
decision-event citations.

## M0.3 — Fix the mislabeled exit reason path

The `take_profit 6%` label at +121% (F2) is emitted from live price
evaluation. Until data trust is CLEAN, exit-reason labels must include
the computed percentage next to the configured one, e.g.
`take_profit 6% (configured) — observed +121.6% — DATA_TRUST_DEGRADED`,
so arithmetic corruption is visible at the surface instead of laundered
into a strategy term.

## Out of scope for M0

- any change to decision-pipeline semantics (v3.1 owns those);
- PIT remediation itself (v3.1 06/09 own that; this pack only gates on
  it);
- Shadow implementation (M1).
