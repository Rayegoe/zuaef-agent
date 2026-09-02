# Technical Architecture

## 1. Authority boundaries

### ZUAEF owns
- one outcome-owning `pydantic_ai.Agent`;
- profile/plugin composition;
- run lifecycle;
- step persistence and receipts;
- general capabilities;
- artifact/knowledge boundaries;
- future approval seam for external effects.

### QuantDecision Capability owns
- stable instructions for evidence-based A-share decisions;
- a minimal QuantToolset;
- no daemon, background service, broker runtime or second persistence framework.

### Deterministic quant code owns
- market-data normalization;
- indicator/feature calculation;
- strategy evaluation;
- transaction costs;
- tradeability checks;
- event replay;
- metrics.

### LLM owns
- hypothesis formation;
- selecting one meaningful mutation;
- interpreting evidence;
- writing Strategy Result;
- explaining Decision Brief.

The LLM does not own deterministic market facts.

## 2. Historical path

```text
AKShare history / validated cache
               ↓
normalized market dataset
               ↓
Qlib fast/vector research
               ↓
frozen signals/trades
               ↓
independent event replay
               ↓
StrategyEvidence
               ↓
QuantDecision Agent
               ↓
Strategy Result
```

## 3. Live path

```text
AKShare current snapshot
        ↓
deterministic active-strategy scanner
        ↓
0..N triggered candidates
        ↓
compact DecisionContext
        ↓
bounded ZUAEF run
        ↓
Decision Brief
```

No candidate → no LLM request is required.

## 4. Watch-process boundary

If P5 proves a watcher is useful, it is a host process such as `tools/quant_watch.py`:

```text
poll market → deterministic scan → trigger bounded ZUAEF run only when needed
```

It is not a Plugin background task and does not change ZUAEF Core into a trading daemon.

## 5. Minimal target layout

```text
plugins/zuaef-quant/
  pyproject.toml
  zuaef_quant/
    __init__.py
    plugin.py
    capability.py
    toolset.py
    market_data.py
    strategy.py
    engine.py
    replay.py

profiles/quant-decision.toml
benchmarks/quant-decision/
  benchmark.toml
  market_rules.toml
  baseline.py
  evolve.py
examples/quant_decision.py
tests/quant/
```

Prefer fewer files if possible. If the MVP grows to 30+ new Python modules before live/paper proof, stop and justify the architecture.

## 6. Artifact truth

Do not begin with an experiment database.

Use existing artifact/knowledge mechanisms:

```text
strategy artifacts:
  strategy.toml
  evidence.json
  trades.csv
  equity.csv

learning artifact:
  strategy-result.md
```

Any future SQLite layer must be a rebuildable index justified by measured retrieval pain.

## 7. Receipt boundary

Do not add PnL, win rate or strategy lifecycle to `RunReceipt`.

Receipt answers what executed and what files were produced. Strategy evidence answers whether a strategy was useful.

## 8. No second runtime

Forbidden absent a separate proven need:
- `QuantRuntime`
- `StrategyManager`
- `ExperimentManager`
- `GateManager`
- `PromotionEngine`
- custom event bus
- graph state machine
- second Agent registry
- separate receipt store.
