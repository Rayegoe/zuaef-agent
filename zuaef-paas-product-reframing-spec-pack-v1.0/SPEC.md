# SPEC — ZUAEF Product Reframing & Field Validation v1.0

Status: normative for product direction.
Nature: **this pack is a product-authority migration document, not an
implementation authorization.** Phase 1 requires zero production code change.
Date: 2026-08-21.

Authority relationship:

```text
Kernel / plugin ABI authority   zuaef-architecture-subtraction-evidence-reset-spec-pack-v1.2/SPEC.md
Runtime loop authority          docs/runtime-refoundation/SPEC.md
Capability admission            docs/runtime-refoundation/CAPABILITY_ADMISSION.md
Kernel freeze record            docs/t015-kernel-freeze.md
Product surface specs (to be
migrated later, unchanged now)  "ZUAEF FDE Agent Platform — SPEC v0.3.md",
                                "ZUAEF Interactive Business Gateway — SPEC v0.3.md"
This pack                       product subject, Deployment concept, field-validation gate
```

## 1. Normative language

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative.

## 2. Product subject migration (D1)

The product subject changes:

```text
from: one FDE agent serving one bound Customer Case
      (stillevo-fde as "the product seam")

to:   outcome-defined deployments composed from business plugins
```

`stillevo-fde` is reclassified as a **reference deployment** — one instance,
not the product. The product direction sentence (a direction, not current
README copy):

> Turn natural-language business outcomes into plugin-composed deployments
> that produce accepted domain deliverables.

The second half of the existing goal ("own the user outcome with the
smallest reliable agent loop") is unchanged and remains binding.

Note on vocabulary: "deployment" already exists in this repository as
authorization prose ("per-deployment", "deployment profile" —
`src/zuaef_agent/config.py`, `src/zuaef_agent/profiles.py`, README). This
pack names the Deployment as a first-class **product document**; it does not
rename or change that existing code vocabulary.

## 3. Three-way separation: Deployment ≠ Composition ≠ Binding (D2)

```text
Natural-language intent
        │
        ▼
Deployment definition (deployment.md)
        │
        ├── outcome / deliverables / boundaries
        ├── proposes composition
        └── may declare binding needs
                 │
        ┌────────┴────────┐
        ▼                 ▼
Composition           Binding
profile → snapshot    gateway/session
"what it can do"      "which object the run acts on"
```

Definitions:

- **Composition** — the authorized capability set. `profiles/*.toml` resolved
  by `resolve_profile()` (`src/zuaef_agent/composition.py`) into a frozen
  `CompositionSnapshot` (`src/zuaef_agent/plugin_api.py`). Machine
  configuration; no model request happens here.
- **Binding** — runtime identity: which business object the current run acts
  on. Established by the Gateway/host as opaque `bindings` on `CoreDeps`
  (`src/zuaef_agent/models.py`, `gateway/bridge.py`), e.g. `{"case": ...}`.
- **Deployment** — business intent: outcome, deliverable expectations,
  operating boundaries. A human-readable document, not a runtime object.

Normative constraints:

- A Deployment definition MUST NOT own composition authority. It proposes a
  composition; the reviewed `profile.toml` remains the machine configuration
  and composition authority.
- A Deployment definition MUST NOT carry binding values (`case_id`, customer
  ids, conversation ids). It MAY declare binding *requirements* ("this
  deployment requires one active customer engagement bound at runtime");
  binding values remain established by the Gateway/host.
- A merged object such as `deployment.json {plugins, case_id, customer_id,
  conversation_id}` is FORBIDDEN: it fuses deployment definition, composition
  authority and runtime routing into one artifact.

## 4. Natural-language authoring is a field-experimental product hypothesis (D3)

Two status namespaces, never mixed:

```text
product authoring status    FIELD_EXPERIMENTAL — a product hypothesis under
                            field validation (ladder: FIELD_EXPERIMENTAL →
                            FIELD_VALIDATED → PRODUCT_ADMITTED)
runtime capability status   N/A — the authoring pass happens before any
                            production run and modifies no agent's model
                            cognitive environment
```

The authoring seam is not a runtime capability and MUST NOT be recorded in
the runtime capability ledger. Two consequences:

- Any model-visible capability a deployment proposes, or a derived profile
  requests, remains individually subject to
  `docs/runtime-refoundation/CAPABILITY_ADMISSION.md` on its own evidence.
  Customer natural language MUST NOT become capability admission authority.
- If the authoring pass itself ever becomes part of a production agent loop
  (model-visible), only then does it acquire a runtime capability status,
  admitted separately on its own evidence.

Phase-1 flow (no production runtime change):

```text
customer natural-language description
        ↓  (LLM authoring pass, template-conformant; vocabulary =
           admitted authoring catalog, not the installed inventory)
deployment.md draft
        ↓  (human business review, recorded edits)
approved deployment.md
        ↓  (proposed composition)
composition authorization review:  requested ∩ admitted
        ↓  (requested-but-not-admitted recorded, never silently
           enabled, never silently dropped)
reviewed profile.toml
        ↓  (existing path)
resolve_profile() → CompositionSnapshot
```

- **installed ≠ admitted.** The authoring model selects from an *admitted
  authoring catalog* — the operator-defined subset of installed plugins and
  capabilities that already carry admission evidence for this
  deployment/task class. Capabilities without admission evidence surface as
  requested-but-not-admitted and MUST NOT enter the profile.
- The authoring seam MUST NOT enter production use before the field
  evidence required by `FIELD-VALIDATION.md` in this pack; and field
  validation of the document interface admits no runtime capability
  (FIELD-VALIDATION §7).

## 5. Case remains a business-object plugin (D4)

- The Case schema MUST NOT change in this reframing. `CaseDoc` and
  `Situation` (`plugins/zuaef-case/zuaef_case/models.py`) stay as they are.
- New models named OutcomeCase / EngagementState / DeploymentState /
  BusinessProcessState MUST NOT be created for this product direction.
- Case is one instance of a business binding/domain capability. Future
  binding types (CRM opportunity, project, supplier, campaign, account) are
  peer plugins, not Case subclasses.
- The kernel continues to see opaque `bindings` only.
- A deployment.md MAY reference the case plugin in its proposed composition;
  a Deployment MUST NOT become the Case object or vice versa.

## 6. Context projection is mechanical: bounded ≠ selected (D5)

Invariant (an architecture review gate for any future projection change):

A context provider (the Case brief today, a Deployment projection if one is
ever built) MAY `read → bound → render`: read files, truncate to fixed
character bounds, render fixed sections in fixed order.

It MUST NOT `interpret → rank → select business meaning`. Forbidden host
operations include: relevance-filtering deliverables or boundaries;
keyword-based filtering of any section; hiding or reordering sections by
request context; ranking business rules and injecting only a subset.

This is a deliberately stricter product-local rule, not a claim that T006
proved all host preselection universally forbidden: the T006 diagnosis
recorded host semantic preselection as measured risk in supplementary
writing context
(`docs/runtime-refoundation/experiments/T006-wcase2-observation-proof.md`).
A small, customer-authored, high-value business contract has nothing to
search and no relevance decision to delegate to the host — so for
deployment context the stricter rule costs nothing and closes the risk
class entirely.

## 7. Plugin-owned deliverables (D6)

Normative convention:

```text
Plugin owns    the semantic deliverable definition (what "accepted
               deliverable" means in its domain, stated in the plugin's own
               docs/skill text — e.g. ace-writing: publish-ready article;
               budget: analysis report/workbook; wordpress: remote page in
               required state)
Core owns      operational truth only: ArtifactFact, ToolEffectFact,
               ExecutionState (src/zuaef_agent/models.py) — file exists,
               effect happened, run state
Human/domain
evaluation
owns           acceptance
```

- v1 adds **zero new universal schema**. DeliverableProtocol,
  DeliverableRegistry, DeliverableVerifier, OutcomeResult,
  UniversalDeliverable MUST NOT be added unless multiple plugins later
  demonstrate the same stable repeated mechanism (elevation rule,
  `AGENTS.md`).
- This convention continues existing subtractions rather than adding a
  layer: `receipt.summary.deliverable` was already removed
  (`docs/t000-baseline-audit-v1.2.md`), and `save_article` is classified
  `ARTIFACT_SUBMISSION`, not `EXTERNAL_ACTION` (ADR-RF-005).

## 8. Kernel policy preserved (D7)

- The v1.2 change rule stays authoritative: kernel edits are admissible only
  for PydanticAI/Harness compatibility, execution correctness, a security
  boundary, durability/resume correctness, the composition ABI, or generic
  operational run facts. **The new product direction is not a kernel-change
  reason.**
- Freeze status MUST be recorded accurately in every document that mentions
  it:

```text
kernel freeze policy    = authoritative (AGENTS.md; v1.2 pack §16)
verification gate       = BLOCKED — T015 not PASS (docs/t015-kernel-freeze.md)
```

  No document may mark the freeze as verified while the gate is blocked.
- Runtime queue/gate status is authoritative in
  `docs/runtime-refoundation/TASKS.md`. This pack MUST NOT mirror runtime
  task state except as a dated observation; where the two disagree,
  TASKS.md wins and this pack is stale.
- Dated observation (2026-08-21): T006 is recorded complete at HEAD with
  the diagnosis verdict `HOST_SEMANTIC_PRESELECTION_CAUSES_MEASURED_RISK`
  — diagnosis only, no production-code change; the T006-B1 human
  quality/evidence gates remain `UNJUDGED` (null), and an uncommitted
  TASKS.md revision restates that pending gate as the next queue action.
  Nothing in this pack pre-empts or blocks runtime queue work; the two
  streams share no runtime files.

## 9. Authority migration sequencing

```text
1. this SPEC Pack                    (product decisions)
2. step 0 + first field trials       (FIELD-VALIDATION.md)
3. recorded field evidence
4. README / AGENTS narrative migration
```

Until step 3 completes:

- README/AGENTS MAY describe natural-language deployment as a **direction /
  experimental product hypothesis**.
- They MUST NOT present it as current capability. Copy like "describe your
  business outcome and ZUAEF automatically composes your deployment" is
  forbidden marketing of an unverified capability.

## 10. Phase-1 change inventory (exhaustive)

Allowed in phase 1:

- this pack (SPEC.md, FIELD-VALIDATION.md);
- `deployments/<name>/deployment.md` instances authored from real material;
- an experimental authoring prompt/skill, benchmark-only, clearly labeled
  non-production, plus the operator-defined admitted authoring catalog it
  selects from.

Not allowed in phase 1:

- edits to `core.py`, `runtime.py`, `composition.py`, `profiles.py`,
  `CaseContextCapability`, or the Gateway;
- README/AGENTS product-narrative migration;
- any new engine, registry, state machine, or universal schema.

Even the Case-brief projection upgrade is deferred: the field experiment
must first show whether the existing projection can already carry outcome
context. "改投影语义，不改 schema" is the fallback, not the first move.

## 11. Decision register

| id | decision | status |
|----|----------|--------|
| D1 | product subject: outcome-defined deployments from business plugins; `stillevo-fde` = reference deployment | normative |
| D2 | Deployment ≠ Composition ≠ Binding; deployment.md proposes composition, declares binding needs, owns neither | normative |
| D3 | authoring = FIELD_EXPERIMENTAL product hypothesis (runtime status N/A); derived capabilities admitted separately; installed ≠ admitted | normative |
| D4 | Case stays a business-object plugin; no schema change; kernel sees opaque bindings | normative |
| D5 | context projection is mechanical; bounded ≠ selected; architecture review gate | normative |
| D6 | plugin owns deliverable semantics, core owns operational facts, human evaluation owns acceptance; zero new universal schema | normative |
| D7 | kernel freeze policy authoritative, T015 gate BLOCKED, T006-B1 gate untouched | normative |
