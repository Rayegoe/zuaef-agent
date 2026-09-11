# 02 — M1: Deterministic Shadow Replay Projection

Goal: one small deterministic projector that answers, under explicit and
conservative execution assumptions: "if the frozen strategy were executed
mechanically, what would the account look like?"

Not a broker. Not a paper-trading system. No order books, no partial
fills, no queue simulation, no VWAP/TWAP — those are later fidelity
upgrades with their own admission evidence.

## Shape

```python
replay(
    decision_events,     # READY / EXIT from the decision event store
    market_evidence,     # PIT market execution data + corporate actions
    execution_policy,    # frozen AshareExecutionPolicy v0.1 (below)
    initial_capital,     # explicit, fixed, versioned
) -> ShadowResult         # trades / positions / nav / metrics
```

Implementation target: a few hundred lines, pure projection, no hidden
state (no "append current position", no "update mutable balance", no
"load yesterday state"). Host-side deterministic computation — zero model
requests, zero Agent tool calls (progress telemetry / budget rules
unaffected).

## Inputs

- Decision events: only persisted frozen-strategy `READY` / `EXIT`
  events (symbol, ts, strategy id). LLM text is never an input; the
  Agent may later *explain* Shadow output but never influence it.
- Market execution data: local PIT store opens (the vendored dump_bin
  pipeline already builds this), each bar with `available_at`.
- Corporate-action data: dividends/splits with quantity adjustment, cost
  adjustment, `effective_date`, `available_at`. A position held across a
  corporate action must be adjusted; missing corporate-action evidence
  degrades that symbol (see Evidence Gate), it is not silently ignored
  (000807 F2 is the reproduced failure class).
- No Qlib Account / vn.py / RQAlpha runtime dependency in v0.1.

## AshareExecutionPolicy v0.1 (frozen, versioned)

```text
BUY   READY at T  → earliest execution T+1 → first tradable open
                  → fill = open × (1 + 10bp)
SELL  EXIT at T   → earliest legal execution (T+1 for shares bought T+1,
                  same/next tradable open thereafter)
                  → fill = open × (1 − 10bp)
Constraints:
  T+1 (shares not sellable on buy day)
  suspended day            → no fill, roll to next tradable open
  one-word limit-up open   → BUY not filled (NOT_FILLED)
  one-word limit-down open → SELL not filled (NOT_FILLED)
  lot size = 100           → round down
  insufficient cash        → reject intent (recorded, never silently clipped)
```

Anything not listed is out of scope for v0.1.

## Outputs (all derived, all deletable)

```text
workspace/artifacts/quant/shadow/
  trades.jsonl          ordered fills with policy version + rule applied
  positions.json        projection of decision events × market evidence
  nav.jsonl             daily NAV series
  performance.json      metrics + evidence_gate block
```

`positions.json` (canonical) is NOT touched by any of this; it stops
being called "仓位真相" in prose — it is the projection of user-ack
transactions, and Shadow state lives entirely under `shadow/`.

## Canonical serialization (determinism contract)

Determinism is byte-level, so the writer must be canonical:

- fixed JSON key order (sorted), fixed indentation, UTF-8, `\n` endings;
- fixed symbol ordering (sorted), fixed event ordering (ts, then symbol,
  then type);
- fixed decimal precision for prices/quantities/metrics (explicit
  quantization, never float repr);
- fixed timezone (+08:00) for all emitted timestamps;
- `input_as_of` (data boundary) is allowed; wall-clock `generated_at`
  and random UUIDs are forbidden inside canonical artifacts;
- replay outputs must never mutate live-forward counters or state
  (v3.1 §09 rule reused).

## Four hard gates

```text
A. Isolation      Shadow never writes the canonical ledger or anything
                  outside workspace/artifacts/quant/shadow/; no model
                  calls; no new runtime dependencies.
B. Reconstruction rm -rf the shadow dir + rerun → complete rebuild.
C. Determinism    same inputs → byte-identical outputs (diff -ru = 0,
                  two independent runs, see 03).
D. Evidence       PIT != CLEAN → Shadow runs, engineering facts are
                  valid, performance conclusions are not admissible;
                  surfaces render the 00 §Evidence Gate block.
```
