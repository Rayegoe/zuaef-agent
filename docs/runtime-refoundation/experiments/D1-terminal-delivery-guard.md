# D1 — Terminal Delivery Guard（终局必达保险）

Date: 2026-09-08. Operator directive: phase 1 of the four-phase D1 plan
(user message after incident 9c1c9abb). Status: mechanism tests green; live
business verification pending (next real research run or operator-triggered
run).

## 1. Observe (real traces)

Two production quant research runs ended `limit_reached` AFTER recording
their business deliverable, so the chat user received only a budget notice:

- `77c45d0e` (M2 baseline incident): 12 requests, 25 tool calls,
  746,586 input tokens, 2 unresolved effects.
- `9c1c9abb` (2026-09-08, 002415): 12 requests, 16 tool calls,
  283,570 input tokens, 8m47s. Timeline: `record_decision_brief` completed
  at 09:57:34.593 (full Chinese conclusion on disk: WATCH + why +
  invalidation + trigger facts); request 13 (pure presentation re-statement)
  was rejected at 09:57:35 by `request_limit=12`. The user received nothing.
- Cross-domain recurrence: T006-B2 (writing benchmark) recorded the same
  shape — "reached limit_reached after producing an artifact".

## 2. Classify

The blocked 13th turn was pure PRESENTATION of an already-recorded
deliverable (RUNTIME-2: presenting a finished artifact is not a new semantic
decision). The failure is a delivery/orchestration defect, not a modeling
failure: 预算限制阻止了交付，而不是失控。

## 3. Causal hypothesis

The terminal surface policy treats "no model reply" as "no result", although
the model had already authored the user-facing answer and the host had
already persisted it. Deterministically delivering the domain-marked
deliverable removes the need for the 13th request entirely — no LLM call,
no budget semantics change.

Operator decisions embedded here: the "reserve a final-response budget"
variant was REJECTED (the runtime cannot semantically know which request is
the final one; a reserved N is a magic number). The WORK BUDGET /
FINALIZATION BUDGET split remains a possible later refinement (D1-B phase).

## 4. Change (narrowest, layer-conformant, core untouched)

- Domain (quant plugin): `record_decision_brief` atomically publishes
  `artifacts/quant/briefs/last-reply.json` — the domain-owned reply marker:
  `{recorded_at, decision_id, text}` where `text` is composed mechanically
  from the model-authored brief fields (symbol/action/why/invalidation/
  trigger_facts). No new semantic judgment; the model made the choice when
  it recorded the brief.
- Gateway presentation: `_reply_artifact_text()` reads the marker ONLY when
  `execution_state != completed`, only when the marker is fresh for THIS run
  (`recorded_at >= started_at` — a stale marker from an earlier run is never
  re-delivered), bounded at 2400 chars; `render_terminal(..., reply_artifact=`
  `...)` appends the recorded conclusion under the budget/failed notice
  labeled 已落盘的决策结论（来自运行产物，非重新推理）. All three terminal
  settle paths wired. `/inspect`, Console and receipts unchanged.
- Layer audit: domain knowledge (which artifact is the reply) stays in the
  quant plugin; the gateway only transports a host-readable marker; core
  models/receipt schema/runtime untouched. The marker lives under
  `artifacts/**` which the model cannot write (core protected patterns), so
  a model cannot plant a fake deliverable.

## 5. Evaluation

Mechanism tests (all green, 1268 passed full suite):

- renderer: limit_reached/failed + deliverable → notice + recorded
  conclusion + /inspect, no operational leakage; blank deliverable → bare
  notice unchanged (3 new).
- service: fresh marker → delivered & bounded; stale marker → not delivered;
  missing/corrupt → not delivered; completed run → never; e2e with
  `request_limit=1` reproducing the incident shape → user message contains
  the 002415 conclusion (2 new); no-marker run keeps the honest bare notice.
- quant: `record_decision_brief` publishes the marker atomically with the
  composed text (1 new, real 002415 incident fields as fixture).

Acceptance D1 #1 (已经成功产生 decision_brief 的 Run 绝不能只返回
limit_reached) is satisfied at the mechanism level. Live verification on a
real research run is outstanding and recorded as such.

## 6. Queued next phases (operator plan, NOT executed in this iteration)

- D1-B phase 2: progress-aware budget — soft checkpoint at 12 with
  evidence-based extension (+8), hard emergency ceiling (50–64), per-profile
  configuration. Requires a Core-adjacent runtime change → must go through
  the refoundation gates with a reproduced-failure benchmark (the two
  002415 receipts are the fixtures; acceptance #2: a 20+ request task must
  survive).
- D1-B phase 3: stall detection — same tool+args repetition, repeated
  identical failures (this trace: two run_code failures were the monty
  sandbox rejecting CPython `str % tuple` printf formatting the model
  legally used), no-progress turns → recovery → PARTIAL result. Acceptance
  #3/#4; `/inspect` should distinguish COMPLETED / COMPLETED_PARTIAL /
  STALLED / HARD_LIMIT_REACHED (#5).
## 7. Closure update (2026-09-08 evening)

- **D1-A → PASS (mechanism-level, closed)**: the forced fixture
  `test_twelve_turn_run_with_recorded_brief_still_delivers` reproduces the
  operator's acceptance — `request_limit=12`, twelve real model turns of
  tool work, the brief recorded by turn 12, request 13 rejected by the
  runtime, and the recorded conclusion still delivered to the user. This is
  the mechanism guarantee, not luck. Live production confirmation pending
  the next real >12-turn research run (low probability given D1-C gains).
- **D1-C → MEASURED IMPROVED**: first two post-deploy production runs on
  OPi5 (receipts `78ce147f` 19:58 CST, `505438f3` 20:19 CST, both
  `completed`) vs the 9c1c9abb baseline: 6 req / 10 tools / 159,317 input /
  66% cache-read / 3m32s and 3 req / 4 tools / 55,779 input / 1m50s, vs
  12 / 16 / 283,570 / 28% / 8m47s. Zero failed run_code (was 3).
- **D2 Quant Evidence Accounting implemented (same day, operator
  directive)**: `zuaef_quant/validation.py` computes strategy maturity from
  the canonical ledger — `validation_age_calendar_days`,
  `validation_age_trading_days` (distinct in-session soak scan dates since
  the earliest paper entry: measured operating days, never a calendar
  guess), observation counts split executed/skipped and
  settled-full-horizon(d8)/accumulating, entries/exits, ready/near event
  counts, and a per-symbol lifecycle table (entry date, state, exit
  trigger, position_closed, forward observation settled d1/d5/d8) that
  keeps the position plane and the observation plane explicitly separate
  (the "3× EXIT_ALERT vs settled=2" ambiguity). Served inside
  `get_trading_context`; QUANT_INSTRUCTIONS + quant-research SKILL forbid
  prose estimation ("约三周多" named as the defect) and require quoting the
  block. 8 new tests; full suite 1279 passed.
