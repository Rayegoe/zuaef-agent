# Event Types

Suggested logical event taxonomy; map onto existing storage instead of forcing a rewrite.

- `runtime.tick.started`
- `runtime.tick.completed`
- `runtime.health.changed`
- `market.regime.observed`
- `candidate.snapshot`
- `trigger.observed`
- `decision.frozen`
- `position.changed`
- `exit.attention`
- `evidence.trust.changed`
- `observation.forward.created`
- `observation.settled`
- `replay.started`
- `replay.decision.frozen`
- `replay.settled`
- `experiment.proposed`
- `experiment.started`
- `experiment.completed`
- `experiment.promoted`
- `experiment.rejected`
- `report.generated`
- `report.delivered`

Every event should include mode/namespace, timestamp/as-of, run ID, and relevant version identifiers.
