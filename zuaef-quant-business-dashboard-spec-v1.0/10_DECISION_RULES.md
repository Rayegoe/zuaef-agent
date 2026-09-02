# 10 — Decision Rules and Anti-Drift Guardrails

## 1. What the business page may say

Allowed:
- “A-tier candidate by current value/quality policy.”
- “Timing trigger not met.”
- “No action candidate.”
- “Forward evidence insufficient.”
- “Valuation is low relative to peers/history.”
- “Data degraded; ranking incomplete.”

Not allowed without evidence:
- “Undervalued” as an objective fact.
- “Will rebound.”
- “High-probability buy.”
- “Proven alpha.”
- “Agent improved return.”

## 2. Legacy position rule

Ownership is not a positive feature.

For every legacy stock ask:

```text
Would this stock enter the candidate pool today if we did not own it?
```

If no:

```text
status = LEGACY_ONLY
```

The system may still show WATCH/HOLD/REDUCE/EXIT reasoning once actual position information exists, but must not lower candidate gates to protect sunk cost.

## 3. Discovery vs timing

```text
Value/Quality rank = “worth researching/watching”
Timing trigger      = “strategy says conditions are present now”
Agent decision      = “given evidence, what bounded action label is justified?”
```

Never collapse these three into one score.

## 4. Development restart rule

After this spec is implemented, freeze again.

Next code work requires a real market/data failure such as:
- candidate coverage persistently too low;
- ranking dominated by obvious value traps;
- sector model misclassifies financials;
- live trigger density remains unusably low over a meaningful observation period;
- candidate refresh is too slow/unreliable in actual operation;
- forward settlements reveal a systematic execution or signal problem.

A desire for a prettier dashboard is not sufficient.
