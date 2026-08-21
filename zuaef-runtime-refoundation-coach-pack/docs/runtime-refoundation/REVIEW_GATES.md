# REVIEW GATES

A reviewer should reject a runtime change when any gate fails.

## G1 — Outcome
Does the business artifact/decision still satisfy its accepted evaluation?

A `null` outcome evaluation cannot justify accepting a runtime change.

## G2 — Evidence
Are factual/effect claims still grounded and integrity rules preserved?

## G3 — Semantic ownership
Did the optimization move a genuine semantic decision into deterministic host code?

If yes, reject.

## G4 — Model-turn necessity
For every new model request:
- what new semantic information arrived?
- what changed that requires another decision?

If neither is clear, flag it.

## G5 — Tool necessity
For every model-visible tool:
- must the model decide timing/arguments?

If not, consider removing it from the model surface.

## G6 — Capability admission
Does every added capability link to reproduced failure evidence?

## G7 — History/state
Is history being searched to rediscover directly representable current state?

## G8 — Unknown convergence
Does missing evidence terminate appropriately?

## G9 — No local Harness clone
Did the change reimplement an upstream primitive?

## G10 — No benchmark cheating
Did the implementation hard-code WCASE fixture content, case IDs or expected outputs?

## G11 — Authority
After the change, which path is production authority?

Ambiguous dual authority is a failure.

## G12 — Complexity regression
If requests/tokens/latency increased, what outcome improvement pays for it?

## G13 — Premise validity
Is the change driven by a failure reproduced on current code, rather than an
expired diagnosis or a stale queue entry?

## G14 — Semantic preselection
Did a host-side ranking/filtering heuristic take over material, excerpt,
technique or experience selection that belongs to the model?

If yes, reject unless an audit proved the dropped content immaterial.

