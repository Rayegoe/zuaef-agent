# ZUAEF P3B-2 — Generative Agent Loop Separation

This package is the implementation contract for correcting the recurring ZUAEF failure mode where machine schemas, business fields, gates, and workflow instructions begin to steer the LLM's generation instead of merely supporting, constraining, or verifying it.

## Package contents

1. `PRD.md` — product problem, user outcomes, scope, non-goals, success criteria.
2. `SPEC.md` — normative architecture and implementation contract.
3. `TASKS.md` — task-by-task coding checklist with acceptance gates.
4. `PLAN.md` — commit order, migration strategy, test strategy, rollback points.
5. `PROMPT.md` — ready-to-paste coding-agent execution prompt.

## Baseline

Repository: `Rayegoe/zuaef-agent`
Target branch: `main`
Inspection anchor: 2026-08-19
Observed latest product commits:
- `55f1bec` — P3B-1 authoring presentation / outbound-only approval
- `de6a54b` — interaction-contract documentation

P3B-1 is treated as an important field-failure fix but **not** the final architecture. P3B-2 removes the deeper coupling that made the failure possible.

## One-sentence objective

> Restore the native PydanticAI agent loop as the cognitive and generative center: the model owns judgment and language; tools provide capabilities; host code owns authorization, persistence, verification, and receipts.

## Stop condition

Only declare:

`P3B-2 = 100% — STOP`

when all normative gates in `SPEC.md` and `TASKS.md` pass, including the real-model three-turn proof.
