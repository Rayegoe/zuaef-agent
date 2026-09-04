# P4/P5 — Research Memory + Decision/Position Replay

## Research Memory

Do not build a Memory Platform.

```text
workspace/artifacts/quant/research/
  RESEARCH_LOG.md
  LESSONS.md
  OPEN_QUESTIONS.md
  experiments/
  reviews/
```

### RESEARCH_LOG

What have we actually tried? Preserve failures as well as winners.

### LESSONS

What is currently worth believing, but still falsifiable?

Lifecycle:

`CANDIDATE / SUPPORTED / CONTRADICTED / RETIRED`

Each Lesson contains scope, evidence references, interpretation, `Do not infer`, and revisit condition.

### OPEN_QUESTIONS

Highest-value uncertainty, not development backlog.

### Research Run Start

Read active strategy, relevant Research Log, Lessons, Open Questions, parent experiment and latest forward evidence, then answer:

> What single uncertainty is most valuable to reduce now for future trading decisions?

### Research Run End

Output:

`Observation -> Comparison -> Interpretation -> Lesson Impact -> Next Question`

Contradictions append; they do not silently overwrite old Lessons.

---

# Material Decision / Position History

Latest views may be replaced:

- `docs/quant/business.html`
- `docs/quant/dashboard.html`
- latest scan/current position view.

Material historical observations must not be rewritten to match later knowledge.

Preserve enough history to reconstruct:

1. what opportunity state existed;
2. what the strategy/Agent said;
3. whether the user acted;
4. how the position evolved;
5. what exit/closure occurred;
6. what happened afterward.

Multiple material intraday observations are real observations. Do not collapse 10:00, 11:30 and 14:50 into one daily record merely because the calendar date is identical.

## Position Continuity

A user-confirmed real or paper trade creates a position lifecycle that survives page refresh/restart and remains monitored until closure.

Position history should preserve business facts needed for learning, such as entry/action times, position size when supplied, material HOLD/REDUCE/EXIT events and closure outcome. Do not copy every market field into every position record.

## Forward Outcome

Forward observations link back to the original opportunity/decision/position without rewriting what was known at that time.

D+1/3/5/8, MFE/MAE and eventual exit/net outcomes are business evidence. They should be gathered continuously as the market unfolds rather than reconstructed only after formal P6 begins.

## Traceability

Where Agent/Harness run references exist, link them. Keep traceability proportional to its learning/audit value; do not turn provenance into the primary user experience.
