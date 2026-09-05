# 09 — 10-Day Production-Equivalent PIT-Safe Replay

Priority: P0.

Goal: replay the most recent 10 A-share trading days using current production semantics,
without future leakage and without touching live-forward evidence.

This is NOT the existing GEN1 research evaluator.

For replay point T:
1. runtime clock reports T;
2. every read enforces available_at <= T;
3. incomplete bars are unavailable;
4. future/current index membership cannot leak backward;
5. later revisions cannot leak backward;
6. strategy/config version is explicit.

Cadence:
Use actual production cadence where practical. If a bounded diagnostic cadence is used,
label the deviation explicitly. An EOD-only run cannot claim intraday equivalence.

Per-day output:
- candidate/universe reconstruction status;
- observation count;
- READY/NEAR transitions;
- runtime/data-trust status;
- PIT blocks/degradations;
- decisions;
- D+1/3/5/8 settlement where available;
- MFE/MAE;
- namespace=`replay`.

Acceptance:
- EOD intraday leakage adversarial test blocked;
- future announcement leakage blocked;
- historical membership leakage solved or explicitly blocks/degrades;
- same inputs/config reproduce same result;
- replay never changes live-forward counters/state;
- every zero-trigger day is explained as genuine no-trigger or an explicit evidence/runtime block.
