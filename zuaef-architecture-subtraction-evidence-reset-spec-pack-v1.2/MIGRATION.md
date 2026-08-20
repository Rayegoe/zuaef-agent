# MIGRATION — Current Repository to Target

Baseline: `main@14e0df06012c4b925012d3ee9be0734af0282a7d`

## 1. `src/zuaef_agent/models.py`

### Current
Contains:

- `SourceRef`
- `RunSummary.artifacts`
- `RunSummary.evidence`
- `RunSummary.unknowns`
- `ArtifactVerification`
- `ToolEffectVerification`
- `RunReceipt.verified_*`
- `RunReceipt.degraded`
- `PauseReceipt.settled_evidence`
- `CoreDeps.case_id`

### Target

Remove semantic authority.

Suggested replacements:

```text
SourceRef                     → remove from kernel
ArtifactVerification          → ArtifactFact (only if consumed)
ToolEffectVerification        → ToolEffectFact
CoreDeps.case_id              → bindings
RunReceipt.verified_*         → artifact_facts/tool_effect_facts or delete
PauseReceipt.settled_evidence → delete
degraded                      → delete
```

Remove `RunSummary` entirely if no real consumer requires it. If compatibility requires it temporarily, reduce it to operational settlement only and schedule deletion.

## 2. `src/zuaef_agent/verification.py`

### Current
Mixes:
- path safety;
- hashing;
- run ownership;
- knowledge schema checks;
- evidence-ref parser;
- StepStore event projection.

### Target

Create one smaller integrity module.

Keep:
- hash;
- containment;
- changed-file facts;
- StepStore event facts.

Delete:
- semantic evidence parser;
- knowledge-source validation as truth;
- status degradation hooks.

Do not create an `evidence_v2.py`.

## 3. `src/zuaef_agent/runtime.py`

### Current
`finalize_terminal()` performs semantic-looking settlement and downgrades status based on `degraded`.

### Target

Runtime:
- executes;
- records usage;
- handles pause/resume;
- records errors;
- records changed artifact byte facts if useful;
- records tool-event facts if useful.

Runtime MUST NOT:
- parse model evidence references;
- decide factual quality;
- downgrade because a source field is absent;
- know Case identity;
- inspect domain knowledge types.

Delete `_assert_pending_case_isolation`.

Replace `case_id` threading with opaque `bindings`.

## 4. `src/zuaef_agent/knowledge_store.py`

### Current
Global semantic types and source requirements.

### Target
Document store only.

Remove:
- `REQUIRED_SOURCE_TYPES`
- `NO_SOURCE_TYPES`
- `KNOWN_TYPES`
- truth semantics attached to `sources` frontmatter.

Retain:
- safe IDs;
- containment;
- atomic writes;
- search/list/read;
- optional simple metadata.

If current knowledge capability is no longer useful after upstream Memory adoption, do not force this spec to preserve it as a core invariant.

## 5. `src/zuaef_agent/knowledge_capability.py`

Simplify tool instructions.

Remove claims such as “evidence-backed artifacts” unless the content actually contains inspectable sources.

Do not require the model to construct `SourceRef` objects merely to satisfy storage.

## 6. `src/zuaef_agent/context_projection.py`

Delete from generic source tree after migration.

Move the useful bounded natural-language projection logic to:

```text
plugins/zuaef-case/zuaef_case/context.py
```

or the smallest equivalent module.

Expose through a Case-owned PydanticAI Capability.

## 7. `plugins/zuaef-case`

Add only what the domain needs:

```text
context capability
binding lookup
case-specific tool argument validation
```

Do not add a plugin service layer.

Tool approval isolation must happen before approval through an upstream-supported validation seam.

## 8. `src/zuaef_agent/gateway/bridge.py`

Remove:

```text
project_case_context
CASE_CONTEXT_SEPARATOR
case-specific context injection
```

Gateway passes:

```text
prompt
bindings
conversation identity
```

The composed plugin capability handles domain context.

## 9. `src/zuaef_agent/continuation.py`

Replace receipt `case_id` restoration with `bindings`.

Resume remains exact with respect to:
- conversation;
- composition;
- bindings;
- message history;
- pending tool results.

## 10. `config.py`, `profiles.py`, `core.py`

Do not expand `GENERALIST_FLAGS`.

Add a comment/test that the current list is closed compatibility surface.

Future generic abilities should arrive via upstream capability composition/plugin, not global schema expansion.

A later change may extract these constructors, but do not combine that larger move with the critical evidence cleanup unless tests prove it is low risk.

## 11. Editorial learning assets

### Current authority
`human_patches.jsonl` encodes derived semantic fields.

### New authority
Prefer:

```text
learning/cases/
```

or a renamed benchmark-local equivalent.

For each migrated case preserve:
- original request/context when available;
- rejected/before text;
- chosen/after text;
- original editor comment;
- original dataset/source URL;
- rights/license note.

Move old sensor/action/weight fields under:

```text
derived/legacy/
```

if still required for historical benchmark reproduction.

No production runtime imports these derived fields.

## 12. Tests

Rewrite tests around real invariants.

Delete tests whose only purpose is to assert:
- a `verified_` field exists;
- an evidence ref string matches a regex;
- a semantic enum was copied;
- a hard-coded quality weight equals a fixed number.

Keep/add tests for:
- path traversal rejection;
- exact composition resume;
- bindings preservation;
- native approval;
- plugin isolation;
- changed artifact byte facts;
- StepStore continuity;
- old receipt compatibility if explicitly retained;
- source-linked artifact example;
- learning case round trip preserving full human text.

## 13. Documentation

Update:
- README;
- AGENTS.md;
- plugin development experience;
- relevant Phase specs.

Replace “verified business result” language with precise terms:
- execution fact;
- artifact byte fact;
- source-linked result;
- human-reviewed quality.

## 14. Result-structure ownership migration

Search for any generic code that assumes business results have fixed fields.

Target rule:

```text
before:
Kernel/RunSummary/Receipt tells the model or host what a business result contains

after:
Capability instructions + capability-owned tools define the deliverable
Kernel only executes and records operational facts
```

For each existing domain:

### ACE Writing
Move/retain article structure, editorial behavior, source presentation, and save semantics inside the writing capability/plugin. Do not reintroduce them in `CORE_INSTRUCTIONS`.

### Budget
Keep deterministic calculation/report semantics in budget plugin code/instructions. Kernel sees only natural presentation/artifact facts.

### Client Service
Keep reply/strategy conventions in the client-service capability/plugin.

### WordPress
Keep post fields required by WordPress inside the WordPress plugin. They are tool/API parameters, not generic Agent result fields.

### Research (future/current)
Research capability owns claim/source presentation conventions.

Migration acceptance:
- changing a writing article format does not edit Kernel;
- changing budget report format does not edit Kernel;
- adding a new domain result does not edit a generic result schema.
