# Capability Admission Protocol

## Principle

A capability is a modification of the model's cognitive environment.

It is not admitted merely because it is implemented upstream.

## Admission questions

Every proposed production capability must answer:

1. **Failure:** What reproduced task failure exists without it?
2. **Mechanism:** What exact mechanism does the capability add?
3. **Model surface:** What tools/instructions/settings/hooks become visible or active?
4. **Cost:** What measured requests/tokens/context/latency does it add?
5. **Alternative:** Can deterministic code or a narrower tool solve the failure?
6. **A/B:** Does the capability improve the outcome on the target failure?
7. **Scope:** Which profile/task class needs it?
8. **Withdrawal:** What benchmark would allow us to remove it later?

## Default capability table

This table is a starting status, not eternal policy.

| Capability | Default re-foundation status | Admission evidence |
|---|---|---|
| Planning | NOT ADMITTED | measurable long-run drift |
| Skills | NOT ADMITTED GLOBALLY | task needs deferred expert guidance and improves outcome |
| FileSystem | NOT ADMITTED GLOBALLY | model must semantically navigate workspace |
| Knowledge | NOT ADMITTED GLOBALLY | task requires that knowledge surface |
| ToolOutputLimits | CONDITIONAL | oversized returns measurably pollute context |
| StepPersistence | CONDITIONAL | durability/debug/resume requirement |
| Memory | NOT ADMITTED | cross-session forgetting causes reproduced failure |
| ConversationSearch | NOT ADMITTED | bounded current state is insufficient and historical retrieval helps |
| RepoContext | NOT ADMITTED | code/repository task needs orientation |
| SubAgents | NOT ADMITTED | isolation/parallelism produces measured benefit |
| ToolSearch | NOT ADMITTED | large tool surface causes selection/context failure |
| Context controls | NOT ADMITTED | measured context pressure |
| Shell | NOT ADMITTED | authorized execution task requires it |
| CodeMode | EXPERIMENTAL | repeated dependent tool calls cause round-trip/context bloat |

## Example — Planning

Bad justification:

```text
The task is complex.
Planning is a Harness best practice.
```

Valid justification:

```text
Benchmark LONG-3 runs for 40+ model turns.
Without Planning, 4/10 runs omit required unfinished steps.
With Planning, 9/10 complete all steps.
Median requests increase 6%, outcome completion rises 50%.
Planning admitted only to profile long-ops.
```

## Example — StepPersistence

Bad:

```text
All serious agents should be durable.
```

Valid:

```text
Gateway must resume a paused external-effect approval after process restart.
Without persisted settled frontier, the run cannot safely continue.
StepPersistence admitted to that interaction profile.
```

## Admission record template

Use:

```text
templates/runtime-refoundation/capability-admission.md
```

No capability is promoted in the same commit that first proposes its admission unless the evidence already exists and is linked.

