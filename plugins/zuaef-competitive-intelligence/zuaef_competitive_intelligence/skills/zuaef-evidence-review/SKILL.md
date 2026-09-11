---
name: zuaef-evidence-review
description: "Use before finalizing any evidence-backed deliverable (product or competitor diagnostics, research syntheses, client-facing reports, quantitative claims) to separate facts, inferences, recommendations and gaps, and to stop unsupported claims from reaching the user."
---

# Skill: Evidence Review

## Purpose

Enforce the evidence boundary between fact, inference, recommendation, and gap.
Prevent over-claiming and prevent weak signals from being presented as strong conclusions.

## When to Use

- Before finalizing any report, diagnostic, synthesis, or recommendation.
- When a claim needs its evidentiary basis checked ("how sure are you about X?").
- After reading sources/knowledge material and before writing conclusions.
- When a deliverable mixes retrieved facts, model inference, and advice.

## Evidence Taxonomy

Classify every claim into exactly one bucket.

### 1. Fact
- Directly supported by a source URL, quoted snippet, or evidence path.
- Independently verifiable by a third party.
- Example: "Model X is listed at $1,999 on the official market page as of June 2025."

### 2. Inference
- A logical consequence of one or more stated facts.
- Must be labeled as inference, never presented as fact.
- Must state the facts it rests on.
- Example: "It is reasonable to infer a mid-market positioning, because (a) the top-selling models are priced $1,500-$2,500 and (b) marketing copy emphasizes daily commuting."

### 3. Recommendation
- Actionable advice derived from facts and inferences.
- Must carry an explicit risk caveat.
- Must state what evidence would change it.
- Example: "Monitor the certification rollout (risk: delay increases regulatory exposure; evidence needed: an official announcement)."

### 4. Gap
- A claim or question for which no evidence currently exists.
- Stated explicitly, never hidden or smoothed over.
- Must explain why closing the gap matters.
- Example: "Gap: no evidence of the battery cell supplier. This matters because cell supplier determines the certification pathway and insurance risk."

## Hard Rules

```text
1. A critical claim without source_url OR quoted_snippet OR evidence_path is a gap, not a fact.
2. An inference presented without its underlying facts is a hidden assumption - downgrade to gap.
3. A recommendation without a risk caveat is incomplete.
4. A recommendation without a stated falsifier is speculation.
5. Weak signals (single source, dated source, anonymous source) are labeled "tentative".
6. Never state certainty beyond what the evidence supports.
7. Never claim an action, delivery or side effect occurred unless the active tool surface performed it and returned success.
```

## Validation Workflow

When asked to validate evidence:

```text
Step 1: List every claim made in the reasoning or draft.
Step 2: For each claim, look for source_url / quoted_snippet / evidence_path.
Step 3: Classify each claim as fact / inference / recommendation / gap.
Step 4: Flag inferences missing their underlying facts.
Step 5: Flag recommendations missing a risk caveat or falsifier.
Step 6: Flag critical claims with no evidence.
Step 7: Output the structured evidence map.
Step 8: State whether the deliverable passes the evidence gate.
```

## Output Format

```markdown
## Evidence Map

| Claim | Type | Evidence | Status |
|-------|------|----------|--------|
| ...   | Fact | source: ... | OK |
| ...   | Inference | rests on: ... | OK |
| ...   | Recommendation | risk: ...; falsifier: ... | OK |
| ...   | Gap | why it matters: ... | OPEN |

## Gate Result

- Gaps found: N
- Warnings: N
- Pass: YES / NO
- If NO: which claims must be fixed before delivery
```

## Iron Rule

> Fact without evidence is not fact. Inference without facts is assumption. Recommendation without risk is opinion. Gap unspoken is deception.
