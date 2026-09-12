# ZUAEF Architecture Consolidation Spec

| Field | Value |
|---|---|
| Status | Scoped work definition — authorized sequence, not authorization for a big-bang rewrite |
| Date | 2026-09-11 |
| Baseline | `main@cf581e5` |
| North Star | [`NORTH_STAR.md`](./NORTH_STAR.md) |
| Scope | Host Control Plane, command grammar, Gateway ownership, Quant ownership |

> Consolidation means adding less while restoring ownership. This spec defines the smallest sequence
> that gives deterministic control one home and gives each product capability one owner.

---

## 1. Purpose

The current repository does not need another Runtime architecture. It needs its existing authority
returned to clear owners:

```text
deterministic operator control  -> shared Host Control Plane
commands                        -> grammar over that control plane
Gateway                         -> transport / platform adapter
Quant product runtime           -> zuaef-quant owner, not root tools/
```

This spec defines only those four workstreams plus the capability-ledger prerequisite. It deliberately
does not authorize Runtime v2, a new framework, or a global migration of unrelated code.

---

## 2. Success condition

Architecture consolidation is successful when all of the following are true:

1. There is one deterministic Host Control Plane beneath CLI, Gateway and Web Console.
2. A surface can render and collect input, but does not independently implement run inspection,
   session/context binding, approval settlement, or artifact-listing semantics.
3. The command interface has a small noun/verb grammar; existing commands remain aliases during
   migration.
4. `GatewayService` is a transport/adapter again and contains no domain filesystem convention.
5. Quant product implementation has one owner: `zuaef-quant` (plugin/package/deployment), not root
   `tools/`.
6. No behavior has two equal "official" paths after a workstream lands.
7. Runtime behavior and business outcomes do not regress.
8. No new intermediate layer, framework, state store, event bus or service boundary is introduced to
   perform this consolidation.

This is not a line-count target. Fewer lines are welcome only when ownership and reliability improve.

---

## 3. Exclusions

This spec does **not** authorize:

```text
ZUAEF Runtime v2
Global Router
Domain Model
Workflow DSL
Command Framework
Universal State Layer
new database / message broker / event bus / daemon
new model-visible tools or capabilities
domain command registration in the Core CLI
a Git repository split
moving Web Console to another repository
thinning package dependencies before ownership is clear
```

Also out of scope for this phase:

- production/experimental profile directory split (separate P1 change);
- root historical spec/proof relocation (P2);
- Core dependency thinning (P2);
- Web Console packaging demotion (P2);
- Zombie deletion beyond the authority each workstream itself removes.

These items remain on the North Star priority table. They must not be bundled into this phase.

---

## 4. Execution rules

### 4.1 One authority per behavior

Before a class/function/command/config is moved, identify:

```text
current owner
behavior contract
callers/surfaces
durable facts it reads or writes
failure it exists to prevent
target owner after the change
```

After the change, the old owner must not remain an equal alternative. A temporary compatibility
shim may exist only with a deletion condition in the same spec/PR.

### 4.2 Extract, delegate, delete

Preferred sequence for each workstream:

```text
1. extract one deterministic behavior into its real owner;
2. make the old call site delegate;
3. keep behavior tests/evidence green;
4. delete the old authority or mark it schema-only compatibility;
5. update runbooks/docs in the same change.
```

No workstream is "done" when it creates a second path that also works.

### 4.3 Narrow interface, native data

Control-plane functions accept settings, IDs, decisions and explicit arguments. They return typed
deterministic results. They must not import Telegram/Feishu/Starlette/argparse rendering code, and
they must not know domain names, file extensions or product conventions.

### 4.4 No semantic preselection

If consolidating a surface requires deciding which run/material/artifact/case is relevant, that
decision belongs to the model or an explicit operator argument. Deterministic code may transport,
filter by explicit ID, page, or apply a declared mechanical rule; it may not invent relevance.

### 4.5 Preserve executable aliases

No operator is forced to relearn everything in one release. Existing commands remain aliases while
the canonical grammar is introduced. Aliases must delegate to the canonical path, not re-implement it.

### 4.6 Testing evidence

Each workstream needs:

- a behavior trace of the old path;
- focused tests for the new owner;
- a surface-level integration test proving the old user-visible behavior still works;
- an explicit statement of what old code/tests/docs were deleted.

Do not add a new proof framework, manifest layer or verification service for this phase.

---

## 5. Prerequisite C0 — Authority and capability ledger

**Status:** required before or alongside C1; no new runtime code

This prerequisite does not move code. It completes the evidence base:

- complete `T009 — Capability ledger` in `docs/runtime-refoundation/TASKS.md`;
- classify each capability as `REQUIRED_INVARIANT`, `ADMITTED_PROFILE`, `EXPERIMENTAL`,
  `QUARANTINED`, or `DELETE_CANDIDATE`;
- record, for each existing surface/control behavior, whether its owner is Surface, Host Control,
  Profile/Runtime, or Domain;
- identify every shadow authority (including root `tools/quant_*` and Gateway's Quant artifact path).

Output:

```text
owner map
capability ledger
shadow-authority inventory
delete/demote candidate list
```

C0 is complete when every behavior named in C1–C4 has a current owner and a target owner.

---

## 6. C1 — Shared Host Control Plane

### 6.1 Current evidence

- `GatewayService` implements run/session/approval/artifact/progress control internals.
- Web Console implements its own run readers, projectors, inspection, analysis actions and SSE.
- CLI implements run/profile/plugin/gateway/web dispatch directly.
- There is no shared deterministic host layer providing one contract for these surfaces.

### 6.2 Target

Introduce one deterministic Host Control Plane in `src/zuaef_agent/` that owns generic control
operations over existing runtime facts. Candidate module/package name is an implementation detail
(for example `zuaef_agent.control`); the contract matters more than the path.

Ownership groups:

```text
Run:       list, show, inspect, resume
Session:   show, reset, current bindings
Context:   profile binding, case binding, explicit unbind
Approval:  approve, deny, pending/status query
Artifacts: list, resolve, export through explicit policy
System:    health, configuration inspection
```

### 6.3 Boundaries

The Control Plane may:

- read RunReceipts, StepPersistence step facts, composition snapshots and routing bindings;
- resolve explicit IDs;
- validate authorization/allowlist facts given by the surface;
- settle deterministic approval state through the existing `continuation.resume_paused_run` seam;
- return typed data for surface renderers.

The Control Plane may not:

- call a model;
- select business relevance;
- own approval semantics owned by PydanticAI native approval;
- duplicate Harness durable execution;
- read domain-specific artifact paths/conventions;
- own Telegram/Feishu/Web rendering;
- become a long-running service or a new state store.

### 6.4 Deliverables

- A narrow importable contract with deterministic tests.
- The first consumers: CLI run/session/artifact inspection paths, the Web Console's generic
  inspection/action paths, and one Gateway command path.
- A deprecation note for each surface function replaced.

### 6.5 Acceptance

- no model requests occur in control-plane tests;
- one artifact-listing/read-inspection authority exists;
- surface-specific command formatting remains outside the Control Plane;
- `GatewayService` and Web code delegate at least the selected generic operations to C1;
- no new process, database, bus or state file is introduced.

### 6.6 Not in C1

- moving all Gateway concerns at once (that is C3);
- moving domain-specific artifact delivery;
- redesigning run facts or receipts;
- adding an HTTP/RPC boundary around the Control Plane.

---

## 7. C2 — Command grammar

### 7.1 Current evidence

Commands are a flat list of verbs. There is no noun-level model that helps an operator understand
where a command belongs.

### 7.2 Target CLI grammar

Conceptual tree; the installed binary may remain `zuaef-agent` during migration:

```text
zuaef run
    start
    list
    show
    inspect
    resume
    artifacts

zuaef session
    show
    reset
    profile
    case

zuaef profile
    list
    show
    check

zuaef plugin
    list
    inspect

zuaef knowledge
    list
    search
    read
    record

zuaef system
    health
    doctor
    config

zuaef serve
    gateway
    web
```

Old forms remain aliases, for example:

```text
zuaef-agent resume      ==  zuaef-agent run resume
zuaef-agent gateway ... ==  zuaef-agent serve gateway ...
```

### 7.3 Target chat grammar

Chat should expose the small canonical set, not a copy of the CLI tree:

```text
/help

/session
/session new

/context
/context profile ...
/context case ...

/run
/run inspect
/run artifacts

/approve
/deny
```

Existing commands remain shortcuts:

```text
/status   -> /run show
/inspect  -> /run inspect
/artifacts-> /run artifacts
/new      -> /session new
/profile  -> /context profile
/case     -> /context case
/cases    -> /context case list
/unbind   -> /context case unbind
```

### 7.4 Domain commands

Do not register domain command trees in the Core CLI:

```text
NOT: zuaef quant scan
NOT: zuaef writing revise
NOT: zuaef wordpress publish
```

Deterministic domain operations belong to the domain deployment CLI:

```text
zuaef-quant scan
zuaef-quant monitor
zuaef-quant dashboard
zuaef-quant bridge
```

Semantic domain work stays natural language through the agent profile. If a domain needs a command,
that command belongs to the domain owner/distribution, not to a Core registry.

### 7.5 Implementation rule

Do not build a "Command Framework". Prefer argparse subcommands / a data-driven command map plus
explicit handlers. The grammar is product surface; it is not a new runtime.

### 7.6 Deliverables

- CLI parser tree with canonical noun/verb paths.
- Alias mapping table, with all old forms working.
- Canonical chat commands with old commands as aliases.
- Help text that explains run/session/context/system structure.

### 7.7 Acceptance

- every old command still works and delegates to the canonical handler;
- no control command starts a model run;
- no domain noun is registered in the Core CLI;
- command help presents nouns first;
- adding one new operator action does not require a new top-level verb.

---

## 8. C3 — Gateway shrink and domain-boundary repair

### 8.1 Current evidence

`src/zuaef_agent/gateway/service.py` (~48 KB) contains transport concerns plus deterministic control,
run dispatch, progress, continuation, approval, case enumeration, artifact delivery, rendering and
domain fallback. It directly names `artifacts/quant/briefs/last-reply.json`.

### 8.2 Classification rule

Every `GatewayService` responsibility must be assigned exactly one target:

| Responsibility | Target |
|---|---|
| Telegram/Feishu transport, webhook/callback mapping, allowlist | Gateway/Surface |
| generic run/session/context/approval/artifact control | C1 Host Control Plane |
| platform message rendering | Gateway renderer / Surface |
| agent dispatch and continuation invocation | existing runtime/continuation seam |
| domain artifact convention or domain fallback | Domain owner |
| host-grounded interaction projection | Gateway until a generic fact contract is extracted into C1; domain-specific meaning stays domain-owned |

### 8.3 Required repairs

1. Remove direct Gateway knowledge of Quant artifact paths. Replace with either:
   - an explicit domain-artifact contract implemented by the domain owner; or
   - a generic platform reply projection, if the behavior is truly generic.
2. Move generic status/inspection/artifact-listing/approval-settlement paths to C1.
3. Move collection/enumeration policy that belongs to the Case domain to the Case plugin owner.
4. Keep notifier/platform rendering outside the Control Plane.
5. Ensure one gateway process remains a transport adapter; do not create a second service.

### 8.4 Deliverables

- `GatewayService` responsibility map in code tests or docs.
- C1 delegation for selected generic operations.
- Domain path literal removed and behavior covered by a domain-owned test.
- Renderer/transport tests unchanged or improved.

### 8.5 Acceptance

- no domain path literal remains in generic Gateway code;
- no generic surface test needs a real domain model to inspect a run;
- existing Telegram/Feishu behavior and approval flow still pass;
- no duplicated status/inspection/artifact semantics across C1 and Gateway.

### 8.6 Rollback

Each extraction is independently revertible. Do not refactor `GatewayService` wholesale.

---

## 9. C4 — Quant ownership returns to `zuaef-quant`

The domain-level requirements and intent/authority evidence are maintained in
[`../domain-surface/SPEC.md`](../domain-surface/SPEC.md) and its
`QUANT_INTENT_MATRIX.md` / `QUANT_AUTHORITY_MAP.md`. The P3 real-model canary
has passed (`P3_FULL_PASS`), so C4's interface premise is established; the
engine migration followed the P4/P5/P6 gating in the domain-surface spec (all
executed).

Current status: P4 engine consolidation, P5 deterministic operator surface, P5.8
monitor/bridge/scan/quant-core extraction and P5.9 production-authority completion
are executed (`docs/domain-surface/P4_ENGINE_CONSOLIDATION_REPORT.md`,
`P5_OPERATOR_SURFACE_MAP.md`, `P5_OPERATOR_SURFACE_REPORT.md`,
`P5_8_PRODUCTION_AUTHORITY_REPORT.md`, `P5_9_PRODUCTION_AUTHORITY_REPORT.md`).
P6 has retired the zero-caller root compatibility wrappers: production runtime
authority is entirely in `zuaef_quant`, while root `tools/` retains only genuine
audit/benchmark/diagnostic/developer tooling. See
`docs/domain-surface/P6_SHADOW_LAYER_RETIREMENT_REPORT.md`. The P6 closure then
deleted the last root product workflow (`quant_daily.sh`) and removed the
operator layer's reverse dependencies on the model-facing layers
(`docs/domain-surface/P6_CLOSURE_REPORT.md`). P7.1/P7.2 retired the watchlist
aliases and `get_live_signals`. P7.3 migrated broad-context callers, but the
actual Telegram E2 canary used `get_trading_context` after `get_positions`;
the broad tool remains deferred and P7.4 was not started under the recorded
stop rule (`docs/domain-surface/P7_SEMANTIC_SURFACE_REPORT.md`).

### 9.1 Current evidence

```text
plugins/zuaef-quant/    zuaef_quant production owner
tools/quant_*           developer/audit/benchmark tooling only
```

`plugins/zuaef-quant/zuaef_quant/toolset.py` invokes domain modules
(`zuaef_quant.eval_sidecar`, `zuaef_quant.market_context`, `zuaef_quant.market_intel`,
`zuaef_quant.dashboard.render`); no production authority or compatibility wrapper
remains under root `tools/`.

### 9.2 Target

Quant owns its operational runtime:

```text
plugins/zuaef-quant/ (or its explicitly chosen distribution/package)
    plugin / toolset / skills
    scan / monitor / dashboard / market intel / evaluation
    candidate building / data fetch / bridge / PIT audit / validation / serve
```

Root `tools/` returns to development and repository operations only. It is not a second product
runtime.

### 9.3 Migration sequence

1. Inventory each `tools/quant_*` file: product runtime, deployment script, or proof/dev tooling.
2. Move product implementation into the Quant owner's package/module and expose it through a
   Quant-owned entry point.
3. Update `zuaef-quant` to call its own package, never a repository-relative `tools/` subprocess.
4. Create/maintain a domain deployment CLI such as `zuaef-quant run scan` / `monitor` / `dashboard`
   only for deterministic operations that truly need command invocation.
5. Update systemd units, ops runbooks, docs, tests and state paths in the same migration.
6. Delete the old root copies or leave a thin one-release compatibility shim with a recorded deletion
   condition. Do not leave both implementations equal.

### 9.4 Live-ops guardrails

Until migration is complete and deployed:

- canonical trading-ledger writes stay on the current single-writer path;
- do not create a second writer or a second ledger authority;
- do not change service units silently;
- update `docs/quant/README.md` and the relevant domain source-of-truth when the owner moves.

### 9.5 Acceptance

- `zuaef-quant` does not resolve root `tools/quant_*`;
- one owner can package, deploy, test and retire the Quant operations;
- trading-ledger single-writer behavior is preserved and documented;
- `tools/` no longer contains product authority for Quant;
- existing operational service paths continue to work after migration.

### 9.6 Not in C4

- changing trading strategy, model choice, data provider, or business semantics;
- moving Quant into Core;
- creating a generic plugin CLI framework;
- moving all root `tools/` scripts at once.

---

## 10. Sequence and PR strategy

Recommended order:

```text
C0  authority/capability ledger                  (P0, evidence only)
C1  Host Control Plane extraction                (P1)
C2  command grammar over C1                      (P1)
C3  Gateway shrink using C1                      (P1)
C4  Quant ownership migration                    (P1, may run in parallel after C0)
```

Rules:

- Do not start C2 before C1 has a stable contract for the commands it exposes.
- Do not perform C3 as a single rewrite; use independent extraction PRs.
- Do not combine profile/package/root-history cleanup with C1–C4.
- One PR should remove or demote authority; otherwise it is not consolidation.

A PR in this phase should be small enough that its North Star sentence is:

```text
This change moves [behavior] from [old owner] to [new owner]
because [reproduced ownership failure],
and deletes/demotes [old path].
```

---

## 11. Evidence and verification

Before changing behavior, capture a current trace or test.

Evidence types:

```text
surface behavior tests
one real CLI/Gateway/Web flow per moved behavior
Capability Ledger entries
domain source-of-truth / live-ops confirmation for Quant migrations
```

Do not create:

```text
new hash lineage
new receipt/proof layer
new architecture registry
new broad benchmark suite
```

Verification is per workstream. Full-suite regression remains the gate.

---

## 12. Stop and kill criteria

Stop the consolidation phase and report rather than adding machinery when:

- a target owner cannot be named;
- two equal implementations would survive the change;
- a "temporary" compatibility layer has no deletion condition;
- the change requires a new framework/service/state layer;
- semantic selection would move into deterministic code;
- current operational behavior cannot be preserved and no domain owner accepts the requirement;
- outcome or safety evidence regresses.

A zero-change conclusion is valid when the ownership defect does not reproduce or when previous work
already established the target. Do not manufacture code movement as proof of progress.
