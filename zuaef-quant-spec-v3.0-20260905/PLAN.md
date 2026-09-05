# PLAN — Implementation Order

## Phase 0 — freeze reality

Do not start by refactoring. Inspect the local running tree, running services, state, logs, and latest reports. Record what is actually running and whether local changes are ahead of Git.

## Phase 1 — add observation/control seams

Create structured status/actions around existing behavior. This gives Agent and Code a reliable control surface without moving the working Quant core.

## Phase 2 — build the time machine

Introduce the narrow replay clock/as-of boundary and separate evidence namespace. Prove with adversarial tests that future data cannot affect a past decision. Run the recent 10-day replay.

## Phase 3 — add research intelligence in shadow

Add Market Regime and priority evidence retrieval. They start as shadow/context, not as immediate production-rule changes.

## Phase 4 — enable controlled experimentation

Add experiment lifecycle and S0/S1/S2 isolation. Let Agent/Code test hypotheses without mutating production.

## Phase 5 — accumulate real forward evidence

Keep production frozen while live data settles. At 20 trading days or 30 settled forward triggers, whichever comes first, conduct the formal M1 audit if the evidence pipeline has no unresolved integrity failures.

## Phase 6 — promote or reject

Only experiments surviving replay → shadow → new forward evidence can become a new versioned production strategy. Real broker execution remains a separate later decision.
