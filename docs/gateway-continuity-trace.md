# Gateway Continuity — TRACE (支线 C / T010–T011) — Phase 1

Status update (promoted to `main` `4fe3342`): **Phase 2 is implemented on main**
(`bridge.prior_run_history` + `start_profile_run(message_history=...)`); the
phase-1 RED test below is now green there. This document remains the historical
phase-1 record: the trace, the defect proof, and the T002 API confirmation.

Original phase-1 status: **TRACE ONLY.** No runtime change was made in this phase.
This document maps the exact path `inbound message → session → run →
persistence → next inbound`, names the continuity defect with code-level
evidence, and records the Harness 0.20.0 public continuation/StepStore API
confirmation that unlocks the Phase-2 implementation.

Scope of files studied (all under `src/zuaef_agent/`):

```
gateway/service.py      dispatch, session routing, approval callbacks
gateway/runner.py       process runner (poll loop, restart recovery)
gateway/store.py        SQLite routing-state store
gateway/bridge.py       the ONLY place the Gateway touches the shared seam
continuation.py         the single pause/resume orchestration
runtime.py              shared execute_run seam + receipt settlement
core.py                 agent composition (StepPersistence capability wiring)
```

Baseline pinned: `pydantic-ai==2.30.0`, `pydantic-ai-harness[skills,code-mode]==0.20.0`
(see `docs/upstream-baseline.md`, `uv.lock`).

---

## 1. The golden contract (SPEC §15, TASKS T010/T011)

Normal follow-up must be:

```text
Gateway session
→ prior server-authoritative run
→ public persistence/history restore
→ message_history
→ fresh run_id
→ same conversation_id
→ Agent.run(...)
```

Pause/resume uses the same history semantics plus `DeferredToolResults`. No
second conversation database, no custom history-repair runtime, no private
backend parsing.

---

## 2. Traced flow — `inbound message → session → run → persistence → next inbound`

### 2.1 inbound message

`runner.py` polls the surface (`TelegramAdapter.poll_once`, `runner.py:180`),
each event → `GatewayService.handle(event)` (`runner.py:187`,
`service.py:95`).

- Allowlist check (`service.py:96-101`).
- `GatewayStore.get_or_create_session(...)` (`service.py:102-109`): same
  `(surface, tenant_id, channel_id, thread_key)` → same `SessionBinding`. A
  brand-new session mints `conversation_id = uuid4().hex` once
  (`store.py:135`); the id is persisted and reused for every later turn.

### 2.2 session routing

- callback (approve/deny button) → `_handle_callback` (`service.py:187`) →
  `bridge.resume_for_surface` → `continuation.resume_paused_run` (pause path,
  §2.4).
- slash command → `_handle_command` (`service.py:261`). `/new` mints a fresh
  `conversation_id` (`store.py:208`) and clears run pointers — a new dialogue.
- free text with a paused run → rejected (`service.py:117-119`).
- free text otherwise → `_start_run` (`service.py:128`).

### 2.3 normal run (the defect carrier)

`_start_run` (`service.py:128-149`):

```text
run_id = uuid4().hex                                   # fresh run_id        service.py:129
save_session(active_run_id=run_id)                     # routing state       service.py:130-131
bridge.start_profile_run(
    prompt=project_prompt(envelope),
    conversation_id=session.conversation_id,           # SAME conversation   service.py:137
    run_id=run_id,                                     # fresh run
)                                                      #                    service.py:133-140
```

`bridge.start_profile_run` (`bridge.py:65-100`) composes the agent
(`build_profile_agent`) and calls the shared seam:

```text
execute_run(agent, deps,
    prompt=prompt,
    run_id=run_id,
    conversation_id=conversation_id,                    # bridge.py:92-100
    composition=snapshot)
#  ⚠ NO message_history argument
```

`execute_run` (`runtime.py:487`) then invokes the agent with
`message_history=None`:

```text
agent.run(prompt, deps=deps,
    message_history=list(message_history) if message_history is not None else None,
    conversation_id=conversation_id, ...)               # runtime.py:562-574
```

**Result:** Turn 2's `Agent.run` starts with an empty `message_history`.
`conversation_id` is reused, `run_id` is fresh, but Turn 1 is **not**
model-visible in Turn 2. `_start_run` never even reads
`session.last_terminal_run_id` — the routing state the session already tracks
(`store.py:39`) is unused for continuity.

Terminal settlement: `_settle_terminal` (`service.py:151-160`) stores
`last_terminal_run_id` and renders the receipt. The `RunReceipt` records
`continued_from_run_id = None` for this normal turn (`runtime.py:335-337`),
so receipts do not chain normal turns.

### 2.4 persistence (what SHOULD feed the next inbound)

`core.py:102-112` adds Harness `StepPersistence` to every agent when
`enable_step_persistence` (default `True`):

```text
StepPersistence(store=FileStepStore(settings.step_store_dir,
                                    max_snapshots_per_run=...),
                agent_name="zuaef", run_id=run_id)
```

The capability hooks the run: each terminal `Agent.run` appends `StepEvent`s
and saves a **`complete` snapshot of the full message history** at `after_run`
(verified empirically in §4). So Turn 1 IS durably preserved already.

The **only** place restored history is consumed today is the pause path.

`continuation.resume_paused_run` (`continuation.py:41-136`):

```text
receipt = ReceiptStore.read(paused_run_id)              # state == paused
history = continue_run(FileStepStore(step_store_dir),
                       run_id=paused_run_id,
                       include_interrupted=True)        # continuation.py:80-88
execute_run(agent, deps, message_history=history, ...)  # continuation.py:126-135
```

That is the T011 path — it restores history via the public API and works.
A normal follow-up (T010) is the same shape minus the restore step.

### 2.5 next inbound

The next free-text message hits `handle` again → same session → same
`conversation_id` → `_start_run` → empty `message_history` (loop back to §2.3).

---

## 3. Confirmed defect (with the failing test)

**Defect:** `conversation_id` is reused across normal turns **but** Turn 1's
`message_history` is not restored into Turn 2's `Agent.run`.

- What works today: `conversation_id` correlation (`service.py:137`), fresh
  `run_id` per turn (`service.py:129`), persistence of every terminal run
  (`core.py:102-112`), and pause/resume history restore (`continuation.py:87`).
- What is missing: the normal-follow-up restore step between `last_terminal_run_id`
  and `execute_run(message_history=...)`.

Proof (test-first, intentionally **RED** on this branch):

`tests/test_gateway_continuity.py::test_normal_followup_reuses_conversation_but_keeps_empty_history`

```text
Turn 1 "…blue umbrella"  →  completed
Turn 2 "Now rewrite the opening with a warmer tone"
  ✓ conversation_id == Turn 1's        (reused — passes)
  ✓ run_id != Turn 1's                 (fresh — passes)
  ✗ "blue umbrella" NOT in Turn 2's model context   (FAILS — the defect)
  actual Turn-2 context: "Now rewrite the opening with a warmer tone"
```

Run it:

```bash
uv run pytest tests/test_gateway_continuity.py -v
# 1 failed (the RED defect test), 1 passed (the green diagnostic)
```

---

## 4. T002 confirmation — public continuation/StepStore API in Harness 0.20.0

Confirmed by reading the installed harness (`pydantic_ai_harness.step_persistence`,
v0.20.0 README + source) and by an empirical probe in this branch:

Public, released API (no `main`-only imports):

| API | Purpose | Confirmed |
|---|---|---|
| `FileStepStore(directory, *, max_snapshots_per_run=None)` | durable step store | YES |
| `StepStore.list_runs(*, conversation_id=...) → list[RunRecord]` | find a dialogue's runs, chronological (`[-1]` = latest) | YES |
| `StepStore.latest_snapshot(*, run_id, include_interrupted=False) → ContinuableSnapshot` | newest `complete` snapshot | YES |
| `continue_run(store, *, run_id, include_interrupted=False) → list[ModelMessage]` | rebuild `message_history` from a snapshot | YES |
| `StepPersistence(store=…, agent_name=…, run_id=…)` capability | writes events + snapshots during `Agent.run` | YES |

Empirical proof (green diagnostic
`test_terminal_run_leaves_resumable_snapshot`, currently passing): a terminal
Turn-1 run via the real Gateway leaves `run.json` under the conversation, a
`complete` snapshot whose messages contain Turn 1's prompt, and
`continue_run(store, run_id=Turn1)` returns that history.

```bash
uv run pytest tests/test_gateway_continuity.py -k terminal_run_leaves_resumable_snapshot -v
# passes: snapshot.state == "complete", continue_run rebuilds "…blue umbrella"
```

Note (for step-bounded history): with the default `max_snapshots_per_run=8`,
older per-step snapshots are pruned inside one long run; the retained `complete`
snapshot keeps the default read path correct. Whole-run `conversation_id`
grouping is unaffected.

---

## 5. Phase 2 — implementation sketch (DEFERRED, not implemented here)

The fix is small and stays inside the existing seams — no new framework, no
second persistence, no custom history-repair runtime (SPEC §19 forbids those):

1. In the normal-run path (`service.py:_start_run` / `bridge.start_profile_run`),
   before `execute_run`, resolve the prior run:
   `prior = session.last_terminal_run_id` (the server-authoritative previous run).
2. Restore history through the public API:
   `history = continue_run(FileStepStore(settings.step_store_dir), run_id=prior)`
   (guard `LookupError`, e.g. missing snapshot → start cold with a documented
   decision; do not crash the turn).
3. Pass `message_history=history` (and keep the same `conversation_id` + a
   fresh `run_id`) through `execute_run`.
4. Optionally set `RunReceipt.continued_from_run_id = prior` for normal turns
   so receipts chain the same way the pause path already chains.
5. T011 (approval) must keep working unchanged — it already restores history;
   add a regression that a paused-then-approved turn still carries Turn 1.

Phase 2 is gated on the T002 ledger recording the §4 confirmation; when it
lands, the RED test above is expected to turn GREEN.

---

## 6. Evidence summary

| Item | Status |
|---|---|
| Trace of the full turn loop | this document, §2 |
| Defect precisely located | §3 (`service.py:133-140` → `bridge.py:92-100` → `runtime.py:565`) |
| Public API confirmed (T002) | §4 |
| RED defect test | `tests/test_gateway_continuity.py::test_normal_followup_reuses_conversation_but_keeps_empty_history` |
| GREEN persistence diagnostic | `tests/test_gateway_continuity.py::test_terminal_run_leaves_resumable_snapshot` |
| Runtime change | NONE (phase-1 TRACE ONLY) |
