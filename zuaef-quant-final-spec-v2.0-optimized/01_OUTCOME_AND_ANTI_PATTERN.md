# Outcome Contract + Anti-Pattern Gates

## Product Contract

Current S3 is **fundamental/tradability filtering + short-horizon mean-reversion timing**, with an expected holding period of roughly 2–8 trading days. It is not long-term value investing and it is not the product itself.

Economic hypothesis:

> In sufficiently sound and tradable companies, a sharp short-term decline followed by renewed participation and price stabilization may contain a temporary mispricing that reverts over the next several sessions.

The product contract is broader and stable:

`full market -> small watch universe -> intraday monitor -> action decision -> position management -> real outcome -> learning`

## Primary Business Outcomes

1. **Opportunity compression:** reduce thousands of stocks to a small watch universe that deserves human attention.
2. **Timely assistance:** during trading hours, detect and surface material WATCH/NEAR/READY/INVALIDATED changes without requiring the user to stare at the screen continuously.
3. **Position continuity:** once the user records a trade, continuously evaluate HOLD/REDUCE/EXIT until closure.
4. **Decision clarity:** user understands why, invalidation, risk and what requires action now.
5. **Forward truth:** every real observation/decision can accumulate D+1/3/5/8, MFE/MAE, exit and net outcome.
6. **Learning:** every Research Run reduces a real uncertainty that can improve future selection, timing or position management.

`NO_TRADE` is a valid business outcome only when the system was healthy and genuinely found no eligible opportunity. An unavailable/untrusted system is not `NO_TRADE`.

## Outcome-First Admission Gate

Any new development must answer:

1. What real current failure or uncertainty exists?
2. Does it affect selection, monitoring, position management, capital protection or learning?
3. Why are current capabilities insufficient?
4. What is the smallest change?
5. What real-market or adversarial evidence will prove success?

If it cannot answer these, do not develop it.

## Do Not Let Process Correctness Replace Product Value

A green validator, complete report, passing test suite or well-formed artifact proves only its own scope.

It does **not** prove that:

- the selected stocks are useful;
- the alert arrived in time;
- the position was managed correctly;
- the strategy has positive expectancy;
- the user made a better capital decision.

Business progress must be reported in real operational terms: stocks scanned, watch universe, material alerts, positions monitored, actions surfaced, forward outcomes and comparison to simple controls.

## No Mock/Placeholder Business Outcomes

Fixtures and mocks belong in tests only.

Anything shown as a current business result must come from the real production path or be unmistakably marked unavailable. Do not use placeholder values, fixed demo rows or test fixtures to make the product appear operational.

## No Field-Flow Theater

Wrong:

`Source DTO -> Candidate DTO -> Signal DTO -> Decision DTO -> Report DTO`

If a layer only copies data and adds no new fact, decision or business effect, it is workflow theater.

Right:

`Market facts -> deterministic computation -> decision context -> human action -> forward outcome`

## Minimal Persistent Structure

A new persistent value needs a current consumer: evaluator / validator / renderer / Agent recall / audit / live monitor / position manager.

- No consumer: remove it.
- Quant-local structure does not become Core-wide structure.
- Use stable business references where they reduce duplication.
- Research Log / Lessons / Open Questions remain Markdown-first.
- Numerical observations/trades/runs may use JSON/CSV where appropriate.

## Tool Admission

A new model-visible tool must represent an independent action, permission or effect boundary.

Do not turn every file read or helper function into a tool.

Tool-call count is diagnostic, not success. Many calls without additional decision value = tool theater.

## Architecture Admission

Database / queue / scheduler / vector DB / graph DB / workflow engine / new service require a demonstrated failure that the current system cannot solve adequately.

"May be useful later" is not a reason.
