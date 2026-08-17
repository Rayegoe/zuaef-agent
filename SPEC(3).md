# ZUAEF Cognitive Editorial Control Capability — SPEC v0.1

**Target repository:** `Rayegoe/zuaef-agent`  
**Baseline:** `main` commit `a03fd4a52afddb98e347e5d447fbbbf7975c942f`  
**Target plugin:** `plugins/zuaef-ace-writing`  
**Status:** implementation-ready

## 1. Outcome

Make ACE Writing generate high-quality nonfiction through a **runtime cognitive editorial feedback loop**, not through a longer style prompt, a fixed template, a post-hoc reviewer that rewrites the article, or a second custom Agent runtime.

The capability continuously changes the *conditions of the next model step* using approved editorial evidence. It can also reject the first `save_artifact` attempt **before side effects occur** when the draft has converged on a strongly templated trajectory.

The article remains owned by the existing ZUAEF Agent. ACE remains owner of material, evidence, claim validation, canonical artifact semantics, and receipts.

## 2. Non-goals

This feature MUST NOT:

- modify PydanticAI's Agent Loop;
- modify `writing_toolset.py` domain behavior;
- add a writer Agent / reviewer Agent pair;
- perform token-by-token decoding control;
- claim to reproduce a publication or individual writer;
- store full copyrighted exemplar articles as the default runtime corpus;
- allow the model to approve its own editorial evidence;
- auto-rewrite the whole article after generation;
- invent scenes, quotations, memories, or reported facts.

## 3. Architecture

```text
ACE Writing Toolset (unchanged)
        │
        ├── materials / exemplars / knowledge / claims / save
        │
ZUAEF Agent
        │
        └── EditorialControlCapability
              │
              ├── per-run EditorialRunState
              ├── dynamic instructions
              ├── before_model_request
              ├── after_model_request
              ├── after_tool_execute
              └── before_tool_execute(save_artifact)
                         │
                         ├── trajectory sensors
                         ├── approved EditorialEvidence retrieval
                         └── bounded ModelRetry veto
```

## 4. Why this is a Capability

The feature is cross-cutting behavior, not a tool. It combines:

- lifecycle hooks;
- dynamic instructions;
- optional model-setting adjustment;
- per-run state isolation;
- policy over another tool (`save_artifact`);
- provenance-bearing external evidence.

That matches PydanticAI's `AbstractCapability` abstraction and keeps ZUAEF Core unchanged.

## 5. Control-loop semantics

### 5.1 First request

Do not inject a style recipe. The capability only adds minimal invariants:

- do not optimize for one-pass completion;
- do not imitate a fixed template;
- preserve factual boundaries;
- interventions are local cognitive moves;
- prefer patches over whole-document rewrites.

### 5.2 After material / exemplar observation

`after_tool_execute` records context tags. It may prepare one low-pressure, evidence-backed intervention for the next request.

Examples:

- `return_to_observation`;
- `retrieve_concrete_memory`.

These are cognitive moves, not target sentences.

### 5.3 After a substantial model response

`after_model_request` runs cheap trajectory sensors over long-form text. The sensors do **not** define taste. They answer only: “is there enough evidence of drift to retrieve human-approved editorial decisions?”

Initial sensors:

- `template_connectors`;
- `summary_pressure`;
- `uniform_paragraphs`;
- `low_concrete_anchor_density`;
- `abstract_noun_density`.

### 5.4 Before the next model request

Dynamic instructions expose at most one current cognitive move plus its provenance refs.

Optional `temperature_nudge` may change sampling only when explicitly configured. Default is zero.

### 5.5 Before `save_artifact`

This is the hard control point.

1. Inspect `final_markdown`.
2. Detect trajectory signals.
3. Retrieve matching approved editorial evidence.
4. If the combined drift crosses the configured threshold:
   - veto **before** the tool executes;
   - raise `ModelRetry`;
   - require the model to make the smallest useful patch;
   - preserve claims and source ledger;
   - allow at most `max_save_vetoes` (default: 1).
5. A second/identical candidate can never enter an infinite loop.

This turns the save boundary into adversarial generation rather than post-hoc review.

## 6. Editorial evidence

### 6.1 Unit of learning

Do not store “style = rules”.

Store:

```text
Situation
→ observed drift
→ human/corpus editorial action
→ rationale
→ source/provenance
```

Schema:

```json
{
  "id": "human.patch.delay-explanation.001",
  "source_type": "human_patch",
  "source_ref": "patch:...",
  "situation_tags": ["drafting", "nonfiction"],
  "trigger_signals": ["summary_pressure"],
  "action": "delay_interpretation",
  "directive": "...",
  "rationale": "...",
  "weight": 4.0,
  "approved_by": "human-editor",
  "before_excerpt": "...",
  "after_excerpt": "..."
}
```

### 6.2 Sources

Evidence may come from:

1. **Human patches** — highest-value source. Capture before/after plus why the editor changed it.
2. **Approved corpus observations** — derive an editorial move from a publication/article, while storing provenance and only bounded excerpts if needed.
3. **Editorial notes** — explicit decisions such as “hold the explanation until after the second scene”.
4. Built-in seed evidence — bootstrap only, not the long-term moat.

For a preferred publication such as 三联, the system should not reduce the source to “三联风格 prompt”. It should extract repeated **editorial decisions**:
camera distance, timing of interpretation, treatment of contradiction, scene-to-argument transitions, use of quoted speech, rhythm, omission, etc.

## 7. Cognitive actions v0.1

Exactly five:

1. `return_to_observation`
2. `delay_interpretation`
3. `shift_perspective`
4. `retrieve_concrete_memory`
5. `break_trajectory`

Do not add more until real human patches demonstrate a missing action class.

## 8. Factual boundary

“Human-like cognition” does not mean fake nonfiction.

- Source-grounded recollection may be used as fact.
- Unsupported personal memory MUST NOT be invented.
- Free association, analogy, or imagination may be used only when explicitly framed as interpretation/association.
- ACE claim/evidence rules remain authoritative.

## 9. State and durability

`EditorialRunState` is per `Agent.run()` via `for_run()`.

It contains only ephemeral control state:

- model-request count;
- intervention count;
- save-veto count;
- context tags;
- latest signals;
- pending intervention;
- last veto hash.

Long-term editorial learning lives in the host-owned JSONL evidence store, not in run state.

The plugin version is bumped to `0.2.0`; ZUAEF CompositionSnapshot therefore treats this as a different composition. Old paused runs must not silently resume under the new behavior.

## 10. Configuration

```toml
[[plugins]]
id = "ace-writing"
allow_capabilities = true

[plugins.config]
ace_root = "..."
editorial_control = true
editorial_max_injections = 4
editorial_max_save_vetoes = 1
editorial_evidence_limit = 3
editorial_veto_threshold = 1.50
editorial_temperature_nudge = 0.0
```

Optional:

```toml
editorial_evidence_path = "~/.config/zuaef/editorial/evidence.jsonl"
editorial_base_temperature = 0.7
```

## 11. Acceptance gates

### Gate A — no regression

Existing ACE tool names and `writing_toolset.py` behavior are unchanged.

### Gate B — bounded control

- no more than four normal interventions;
- no more than one save veto by default;
- identical rejected drafts are never rejected forever.

### Gate C — provenance

Every semantic intervention references one or more `EditorialEvidence.id` values.

### Gate D — human ownership

The Agent has no tool for self-approving or persisting editorial evidence.

### Gate E — A/B proof

Prepare at least 20 real article tasks and run:

- A: ACE Writing with `editorial_control=false`
- B: same model/material/budgets with `editorial_control=true`

Blind human evaluation should compare:

- perceived templating;
- narrative movement;
- premature explanation;
- specificity/grounding;
- overall publishability.

Machine sensors are diagnostics, not the success metric.

### Gate F — learning proof

Take at least 30 real human edits and ingest them as approved evidence. Re-run the same A/B set and verify that selected evidence refs increasingly come from human patches rather than built-in seeds.

## 12. Future extensions — explicitly deferred

Do not implement yet:

- semantic-vector evidence retrieval;
- a separate editorial LLM;
- full-stream token interception;
- automatic paragraph-by-paragraph generation;
- RL/fine-tuning;
- automatic corpus mining;
- self-learning from model-generated patches;
- multi-agent writer/reviewer orchestration.

Only add these when v0.1 evidence shows a concrete failure mode that cannot be fixed within the existing capability hook surface.
