# QUALITY LOOP — Real Evidence and LLM/Human Iteration

## 1. Purpose

This document replaces “quality by hard-coded evidence fields” with a real learning loop.

The loop is intentionally outside the generic agent runtime.

## 2. What counts as real evidence

### For factual/research work

Evidence is inspectable material that another reader can follow.

Preferred form:

```text
claim
→ citation/link in the actual deliverable
→ source URL
→ reviewer opens source
→ reviewer checks support
```

The runtime should not convert this into `evidence=["knowledge:x"]`.

### For writing/style work

Evidence is not a URL alone.

The strongest quality evidence is:

```text
same task/context
→ output A
→ output B or human revision
→ human preference/annotation
→ explanation grounded in the text
```

Source URLs are still useful when factual material is involved.

### For business actions

Execution evidence is:

```text
tool event / external response / resulting resource
```

but this is an operational fact, not a quality score.

## 3. Learning case packet

Do not begin with a universal JSON schema.

Use a document-first case packet:

```text
learning/cases/<case-id>/
├── request.md
├── context.md
├── output.md
├── sources.md
├── llm-review.md
├── human-review.md
├── revised.md
└── manifest.json       # minimal addressing only
```

`manifest.json` is allowed only for mechanical addressing, for example:

```json
{
  "case_id": "writing-20260820-001",
  "run_id": "...",
  "artifact": "output.md"
}
```

It MUST NOT contain a mandatory taxonomy such as:

```text
trigger_signal
editorial_action
quality_weight
truth_score
approved_by
```

unless a specific experiment derives them temporarily.

## 4. LLM review contract

The reviewer receives:

- original request;
- relevant context/material;
- model output;
- source URLs/resource links;
- optional prior human rules/examples.

The LLM reviewer produces prose, not a fixed classification.

Minimum review questions:

1. What did the output actually accomplish?
2. What important requirement did it miss?
3. Which factual claims need source checking?
4. For each important cited claim, does the cited source appear to support it?
5. What is weak in reasoning, writing, structure, tone, or business judgment?
6. Which passages should change, and why?
7. What should be preserved?
8. What generalizable lesson, if any, can be proposed?

The reviewer MUST be allowed to say:

> no reusable lesson should be promoted from this case.

## 5. Human review contract

Human review is authoritative for preference/promotion.

The human can:

```text
ACCEPT
REJECT
EDIT
PARTIAL
```

These words may be used in the Markdown for convenience, but no database enum is needed.

The human should primarily provide:

- direct comments;
- selected preferred passages;
- edits;
- counterexamples;
- business constraints;
- “do not generalize this” notes.

## 6. Promotion unit

Do not promote sensor/action rows.

Promote one of:

### A. Natural-language guideline

Example:

```markdown
When the source material contains a concrete customer phrase, prefer preserving
that phrase or its local texture rather than summarizing it into a generic
judgment sentence. Do not apply this if the phrase would expose private data.
```

### B. Before / after pair

```text
request/context
before
human revision
why
```

### C. Full accepted exemplar

Only where rights/privacy allow.

### D. Tool/plugin behavior correction

If the failure is actually mechanical, fix the tool/plugin instead of teaching a writing rule.

## 7. Promotion destination

Use the lowest adequate layer:

```text
one-off case fact       → Case / memory
reusable instruction    → Skill
reusable examples       → plugin-owned example pack
deterministic behavior  → Toolset/plugin code
cross-domain runtime    → kernel only if genuinely generic
```

## 8. Promotion process

```text
real task
  ↓
real artifact
  ↓
LLM critique
  ↓
human review/edit
  ↓
candidate lesson
  ↓
apply to held-out / next tasks
  ↓
human comparison
  ├─ better → promote
  ├─ neutral → keep experimental
  └─ worse → reject/rollback
```

No automatic promotion because an LLM assigned high confidence.

## 9. Evaluation design

### Primary metric
Human task-level preference / acceptance.

Examples:

- “Which version would you send?”
- “Which version better satisfies the brief?”
- “Which version is more credible?”
- “Which version requires fewer edits?”

### Secondary metric
LLM judge with source access and explicit reasoning.

LLM judge is useful for scale, triage, and finding issues, but is not the final authority for style/business preference.

### Tertiary diagnostics
Regex/sensors/metrics may detect patterns:

```text
repetition
citation presence
length
broken links
sentence distribution
tool/request counts
```

They MUST be labeled diagnostics and MUST NOT be used as semantic truth without human validation.

## 10. Source inspection

For evidence-bearing work, the evaluation path SHOULD actually fetch/open source URLs when network/tool access exists.

The evaluator should distinguish:

```text
URL present
URL reachable
source relevant
claim supported
claim contradicted
insufficient source
```

These judgments belong in review prose or experiment outputs, not the kernel receipt.

## 11. Migration of Editorial Learning

The current benchmark assets can be useful, but their authority must change.

Current records such as:

```text
trigger_signals = ["abstract_noun_density"]
action = "return_to_observation"
weight = 4.0
approved_by = "human-editor"
```

must be treated as **legacy derived features**, not human truth.

Migration:

1. preserve original before/after text and original source/provenance;
2. preserve actual editor comments where available;
3. make those the authoritative learning case;
4. retain sensors/actions only under an explicit `derived/legacy/` location if experiments still need them;
5. no production capability may require those fields;
6. new learning records are document-first.

## 12. Rollback

Every promoted learning asset should be independently removable.

Do not mutate an opaque global “evidence score”.

Prefer:

```text
skills/writing/SKILL.md versioned change
examples/<pack>/...
plugin version bump
```

Then comparison/rollback is normal version control.

## 13. Relationship to Capability Result Contracts

The learning loop does not define a universal output format.

Each Capability owns its own useful result form. The quality loop evaluates that result **in its native form**.

Examples:

```text
Writing:
  judge the actual article

Research:
  judge the actual report and inspect its URLs

Budget:
  judge the analysis against the actual numbers/input

Negotiation:
  judge the actual proposed/customer-facing response and outcome context
```

Do not normalize all four into a shared JSON evaluation object before review.

If an evaluator needs temporary structured fields for experiment aggregation, generate them as a derived experiment artifact after preserving the native result and natural-language human review.
