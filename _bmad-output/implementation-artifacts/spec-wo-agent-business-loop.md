---
title: 'Prove the minimal WO–Agent business loop'
type: 'feature'
created: '2026-08-21'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/docs/runtime-refoundation/SPEC.md'
  - '{project-root}/docs/runtime-refoundation/CAPABILITY_ADMISSION.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Gateway can deterministically bind a Case and execute a real profile, but it cannot correlate that session with a real WorkOrder or let a Supervisor explicitly accept a completed deliverable. Without that seam, a real run cannot prove that execution truth and business truth remain separate.

**Approach:** Add the smallest host-owned Work Control seam around the existing Gateway session, opaque `CoreDeps.bindings`, Runtime receipt, and real FDE proof. A terminal run records only a `run://` pointer in the external WO authority and leaves its business state unchanged; a distinct Supervisor `/accept` command is the only operation that requests the business transition.

## Boundaries & Constraints

**Always:** Use the current z-workspace WorkOrder as authority; keep Runtime authoritative for run state, history, effects, pause/resume, and receipts; keep Gateway authoritative only for surface/session/WO/Case/run correlation; preserve existing dirty changes; run a real `stillevo-fde` model turn against the real `stillevo-beauty` Case and expose a meaningful deliverable.

**Ask First:** Any external publish/send effect, any WorkOrder close, or any change outside the assigned WO scope.

**Never:** Add a WorkOrder model or state machine to Core; infer WO state from Runtime state; copy `RunReceipt`, usage, tool effects, artifacts, or message history into WO; add a second receipt/evidence/history ledger, hash, manifest, registry, HTTP API, JSON envelope, generic resolver, projection framework, or execution approval engine.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real outcome | Supervisor-bound WO + Case, real profile prompt | Real model produces deliverable; Runtime persists execution facts; WO receives `run://<id>` and remains executing | Pointer write failure is surfaced; Runtime receipt remains authoritative |
| Business accept | Bound WO, last terminal run completed and receipt binding matches | `/accept` calls external Work Control and transitions only that WO to review | Missing/mismatched/failed run or unavailable Work Control is rejected without transition |
| Runtime pause | Run pauses for execution approval | Existing PauseReceipt/StepPersistence resumes with `wo` binding preserved | `/accept` is unavailable while active or paused; `/approve` remains execution-only |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/gateway/models.py` -- persisted session correlation; admits one `work_order_id` because Gateway owns the binding.
- `src/zuaef_agent/gateway/store.py` -- existing SQLite persistence and idempotent column migration.
- `src/zuaef_agent/gateway/bridge.py` -- threads `wo` through existing opaque `CoreDeps.bindings`.
- `src/zuaef_agent/gateway/service.py` -- deterministic bind, pointer callback, and explicit acceptance command; no business state logic.
- `src/zuaef_agent/gateway/work_control.py` -- narrow Python Protocol consumed by Gateway; authority implementation remains outside Runtime.
- `src/zuaef_agent/gateway/renderer.py` -- host-grounded WO binding/status/acceptance messages.
- `tools/fde_two_turn_proof.py` -- existing real Gateway/profile/model/Case proof, composed with the current z-workspace Work Control authority.
- `tests/test_phase2_case_binding.py` and `tests/test_gateway_service.py` -- persistence, opaque binding, no-auto-transition, and explicit-accept boundary checks.

## Tasks & Acceptance

**Execution:**
- [ ] Gateway session/store/bridge -- persist the supervisor-owned WO correlation and preserve it through run and resume.
- [ ] Gateway Work Control seam/service -- record one run pointer after terminal execution without changing business state; accept only on explicit Supervisor command.
- [ ] Existing FDE proof -- bind the assigned real WO and Case, run the real model/profile, capture the real deliverable and receipt, then demonstrate pre-accept state.
- [ ] Boundary tests -- prove execution approval stays distinct and only explicit business acceptance invokes Work Control transition.

**Acceptance Criteria:**
- Given the assigned real WO is executing, when a real Gateway run completes, then its receipt contains `case` and `wo`, a meaningful deliverable exists, and the WO is still executing with only pointer refs added.
- Given that completed bound run, when the Supervisor explicitly accepts it, then Work Control moves the WO to review; no Runtime status or receipt performs that transition.
- Given a pause/resume run, when Runtime resumes it, then the frozen execution retains the same opaque WO binding without Gateway or Core interpreting WO semantics.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest -q tests/test_gateway_store.py tests/test_gateway_bridge.py tests/test_gateway_service.py tests/test_phase2_case_binding.py tests/test_gateway_architecture.py tests/test_architecture_guards.py` -- expected: boundary suite passes.
- `uv run python tools/fde_two_turn_proof.py --workspace <durable-proof-dir> --work-order WO-20260821-ZUAEF-FEATURE-PROVE-MINIMAL-WO-AGENT --work-control-root /home/barry/z-workspace` -- expected: real model run, deliverable, Runtime receipt, run pointer, WO still executing.
- Supervisor `/accept` against the persisted proof session -- expected: the same WO moves to review only after the command.
