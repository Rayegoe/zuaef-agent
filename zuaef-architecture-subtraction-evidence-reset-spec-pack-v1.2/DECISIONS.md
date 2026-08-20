# DECISIONS — Architecture Decisions

## ADR-01 — “Verification” is split into integrity, evidence, and judgment

**Decision:** generic runtime owns integrity only.

Reason:
- bytes/events can be mechanically checked;
- semantic support needs source reading;
- quality needs evaluation/judgment.

Consequence:
- delete semantic `verification` naming from kernel.

## ADR-02 — Evidence lives with the result

**Decision:** factual deliverables expose source URLs/citations directly.

Reason:
- evidence should be inspectable by the reader;
- hidden receipt fields do not help the user assess support.

## ADR-03 — URLs are necessary but not sufficient

**Decision:** source presence alone is not called validation.

Review must be able to inspect whether the source actually supports the claim.

## ADR-04 — Human feedback is an artifact, not a label

**Decision:** preserve human prose/edits as authority.

Derived labels are disposable.

## ADR-05 — No global editorial ontology in runtime

Do not force every writing improvement into:
- sensor;
- action;
- weight;
- score.

Experiments may derive such features locally.

## ADR-06 — Case is plugin semantics

Kernel stores opaque bindings only.

No Binding Framework.

## ADR-07 — PydanticAI/Harness remains the generic behavior substrate

Continue deleting local reimplementations when upstream provides the primitive.

## ADR-08 — Plugin ABI stays small

No Cordis-style service/event runtime is added.

## ADR-09 — Generalist flags are closed compatibility surface

Do not grow a second capability registry around Harness.

## ADR-10 — Quality loop is offline/operator-driven

No mandatory critic/gate on every production run.

## ADR-11 — Real proof cannot be replaced by schema proof

Examples:

```text
“receipt has verified_artifacts”          ≠ artifact is good
“source field is non-empty”              ≠ claim is supported
“approved_by=human-editor”               ≠ human approved this exact promotion
“sensor score improved”                  ≠ humans prefer the result
“tool call completed”                    ≠ business outcome succeeded
```

## ADR-12 — Promotion is versionable and reversible

Promote:
- Skill;
- example;
- plugin change;
- memory/case fact.

Avoid opaque global accumulated evidence scores.

## Forbidden abstractions without a new measured failure

```text
EvidencePlane
QualityPlane runtime
ContextPlane
BindingRegistry
PluginServiceRegistry
EventBus
custom AgentGraph
custom durable runtime
custom long-term memory database
automatic production self-modification
```

## ADR-13 — Result structure belongs to Capability

**Decision:** a Capability/domain plugin defines the useful deliverable shape using its instructions and domain tools.

Kernel keeps natural output and operational receipts.

Rejected alternatives:
- universal `BusinessResult` Pydantic model;
- `result_schema` on `PluginBundle`;
- result registry;
- adding every domain's fields to `RunSummary`.

Reason:
A business capability knows the semantic form of its outcome; the Kernel does not.

## ADR-14 — Domain-local structure may be strict without becoming global

A WordPress tool may require `title/content/status`.
A budget plugin may validate numeric tables.
A research capability may require inspectable URLs in its own report instructions.

These are legitimate local schemas/invariants.

They become over-abstraction only when lifted into a generic ZUAEF result contract without repeated cross-domain evidence.


## ADR-15 — Pydantic models objects, not Agent workflow

**Decision:** Pydantic may validate the shape and deterministic constraints of data crossing a boundary. It must not be used as a generic workflow engine.

Allowed:
- tool arguments;
- API payloads;
- plugin config;
- domain records;
- deterministic calculation inputs/outputs.

Rejected:
- `research_complete`;
- `evidence_passed`;
- `draft_ready`;
- `quality_score`;
- `next_stage`;
- generic phase/status fields used to decide what the Agent is allowed to do next.

Native human approval remains valid for real external/destructive effects because that is an authorization boundary, not a Pydantic workflow gate.
