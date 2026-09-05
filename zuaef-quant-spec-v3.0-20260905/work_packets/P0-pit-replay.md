# WP1 — PIT-Safe Replay Foundation + Recent 10 Days

## Goal
Create a reproducible historical time-machine that cannot consume future information and cannot contaminate live-forward evidence.

## Tasks
1. Introduce narrow replay clock/data-access seam.
2. Enforce `available_at <= decision_time`.
3. Handle intraday bar completion correctly.
4. Separate replay namespace/store/counters.
5. Implement adversarial leakage tests.
6. Replay most recent 10 trading days at production-equivalent cadence.
7. Settle replay observations and generate a separate replay report.

## Must not
- relabel replay as forward;
- loosen production trigger rules;
- use current index membership blindly for historical dates;
- use later-known financials without availability evidence.

## Acceptance
See `09_REPLAY_SPEC.md` and `16_ACCEPTANCE_CRITERIA.md`.
