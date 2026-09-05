# 03 — Architecture

```text
Market/Data
    |
Candidate Builder
    |
M1 Quant Runtime
(timing/lifecycle/positions/settlement)
    |
    +--> Canonical State ---------> Workbench
    |
    +--> Durable Alerts ----------> Quant Event Bridge
    |                                |       |
    |                              E1/E2   deterministic events
    |                                |
    |                         QuantDecision Agent
    |                         interpretation only
    |                                |
    +----------------------------> Bridge
                                     |
                                  Telegram
    |
    +--> Six-tool Agent Surface
    |
    +--> Replay / Experiment Orchestrator
             |        |        |
            S0       S1       S2
          Scratch   Replay   Shadow
```

Authority:
- Runtime owns deterministic trading facts and permission.
- Agent interprets, investigates, proposes hypotheses, runs bounded research.
- Bridge owns proactive Telegram delivery.
- Human owns real-money action during M1.

Critical naming rule:
Current `market_no_trade` means healthy cycle/no actionable opportunity.
Never reuse it for Market Regime.
New fields: `regime`, `participation_permission`, `regime_reason_codes`.
