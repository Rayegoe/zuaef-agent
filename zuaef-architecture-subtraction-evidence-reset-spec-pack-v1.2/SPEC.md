# SPEC — ZUAEF Kernel Subtraction v1.0

## 1. Normative language

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative.

## 2. Target layer model

```text
┌─────────────────────────────────────────────┐
│ Surfaces                                    │
│ CLI / Telegram / Feishu / future adapters  │
└────────────────────┬────────────────────────┘
                     │ normalized input + bindings
                     ▼
┌─────────────────────────────────────────────┐
│ Frozen ZUAEF Kernel                         │
│ - compose                                   │
│ - run                                       │
│ - pause/resume                              │
│ - operational receipt                      │
│ - security/integrity invariants             │
└────────────────────┬────────────────────────┘
                     │ PluginBundle
          ┌──────────┼───────────┐
          ▼          ▼           ▼
      Toolsets    Skills    Capabilities
          │          │           │
          └──────────┼───────────┘
                     ▼
               domain plugins

Separate offline path:

run artifact → source inspection → LLM review → human annotation
→ revision → accepted learning assets → later profile/skill/plugin use
```

## 3. Kernel definition

The kernel MAY know only generic concepts:

```text
Agent
Run
Conversation
Binding
Plugin
Profile
Composition
Tool
Capability
Skill
Approval
DeferredCall
Artifact
Usage
Error
Step
Receipt
```

The kernel MUST NOT know:

```text
Case
Customer
Article
Writing
Beauty
Budget
WordPress
Feishu
Telegram business semantics
Deal
CRM
Project business schema
Editorial action
Editorial sensor
```

Surface code may know transport concepts (e.g. Telegram message IDs), but kernel code MUST NOT import surface modules.

## 4. CoreDeps

### Current problem

Current:

```python
@dataclass(frozen=True)
class CoreDeps:
    workspace_root: Path
    run_id: str
    case_id: str | None = None
```

This makes Case a kernel concept.

### Target

```python
from collections.abc import Mapping

@dataclass(frozen=True)
class CoreDeps:
    workspace_root: Path
    run_id: str
    bindings: Mapping[str, str]
```

`bindings` is opaque to the kernel.

Examples:

```python
{"case": "stillevo-beauty"}
{"project": "wp-redesign"}
{"tenant": "stillevo", "case": "beauty-001"}
```

Rules:

- kernel MUST preserve bindings across pause/resume;
- kernel MUST NOT validate domain-specific key meanings;
- no `BindingRegistry`, `BindingProvider`, or binding class hierarchy may be added;
- plain immutable mapping is sufficient.

## 5. Receipt semantics reset

### 5.1 Receipt purpose

A receipt is an **operational run record**, not a semantic evidence bundle.

It answers:

- what ran;
- with which composition;
- when;
- with which usage;
- what execution state occurred;
- which external/tool events were recorded;
- which artifact bytes were created/changed;
- why execution failed or paused.

It does NOT answer:

- whether the answer is true;
- whether a source supports a claim;
- whether an article is good;
- whether a business decision is correct.

### 5.2 New terminal state vocabulary

Remove business-quality implication from kernel status.

Recommended v2:

```python
ExecutionState = Literal[
    "completed",
    "failed",
    "limit_reached",
]
```

Pause remains a separate receipt state:

```python
state = "paused"
```

Do not use `partial` as a semantic downgrade because a metadata check failed.

If an agent returns a result before a usage boundary and the framework knows it was interrupted, `limit_reached` may contain an artifact/presentation if available; the UI can describe it without inventing a semantic quality judgment.

### 5.3 Remove semantic fields

New receipts MUST NOT write these fields:

```text
RunSummary.evidence
RunSummary.artifacts as model claims
RunSummary.unknowns as host verification degradation
verified_artifacts
verified_knowledge
verified_tool_effects
settled_evidence
degraded
knowledge_updates as "evidence"
```

`RunSummary` SHOULD be removed or collapsed into a small compatibility/terminal message record.

### 5.4 Operational replacements

If byte tracking is useful:

```python
class ArtifactFact(BaseModel):
    path: str
    size: int
    sha256: str
    change: Literal["created", "modified"]
```

This is an integrity fact, not “ArtifactVerification”.

If tool event projection is useful:

```python
class ToolEffectFact(BaseModel):
    tool_call_id: str
    tool_name: str
    status: Literal["started", "completed", "failed"]
```

No `verified_` prefix.

A v2 `RunReceipt` MAY contain:

```text
schema_version
state
run_id
conversation_id
continued_from_run_id
bindings
model
started_at
finished_at
execution_state
usage
usage_complete
artifact_facts
tool_effect_facts
error
step_store
tool_result_store
composition
```

Only retain fields that have a real consumer.

## 6. `verification.py` becomes integrity-only

### Delete

The following semantic mechanisms MUST be deleted from the kernel:

```text
_EVIDENCE_RE
parse_evidence_ref()
verify_knowledge() as semantic proof
verify_tool_effect() as evidence-ref resolution
model-claimed evidence processing
status degradation because an evidence ref cannot be resolved
```

### Retain / rename as needed

These functions represent useful integrity/security behavior:

```text
sha256_file
artifact path normalization / containment
pre-run artifact byte snapshot
changed-artifact byte facts
StepStore tool-event projection
```

The module SHOULD be renamed to something such as:

```text
integrity.py
run_facts.py
```

Do not create both.

### Rule

A byte hash can prove byte identity/change. It MUST NOT be described as proof of correctness.

## 7. Knowledge simplification

### Current problem

`KnowledgeStore` currently defines semantic authority through:

```text
REQUIRED_SOURCE_TYPES
NO_SOURCE_TYPES
KNOWN_TYPES
SourceRef
frontmatter sources
generated.run_id
```

The source requirement can detect an empty field; it cannot verify that the content is supported.

### Target

Knowledge storage becomes document-first.

Minimum required invariants:

- path containment;
- atomic write;
- readable Markdown;
- optional run provenance if operationally useful;
- rebuildable index.

The core MUST NOT require a semantic enum such as:

```text
concept
claim
method
reference
project-note
decision
```

for truth.

Recommended API:

```python
write_knowledge(
    knowledge_id: str,
    title: str,
    body: str,
    tags: list[str] | None = None,
)
```

If run attribution is useful, it may be generated mechanically and remain non-authoritative.

Source URLs belong in the Markdown body or linked source section.

### Important

This does not prohibit a business plugin from defining its own domain schema. It prohibits the generic kernel knowledge store from pretending one global schema encodes epistemic validity.

## 8. Case must become a real plugin

### 8.1 Context

Delete kernel-level `context_projection.py` after equivalent behavior moves into the Case plugin.

Implement Case context through a PydanticAI Capability owned by `plugins/zuaef-case`.

Conceptual shape:

```text
zuaef-case
├── CaseStore
├── CaseContextCapability
├── CaseToolset
└── case-specific validation
```

`CaseContextCapability` reads:

```python
ctx.deps.bindings.get("case")
```

and contributes a bounded natural-language brief.

The Case toolset may remain deferred while Case context is available.

### 8.2 Approval isolation

Delete runtime `_assert_pending_case_isolation`.

Cross-case authorization MUST be enforced in Case-owned tool validation before approval.

Use released PydanticAI validation/approval seams (`args_validator`, tool validation, or the narrowest supported mechanism).

Kernel rule:

> Kernel handles pending approvals generically; domain plugins decide whether tool arguments are authorized for their binding.

## 9. Generalist capability abstraction stop

### Current problem

The same capability list exists across:

- `AgentSettings`;
- environment variables;
- `GENERALIST_FLAGS`;
- `ProfileGeneralistPolicy`;
- composition policy;
- `generalist_capabilities()`.

This becomes a local registry layered on top of Harness.

### v1 rule

`GENERALIST_FLAGS` is **CLOSED**.

Do not add new entries.

Current entries may remain temporarily for compatibility.

Any newly adopted Harness capability MUST first be evaluated as:

1. direct capability in an existing platform pack/profile;
2. capability returned by a plugin;
3. explicit local composition.

It MUST NOT automatically create a new global ZUAEF flag.

### Later optional cleanup

Only after the main subtraction is stable, current generalist constructors MAY move into a single platform capability/plugin package. Do not make that migration a dependency of this spec if it increases risk.

## 10. Plugin ABI freeze

Keep the current small ABI:

```python
PluginEnv
PluginBundle(
    toolsets=...,
    skill_dirs=...,
    capabilities=...,
)
```

Do NOT add:

```text
services
event handlers
background tasks
middleware
runtime handles
agent registry
dependency injection container
plugin lifecycle bus
```

unless a measured real failure cannot be solved by PydanticAI/Harness capabilities/toolsets.

## 11. Result evidence contract

The generic runtime MUST NOT invent an evidence schema.

For deliverables that rely on factual external material:

- the artifact SHOULD use inline Markdown links/citations;
- or it MUST contain a readable `Sources` section;
- every listed source SHOULD include a real URL or stable resource link;
- the prose SHOULD make it possible to understand which source supports which material claim.

Example:

```markdown
The project uses Python package entry points for plugin discovery
([Python packaging specification](https://packaging.python.org/...)).

## Sources
- [PydanticAI custom capabilities](https://...)
- [DeepSeek Harness architecture](https://...)
```

A URL is not automatically proof. Reviewers must inspect whether it actually supports the claim.

## 12. Quality evaluation is not kernel runtime

Quality evaluation MUST be offline or operator-driven.

No production `Agent.run()` should be forced through:

```text
sensor → enum → action → score → gate
```

to be considered successful.

Sensors may exist as diagnostics but MUST be explicitly named diagnostic/heuristic and MUST NOT independently promote learning.

## 13. Source authority hierarchy for learning

Authoritative learning inputs:

1. actual task/request;
2. actual context/material available to the model;
3. actual model output;
4. actual source URLs/resource links;
5. actual human feedback/edit/preference;
6. accepted revised output.

Derived and non-authoritative:

```text
LLM labels
sensor scores
topic tags
embeddings
action classifications
weights
summaries
auto-generated rationale
```

Derived data may be regenerated or deleted.

## 14. Capability-owned Result Contract

### 14.1 Decision

**The structure of a business deliverable is owned by the Capability/domain plugin that knows what the deliverable means.**

The kernel MUST NOT define one universal business-result schema.

The generic agent terminal remains:

```python
output_type=[str, DeferredToolRequests]
```

A Capability customizes the result through released PydanticAI mechanisms:

- `get_instructions()` — describe what a good deliverable looks like for this capability;
- `get_toolset()` — provide domain actions and, where useful, a domain-owned save/finalize tool;
- wrapper / preparation / lifecycle hooks only when the domain genuinely needs them;
- domain-local code may use Pydantic models internally when it needs deterministic validation, but those models MUST NOT become the generic Kernel result contract.

PydanticAI explicitly supports Capability-provided instructions and toolsets. ZUAEF MUST use those seams instead of adding a `result_schema`, `output_fields`, `evidence_fields`, or similar Plugin/Kernel registry.

### 14.2 Result Contract is behavior, not a field schema

A Result Contract answers:

```text
What is the useful end product?
What form should it take?
What must be visible to the user?
Which domain constraints must it respect?
Which source links/citations should appear in the artifact?
Which domain-owned tool saves or delivers it?
```

It is NOT:

```text
title: str
summary: str
evidence: list[str]
unknowns: list[str]
score: float
verified: bool
```

unless a particular business capability genuinely needs such a structure internally for its own deterministic operation.

### 14.3 Examples

#### Writing Capability

The writing capability can define:

```text
deliverable = the article itself
artifact = article Markdown
structure = capability instructions / style assets / task context
sources = inline links or source notes only where factual sourcing is relevant
terminal presentation = full article or concise pointer when artifact is too long
```

No generic `RunSummary.article`, `evidence`, `style_score`, or `quality` field.

#### Research Capability

The research capability can define:

```text
deliverable = decision-oriented research report
structure = question → findings → reasoning → uncertainty → sources
sources = real URLs attached to the claims/findings they support
```

This structure belongs to research instructions/tooling, not to `RunReceipt`.

#### Budget Capability

The budget capability can define:

```text
deliverable = business-readable budget analysis
structure = observed numbers → important variances → implications → questions/actions
```

Deterministic numeric calculations may be validated by the budget plugin, but Kernel does not gain budget fields.

#### Negotiation / Client Service Capability

The capability may decide the useful result is:

```text
customer-facing reply
+
optional operator-only reasoning/notes
```

If two artifacts are useful, the capability owns that convention. Kernel does not add `customer_reply` and `internal_strategy` fields.

### 14.4 Composition rule

Do NOT invent a `ResultContractRegistry`.

Active capabilities compose normally. The capability that owns the requested business outcome provides the strongest domain-specific result guidance and/or save tool.

If two capabilities genuinely conflict over final form, resolve it in:
- the deployment/profile's business instructions;
- a composed higher-level Capability;
- or the task-specific plugin.

Do not solve it by adding global result-type arbitration to Kernel.

### 14.5 Artifact naming and storage

Kernel may provide generic file/storage primitives.

A capability MAY define domain conventions such as:

```text
article.md
research-report.md
budget-analysis.md
customer-reply.md
```

Those names/formats are domain policy and MUST NOT be enumerated in Kernel.

### 14.6 Evidence presentation is part of the Result Contract

For capabilities that make factual claims, source presentation belongs to the capability's result contract.

Examples:

```text
research → claim-level links + Sources section
technical guide → inline links to docs/repositories
article → source notes only where required by the task/editorial policy
budget → source workbook/input reference, not fake web citations
```

There is no universal rule that every artifact must expose the same `sources` field.

### 14.7 Pydantic boundary: shape, not workflow

Pydantic is used to describe and validate **objects at boundaries**.

Legitimate uses include:

```text
tool arguments
external API request/response objects
plugin configuration
persisted records
deterministic domain data structures
```

Examples:

```text
WordPress tool args:
  title/content/status have the shapes required by the WordPress API

Budget input:
  period/value/category fields parse into a deterministic calculation object

Plugin config:
  site_url/path/options have valid types and values
```

Pydantic MUST NOT be used to impose an Agent workflow such as:

```text
stage = research
research_complete = true
evidence_count >= 3
approved = true
next_stage = drafting
```

and MUST NOT create a field-driven process gate such as:

```text
if result.has_sources and result.score > 0.8:
    allow_next_phase()
```

unless that condition is an actual external-system or safety invariant.

Business work remains an Agent loop:

```text
understand
→ decide what is needed
→ use relevant capability/tools
→ produce the useful result
→ revise when needed
```

The path is not encoded as a Pydantic state machine.

### 14.8 Deterministic checks are local computations, not process gates

A capability/tool may perform deterministic checks when the domain itself requires them.

Examples:

```text
budget arithmetic reconciles
a URL parses
a WordPress status is one the API accepts
a filesystem path stays inside its allowed root
```

These checks validate the object/action being executed.

They MUST NOT be promoted into generic workflow governance, completion fields, phase transitions, or quality gates.

### 14.9 Semantic judgment remains model/human work

Questions such as:

```text
Is this research sufficient?
Is this article credible?
Is this recommendation good?
Should another source be consulted?
Is this draft ready?
```

are not Pydantic validation questions.

They are model judgment, capability guidance, and where appropriate human review.

### 14.10 Forbidden result abstractions

Do not add to generic ZUAEF APIs:

```text
ResultSchema
ResultRegistry
DeliverableType enum
EvidenceField
QualityField
UniversalReport
BusinessResult BaseModel
ArtifactKind registry
```

unless multiple real independent domains have first demonstrated the same stable deterministic requirement and upstream PydanticAI/Harness cannot express it.

## 14. Backward compatibility

Old receipts are historical records and MUST NOT force the new runtime to keep old semantic fields.

Preferred strategy:

- writer emits only v2;
- if old receipt reading is still needed for resume/history, isolate v1.2 parsing in one narrow legacy adapter;
- do not copy old evidence semantics into new models;
- no dual-write.

## 15. Dependency direction

```text
gateway ──→ kernel
plugins ──→ kernel public API
platform ─→ kernel / upstream capabilities

kernel -X→ gateway
kernel -X→ business plugins
kernel -X→ Case
```

## 16. Change rule after freeze

Kernel modification is allowed only for:

1. PydanticAI/Harness compatibility;
2. execution correctness;
3. security boundary;
4. durability/resume correctness;
5. composition ABI;
6. generic operational run facts.

“Need a new business capability” is not sufficient reason to edit the kernel.
