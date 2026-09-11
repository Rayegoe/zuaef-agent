# ZUAEF Architecture North Star

| Field | Value |
|---|---|
| Status | Working North Star; normative for future architecture decisions |
| Date | 2026-09-11 |
| Audited baseline | `Rayegoe/zuaef-agent` `main@cf581e5` |
| Scope | system shape, ownership, capability admission, surface/control/domain boundaries |

> Model owns intelligence. Harness owns execution. ZUAEF only connects a concrete task to the real
> materials the model must see and the real actions the environment can actually perform, through
> the thinnest reliable interface.

This document is the architectural admission test for ZUAEF. It does not describe everything the
repository currently contains; it describes what future changes must move toward, what they may not
re-create, and which existing authority is allowed to remain.

---

## 1. Why this document exists

The current problem is not simply "too much code". The problem is that internal mechanisms, product
capabilities and operator entrances have grown out of proportion to each other:

```text
internal machinery        product capability        operator entry points
        many                       real                    many
           \                      /                          /
            \                    /                          /
             ---> authority is spread across all three <---
```

The result is not incomprehension of any single file. It is that no agent or engineer can reliably
answer:

- who owns a behavior after this change;
- which mechanism is still allowed to exist;
- which surface is allowed to interpret runtime state;
- whether a product capability belongs to the core, a plugin, a deployment tool or an external app.

The North Star exists to answer those questions with one rule set. It is deliberately narrower than
a general architecture manifesto.

---

## 2. What ZUAEF does not do

ZUAEF does not try to re-create intelligence that the model already has.

ZUAEF does not build a complex ontology, domain world model, or Claim/Decision/Workflow object system
and then force the model to understand reality through that artificial abstraction.

ZUAEF does not re-create capabilities already provided by PydanticAI Harness, DeepSeek Harness, or
equivalent upstream execution substrates:

```text
Tool Calling
Shell
Filesystem
Skills
Planning
Subagents
Session
Context Management
Durable Execution
```

Those are consumed where admission evidence requires them. They are not ZUAEF's competition.

---

## 3. What ZUAEF is responsible for

The core question is not:

> How do we make the Agent smarter?

It is:

> At this task, what reality does the model actually need to see?

and:

> Once the model decides, what can actually be executed in this reality?

ZUAEF therefore owns **Minimal Reality Binding**:

> Use the thinnest system necessary to connect the correct reality materials and the correct real
> actions to the model at the correct time.

Minimal Reality Binding requires:

```text
Do not model the whole domain in advance.

Do not encode reasoning the model already owns back into host rules.

Do not add a mechanism because it may be useful later.

Do not spend model requests on mechanical actions.

Do not mix operator scripts, business capability and runtime machinery into one layer.

Add structure only for a failure that has actually occurred.
```

### 3.1 Responsibility split

```text
Semantic work        -> MODEL
Mechanical work      -> HOST (deterministic)
Reality connection   -> ZUAEF
```

### 3.2 The connection diagram

```text
                              USER
                                |
                                v
                               TASK
                                |
                  +-------------+-------------+
                  |                           |
       Deterministic Control             Semantic Work
                  |                           |
                  v                           v
        HOST CONTROL PLANE             Relevant Reality
                                              |
                                              v
                                            MODEL
                                              |
                                              v
                                    Real Action Surface
                                              |
                                              v
                                            RESULT
```

Control here is deterministic host control. It is not a router agent, a planner, or a second model.

---

## 4. Six architecture principles

### A. Semantic work belongs to the model

Understanding, judgment, trade-offs, interpretation, prioritization and creation belong to the model.
Do not quietly move those decisions into a host heuristic, keyword ranker, hard-coded taxonomy, or
surface-specific fallback.

### B. Mechanical work belongs to the host

Saving, binding, querying state, approval settlement, export, format conversion, status checks and
deterministic transport do not start a model request.

### C. Reality stays close to its native form

A web page stays a web page. A user's words stay the user's words. Market data stays market data. A
file stays a file. Add a persistent field or structure only after a real business failure proves it
is required.

### D. Every mechanism carries a burden of proof

Every new model turn, tool, capability, persistent field, schema, state, gate, fallback, router,
cache, command family, or service boundary must answer:

> Which reproduced failure or external contract requires it?

If that answer does not exist, the mechanism must not enter production architecture. Deterministic
code is not exempt: deterministic work can still be unnecessary, and it can still steal semantic
authority.

### E. The shortest correct trajectory wins

If two paths produce the same or better business result, prefer the one with fewer model decisions,
less context, fewer tools and fewer mechanisms. Do not add a model turn to perform bookkeeping.

### F. Commands and natural language have different responsibilities

```text
Command         = deterministic host control
Natural language = semantic work
```

This is the intended order of the ZUAEF operator interface.

---

## 5. Target system layers

The target conceptual structure has five layers.

```text
+----------------------------------------------------------+
|                         SURFACES                         |
|        CLI / Telegram / Feishu / Web Console / API       |
+------------------------------+---------------------------+
                               |
                               v
+----------------------------------------------------------+
|                    HOST CONTROL PLANE                    |
|  session / run / context binding / approval / artifacts  |
|                    health / configuration                |
|                   (always deterministic)                 |
+------------------------------+---------------------------+
                               |
                    semantic task only
                               |
+------------------------------+---------------------------+
|                    PROFILE COMPOSITION                   |
|          context + capability binding for a task class   |
+------------------------------+---------------------------+
                               |
+------------------------------+---------------------------+
|                     ONE AGENT RUNTIME                    |
|        PydanticAI agent loop; upstream Harness primitives |
+------------------------------+---------------------------+
                               |
+------------------------------+---------------------------+
|                      DOMAIN ADAPTERS                     |
|              Toolset / Skill / Capability                |
+------------------------------+---------------------------+
                               |
                           REAL WORLD
```

The four composition categories in `AGENTS.md` (Toolset, Capability, Core, Skill) describe how
behavior is packaged inside the Domain Adapters / Runtime layers. They are a different axis from this
five-layer system map; both are binding.

The Host Control Plane must not become:

- an LLM router;
- a workflow engine;
- a domain model;
- a universal state layer;
- a second agent runtime;
- a command framework that invents syntax for every future noun.

It is only deterministic operator control over existing runtime facts.

---

## 6. Current-state audit (`main@cf581e5`)

This audit is an inventory of current authority, not a target to preserve. It was verified against the
Git tree at the stated baseline.

### 6.1 Inventory

| Metric | Current baseline |
|---|---:|
| tracked files | 1232 |
| Python files | 328 |
| `src/zuaef_agent` Python files | 39 |
| plugin Python files | 80 |
| test Python files | 103 |
| plugins | 12 |
| profiles | 13 |
| `tools/` scripts | 33 (32 `.py` + 1 shell) |
| Gateway Python | 12 files / 148,976 B (~149 KB) |
| Web Console Python | 11 files / 124,074 B (~124 KB) |
| `src/zuaef_agent` Python | ~403 KB |
| `tools/` Python | ~694 KB |
| plugin Python | ~539 KB |
| `plugins/zuaef-quant/` all files | 10 files / ~89 KB |
| `tools/quant_*` product operations | 18 files / ~506 KB |

> P6 update: this table is the pre-refoundation baseline (`main@cf581e5`).  Quant production
> ownership has since moved into `plugins/zuaef-quant/zuaef_quant`; root `tools/quant_*` is now
> developer/audit/benchmark tooling only.  See `docs/domain-surface/P6_SHADOW_LAYER_RETIREMENT_REPORT.md`.

The top-level runtime / composition / store / kernel code is much smaller than the sum of the product
surfaces. Gateway + Web Console are approximately 68% of `src/zuaef_agent` Python bytes. A large
"Runtime rewrite" would therefore not address the main authority problem.

### 6.2 Structural finding 1 — Shadow Product Layer (retired)

The pre-P5 finding was that the Quant product body lived in root `tools/` while the
plugin only carried semantic tools and side-environment adapters. P5.8, P5.9 and P6
resolved that ownership defect:

```text
Agent Tool / Operator / systemd
    -> zuaef_quant.*
    -> Reality
```

The former root production implementations now live in `plugins/zuaef-quant/zuaef_quant`
(engines, sidecars and operator app).  All zero-caller compatibility wrappers were
deleted in P6; root `tools/` retains only audit/benchmark/diagnostic/developer tooling.
Evidence: `docs/domain-surface/P5_9_PRODUCTION_AUTHORITY_REPORT.md` and
`docs/domain-surface/P6_SHADOW_LAYER_RETIREMENT_REPORT.md`.

### 6.3 Structural finding 2 — Gateway is a God Object

`src/zuaef_agent/gateway/service.py` is ~48 KB and currently carries concerns including:

```text
authorization
session
profile routing
run dispatch
progress watchdog
continuation / resume
approval
case binding and enumeration
commands
artifact delivery
terminal rendering
domain fallback
```

Gateway has also started to know a Quant filesystem convention directly:

```text
artifacts/quant/briefs/last-reply.json
```

That is a layer leak:

```text
Generic Gateway
      |
      v
knows Quant filesystem convention
```

The correct boundary is not "add another special case"; it is to stop the leak and move generic
control facts to the shared Host Control Plane and domain-specific behavior to the domain owner.

### 6.4 Structural finding 3 — Web Console has become a second Operator Plane

The Web Console owns:

```text
readers
projector
inspection
analysis
analysis_projector
analysis_store
actions
SSE
API
```

Gateway owns overlapping operational semantics:

```text
status
inspect
approval
artifact delivery
progress
run state
```

Both surfaces interpret the same run/receipt/step facts independently:

```text
                    Runtime Truth
                    /          \
                   /            \
            Gateway View      Web View
            Gateway Action    Web Action
            Gateway Inspect   Web Inspect
```

The Web Console is not itself wrong. The missing piece is a shared deterministic Host Control layer,
so each surface becomes an adapter instead of another controller.

### 6.5 Structural finding 4 — the Host Control Plane is missing

ZUAEF has:

```text
Agent Runtime
Plugin Composition
Domain Toolsets
Gateway
Web UI
```

It lacks the layer between them that owns:

```text
run inspection
session reset
profile binding
case binding
approval
artifact listing / export
explicit persistence
health
configuration inspection
```

Consequently CLI, Gateway and Web each grow their own version of deterministic control. The target is:

```text
CLI      ---\
Telegram ---+--> Host Control Plane (deterministic) --> Runtime facts / stores
Feishu   ---+                 |
Web      ---/             no model calls
```

### 6.6 Structural finding 5 — commands are flat and weak

The CLI currently exposes top-level entries such as:

```text
run
resume
plugin
profile
gateway
web
```

The Gateway fixed command set includes:

```text
/help /new /case /cases /unbind /profile
/status /inspect /approve /deny /artifacts
```

The count is not the primary problem. The problem is that there is no conceptual grammar. These
commands really belong to two families:

```text
RUN / SESSION:   /new /status /inspect /artifacts
CONTEXT:         /profile /case /cases /unbind
```

Operators are forced to remember isolated verbs rather than a small model of the system.

### 6.7 Structural finding 6 — profiles no longer carry production order

`profiles/` contains production profiles (`quant-decision`, `coding`, `general-knowledge-worker`,
`stillevo-fde`, `stillevo-ebike-intel`, `wordpress-operator`) alongside experiment variants such as
`ace-writing-t006-b1-technique-off` and `ace-writing-t006-b2-model-owned-techniques`.

As a result, `profile list` shows both:

- modes a user may actually deploy;
- historical A/B variants from a benchmark.

Profile becomes a directory of TOML files rather than a product concept. Production and experimental
profiles must not share one namespace.

### 6.8 Structural finding 7 — Core packaging is not actually thin

Root `pyproject.toml` declares every production plugin as a direct dependency. Architecturally
`installed != enabled`, but at packaging level:

```text
install core
    ~=
install everything
```

This weakens the real Thin Core boundary even when runtime cost looks acceptable. Code ownership,
package dependency and production authority need to be separated; a Git repository split is not
required for that.

### 6.9 Structural finding 8 — the repository is both product and archaeology site

Root contains current production authority alongside historical design evidence:

```text
SPEC files
implementation reports
old platform specs
gateway specs
refactor notes
validation reports
spec packs
_bmad
_bmad-output
benchmarks
experiments
learning
```

History has value. The defect is that history and current authority occupy the same visible level. A
new coding agent cannot quickly answer:

```text
Which file is the current rule?
Which is history?
Which is an experiment?
Which is proof only?
Which path is production?
```

That uncertainty is a direct context cost for Codex / Pi / other development tools. The root should
make the current system visible; history should leave the authority path.

### 6.10 Re-foundation already identified the same problem

`docs/runtime-refoundation/TASKS.md` already contains:

```text
T009 — Capability ledger
T012 — Delete zombie architecture
```

This is evidence that the repository has already recognized the need to classify capability authority
and retire old architecture. The North Star is the admission standard for those tasks, not a reason
to start a separate architecture program.

---

## 7. Most dangerous trend

The dangerous trend is not code volume by itself:

```text
real incident
    -> add mechanism
    -> add test
    -> add document
    -> add special path
    -> add surface handling
```

Every individual repair may be reasonable. The cumulative result is:

```text
the system becomes more reliable
and harder to understand
```

That is the current state.

Therefore every incident fix must answer two questions, not one:

1. How does this fix the reproduced case?
2. Which previous authority becomes unnecessary, duplicated, or deletable because of this fix?

---

## 8. Required consolidation order

The next phase is **Architecture Consolidation**, not Runtime v2 and not a new framework.

Detailed work definitions live in [`CONSOLIDATION_SPEC.md`](./CONSOLIDATION_SPEC.md). The North Star
sequence is:

| Priority | Work | Purpose |
|---|---|---|
| P0 | Freeze this North Star in agent-visible locations | Stop horizontal mechanism growth |
| P0 | Complete the Capability Ledger (`T009`) | State why every mechanism exists |
| P1 | Build the shared Host Control Plane (`C1`) | CLI/Gateway/Web stop owning separate control semantics |
| P1 | Define command grammar (`C2`) | Replace isolated verbs with a small noun/verb model |
| P1 | Shrink `GatewayService` (`C3`) | Remove the God Object and domain fallback |
| P1 | Move Quant operational authority out of root `tools/` (`C4`) | Eliminate the Shadow Product Layer |
| P1 | Separate production and experimental profiles | Restore profile product semantics |
| P2 | Demote Web Console packaging to app/surface | Reduce Core authority |
| P2 | Move root historical spec/proof material out of the authority path | Reduce repository context cost |
| P2 | Converge package dependencies | Make Thin Core true at install time |
| P3 | Complete Zombie Architecture deletion (`T012`) | Leave exactly one production authority per behavior |

Only the first four named workstreams (`C1`–`C4` plus the capability-ledger prerequisite) are in the
current consolidation scope. The remaining rows are explicitly deferred.

---

## 9. Change admission test

Every ZUAEF PR must be answerable in one sentence:

> This change improves the task-to-reality connection because **[reproduced failure / external
> contract]**, and it removes or demotes **[previous authority]**.

If it does not improve that connection, and instead does one of the following:

```text
re-encodes model intelligence
copies Harness capability
pre-builds structure for future possibility
adds another intermediate layer
adds a model turn for mechanical work
adds a surface-specific interpretation of runtime truth
```

then the default decision is **do not merge**.

A useful review checklist:

1. What reproduced failure or external contract requires this?
2. Did semantic judgment move into the host?
3. Is this already owned upstream by PydanticAI / Harness?
4. Which new turn/tool/field/state/gate/router/cache is introduced, and why?
5. Who owns the behavior after this change?
6. Which old path loses authority?
7. Is this the shortest correct trajectory?
8. Is a command doing only deterministic control?
9. Did this create or feed a Shadow Product Layer?
10. Can the same business result be achieved by deleting something instead?

---

## 10. Explicitly not next

Do not start:

```text
ZUAEF Runtime v2
Global Router
Domain Model
Workflow DSL
Command Framework
Universal State Layer
```

Also do not treat this document as authorization for a big-bang refactor. Consolidation means:

```text
add less.

rename existing layers.

take deterministic control out of the Agent path.

return scattered product capability to its real owner.

remove experiments from the production namespace.

separate surfaces from business logic.

delete authority that no longer has a job.
```

---

## 11. Document relationships

| Document | Relationship |
|---|---|
| `AGENTS.md` | Always-on operating rules; routes coding agents to this North Star |
| `docs/architecture/NORTH_STAR.md` | This document; broad architecture authority |
| `docs/architecture/CONSOLIDATION_SPEC.md` | Current work order for `C1`–`C4` |
| `docs/domain-surface/SPEC.md` | Domain-layer work order: `Intent -> Semantic Affordance -> Reality` |
| `docs/runtime-refoundation/SPEC.md` | Runtime-specific subset of the North Star; binding for runtime work |
| `docs/runtime-refoundation/TASKS.md` | Runtime evidence backlog; not a license to expand system layers |
| `docs/runtime-refoundation/DELETION.md` | Deletion protocol used to retire authority |
| `AGENTS.md` Live-ops facts | Current operational truth; do not override without a deployed replacement |

If this document and current code disagree about current behavior, current code plus the live-ops
facts describe reality. This document describes the direction and admission standard. If this
document and an older architecture spec pack disagree about future direction, this document wins, and
the older pack should be demoted or linked as history.

Changes to this document are architecture changes. They require a recorded reason, a reproduced
failure or external contract, and an explicit statement of which previous rule is replaced.
