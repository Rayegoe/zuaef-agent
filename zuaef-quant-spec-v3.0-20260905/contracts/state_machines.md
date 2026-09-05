# State Machines

## Experiment

```text
PROPOSED → RUNNING → {REJECTED | REPLAY_PASS}
REPLAY_PASS → SHADOW → {REJECTED | FORWARD_EVALUATION}
FORWARD_EVALUATION → {REJECTED | PROMOTED}
```

No transition may skip directly from `PROPOSED` to `PROMOTED`.

## Observation

```text
CREATED → FROZEN → DUE → SETTLED
                    ↘ INVALIDATED(reason)
```

Outcome data may not modify the frozen decision payload.

## Report delivery

```text
GENERATED → DELIVERY_PENDING → DELIVERED
                         ↘ FAILED → RETRY
```

Delivery retry never re-enters the decision state machine.
