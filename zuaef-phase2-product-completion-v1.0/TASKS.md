# TASKS — Phase 2 Execution Ledger

Allowed outcomes:

```text
PASS
KEEP
WRAP
DELETE
DORMANT
BLOCKED
```

## P2-T001 — Freeze current main

Run baseline tests/lint and record HEAD. Confirm Phase-1 READY facts. Do not refactor.

## P2-T002 — Add RED tests for remaining product gaps

Add focused tests for:
- profile generalist policy;
- frozen authorization identity;
- `stillevo-fde` initial business tool surface;
- Gateway Case binding;
- bound Case isolation;
- literal Turn-2 prompt/no hidden constraint reinjection.

## P2-T003 — Add profile-level generalist policy

Implement minimal `[generalist]` profile schema.

Rules:

```text
effective = host ceiling AND profile request
```

Tests:
- profile requests Web but host denies → Web absent;
- host allows + profile requests → Web available;
- profile does not request Shell → Shell absent;
- policy changes composition ID;
- resume from frozen snapshot reproduces old policy.

## P2-T004 — Configure `stillevo-fde` generalist policy

Recommended:

```text
web_search = true
web_fetch = true
tool_search = true
memory = true
conversation_search = true
context_controls = true
subagents = true
shell = false
repo_context = false
```

## P2-T005 — Add deferred business-tool composition

Use released PydanticAI deferred-loading/ToolSearch support.

Add the smallest profile/composition marker, e.g. `defer_tools`.

Freeze it in PluginRef/CompositionSnapshot identity.

Mechanically wrap existing plugin Toolsets. Do not rewrite plugin business logic.

## P2-T006 — Configure `stillevo-fde` progressive disclosure

Target:

```text
zuaef-case          eager
client-service      deferred
ace-writing         deferred
zuaef-emtb-budget   deferred
wordpress           deferred
```

Required deterministic test:
- initial tool surface includes Case orientation + discovery;
- writing tools absent before load;
- writing tools appear after load;
- budget/wordpress remain absent/dormant.

## P2-T007 — Add durable Gateway Case binding

Extend existing Gateway SQLite/store/session model.

Required mapping:

```text
surface + tenant + channel + thread
→ case_id
```

Add one supervisor/admin binding operation.

Tests:
- binding survives reopen;
- session resolves binding;
- `/new` creates a new conversation but keeps business Case binding unless explicitly unbound;
- profile switch does not silently change Case.

## P2-T008 — Thread bound Case into execution deps

Add optional server-owned `case_id` to CoreDeps or equivalent.

Gateway passes resolved Case.

Case tool behavior:

```text
if deps.case_id is set:
    requested case_id must equal deps.case_id
```

Tests:
- bound Case read succeeds;
- another Case read/write/send is rejected;
- explicit unbound backward-compatible fixtures still work.

## P2-T009 — Productize Case resource references

Use existing Case state to expose production resource refs needed by domain capability.

For proof Case, persist ACE article/material workspace reference in Case state or equivalent existing data.

Do not create a capability binding registry.

## P2-T010 — Rewrite authoritative two-turn proof

Refactor existing `tools/fde_two_turn_proof.py`.

MUST use:

```text
GatewayService
profile=stillevo-fde
bound Case
real model
real StepPersistence
real Case
real ACE materials
```

Transport may be RecordingSurface.

Turn 1 and Turn 2 must be exactly SPEC text.

No hidden context restatement.

Capture case_id, conversation_id, run ids, initial/loaded tool surface, invoked tools, dormant domains, Case reads/writes, material refs, artifacts, price scan, publish calls, pause/approval, receipts, and Turn-2 prior-history proof.

## P2-T011 — Run real Turn-1 field proof

PASS criteria:
- bound Case loaded;
- writing domain loads on demand;
- real customer material used;
- usable artifact/draft exists;
- no forbidden price;
- no WordPress publish;
- receipt/trajectory recorded.

## P2-T012 — Run real Turn-2 continuity proof

Send only literal correction.

PASS criteria:
- same Case;
- same conversation;
- fresh run;
- prior Turn-1 history visible;
- no-price survives without host reminder;
- prior background/material context reused;
- revised artifact/draft produced;
- unrelated domain remains dormant.

## P2-T013 — Run approval proof

Exercise approve and deny on customer-visible send.

Verify same Case/conversation identity and existing shared continuation seam.

## P2-T014 — Full business regression

Run:

```bash
uv run pytest -q
uv run ruff check .
```

Also run relevant Case, Client Service, ACE Writing, Budget, WordPress, Gateway, CLI resume, Memory/context activation proofs.

## P2-T015 — Documentation truth pass

Update README, `.env.example`, `profiles/stillevo-fde.toml`, and relevant Gateway docs.

Document:
- capability lifecycle;
- host ceiling ∩ profile authorization;
- Case binding operation;
- progressive business loading;
- real FDE proof command.

Remove obsolete claims that Memory/SubAgents are absent from platform.

## P2-T016 — Retire duplicate proof authority and STOP

Mark `examples/fde_loop.py` historical/diagnostic or simplify it to production seam if trivial.

Do not delete useful field evidence.

Final report must show:

```text
P2-1 PASS
P2-2 PASS
P2-3 PASS
P2-4 PASS
P2-5 PASS
P2-6 PASS
P2-7 PASS
P2-8 PASS

PHASE 2 = 100%
STOP
```
