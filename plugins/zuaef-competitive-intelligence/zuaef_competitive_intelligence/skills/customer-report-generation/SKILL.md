---
name: customer-report-generation
description: "Use after diagnostic reasoning to produce a business-owner-readable report: one-sentence judgment, evidence-backed findings, business meaning, prioritized next actions, honest gaps and a confidence statement."
---

# Skill: Customer Report Generation

## Purpose

Produce a report that a business owner - not an engineer, not a data analyst - can read, trust, and act on.

## When to Use

- After diagnostic or research reasoning is complete.
- Before writing the final customer-facing artifact.
- When the user says "write this up for my boss" or "make it customer-ready".

## Audience Definition

```text
Reader: business owner / executive
Knowledge level: no technical background in the domain or in AI
Time: 5-10 minutes maximum
Goal: understand the situation, the risk, and what to do next
```

## Report Structure

### 1. One-Sentence Judgment (Top)

The first line is a single sentence stating the core conclusion.

```text
BAD:  "This report analyzes the competitive landscape using multi-source intelligence..."
GOOD: "<Competitor> poses a mid-tier competitive threat in <segment>; their
       <certification/coverage> gap is the most actionable risk to monitor."
```

### 2. What We Found (3-5 bullets)

Each bullet: one clear point, evidence-backed, no jargon.

```text
BAD:  "Their mid-drive motor delivers 500W nominal with 120 Nm torque,
       outperforming competitors' hub motors at equivalent price points."
GOOD: "Their bikes use a stronger motor than competitors at the same price,
       which matters for hill climbing and cargo loads."
```

### 3. What It Means (1 paragraph)

Translate findings into business meaning: revenue impact, competitive positioning, risk or opportunity.

### 4. What to Do Next (2-3 actions)

Prioritized and actionable.

### 5. What We Do Not Know (Honest Gaps)

State gaps without apology, but with consequence: what would change if the gap closed.

### 6. Confidence Statement

```text
"This assessment is based on <source class> as of <date>. Key uncertainties are: <list>."
```

## Language Rules

```text
BAD:  "Leverage synergies across the value chain"
BAD:  "The schema validates a positive correlation between wattage and satisfaction"
BAD:  "Our AI model flagged 3 anomalies in the signal stream"

GOOD: "Use the dealer network for direct feedback"
GOOD: "Higher motor power tends to make customers happier"
GOOD: "We noticed 3 unusual patterns in their recent activity"
```

## Forbidden Elements

```text
- Technical spec tables longer than 3 rows
- Confidence expressed as percentages or scores
- "AI-driven insights" marketing language
- Jargon without explanation
- Charts without a one-sentence takeaway
```

## Output Targets

Two outputs:

1. **Full report** - internal reasoning plus the evidence map. Persist it
   through the deployment's report tool (ZUAEF competitive-intelligence:
   `save_work_product(kind='report')`, then `render_report` for report.pdf /
   report.docx).
2. **Customer summary** - the 5-minute version for the business owner:
   delivered in the reply, or saved as `customer_summary.md` in the run
   artifact root when the composed surface has a file tool.

If the composed surface has no artifact tool, deliver both in the reply and say
where they would be persisted - never claim a file was written when it was not.

## Iron Rule

> The report is not to show off analysis. It is to help a business person make a better decision.
