# 02 — Architecture

## Target architecture

```text
                    ZUAEF-Agent
            reasoning / orchestration / research
                         │
          ┌──────────────┼─────────────────┐
          │              │                 │
          ▼              ▼                 ▼
   Quant Action API   Evidence API     Experiment API
          │              │                 │
          └──────┬───────┴────────┬────────┘
                 │                │
                 ▼                ▼
        Deterministic Core   Sandbox / Code Runner
        signals/risk/gates    S0 / S1 / S2
                 │                │
                 ▼                ▼
           Evidence Store   Experiment Store
                 │                │
                 └──────┬─────────┘
                        ▼
              Dashboard / Telegram
                        │
                        ▼
                      Human

Broker/data providers remain below the system as market/account infrastructure.
```

## Component responsibilities

### Quant Runtime — production authority

- ingest/normalize permitted data;
- generate candidate pool;
- evaluate timing/triggers;
- evaluate deterministic risk gates;
- manage position lifecycle;
- freeze observations and decisions;
- settle outcomes;
- emit machine-readable state.

The runtime must not delegate hard risk permissions to an LLM.

### ZUAEF-Agent

- interpret system state;
- decide which read/control tools to call;
- investigate anomalies;
- retrieve contextual evidence on demand;
- formulate hypotheses;
- schedule/run sandbox experiments;
- explain decisions and failures;
- create work packets for code changes;
- never silently modify production strategy or evidence.

### Evidence Store

Append-oriented source of truth for:

- observations;
- data-trust verdicts;
- trigger/gate states;
- decisions;
- position lifecycle events;
- settlements;
- replay outputs;
- experiment outputs;
- deployment/config identifiers.

### Sandbox / Code Runner

- S0 Scratch: exploratory Python/SQL/shell.
- S1 Replay: historical clock and PIT-safe data boundary.
- S2 Shadow: live data, simulated actions, no broker effects.

### Evidence Retrieval Layer

On-demand contextual evidence, not a bulk LLM feed. Primary first wave:

- market/sector breadth;
- announcements;
- corporate actions;
- current positions/cost basis;
- minute price/volume.

### Presentation/Attention

Dashboard and Telegram are **projections**, not the source of truth. Agent should consume structured state/events rather than scrape HTML.

## Architectural invariants

1. Production strategy is versioned and frozen until explicit promotion.
2. Replay and live-forward evidence use separate namespaces.
3. An experiment can never rewrite historical production evidence.
4. A real order is an external effect and requires the configured external-effect gate.
5. Missing/uncertain critical evidence fails closed for live trade permission.
6. The LLM can propose; deterministic code permits/denies.
