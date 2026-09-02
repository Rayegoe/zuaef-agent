# Capability / Plugin / Toolset Contract

## 1. Correct hierarchy

Current Pydantic AI/Harness documentation treats **Capabilities as the primary extension point**. Capabilities may combine instructions, toolsets/tools, model settings and hooks.

In ZUAEF:

```text
zuaef-quant Plugin
        ↓
QuantDecision Capability
        ↓
QuantToolset
        ↓
AKShare / Qlib / Replay
```

Plugin and Capability are not alternatives.

## 2. v1 implementation choice

Use the lightest upstream primitive:

```python
from pydantic_ai.capabilities import Capability

quant_decision = Capability(
    id="quant-decision",
    description="Evidence-based A-share strategy research and decision support.",
    instructions=QUANT_INSTRUCTIONS,
    toolsets=[quant_toolset],
)
```

Then return it through existing ZUAEF composition:

```python
return PluginBundle(capabilities=[quant_decision])
```

Do not subclass `AbstractCapability` until a concrete need appears for hooks/wrapping/per-run capability state.

## 3. Stable domain instructions

Keep them short and durable:

1. Evidence before intuition.
2. Simulation before capital.
3. Distinguish backtest, paper and real evidence.
4. Real evidence outranks simulated evidence when they conflict, while respecting sample size.
5. Change one material strategy element per experimental child.
6. Never claim an opportunity without deterministic trigger evidence.
7. `NO_TRADE` is valid.
8. Do not modify evaluator, market rules, cost model or benchmark.
9. Do not generate or execute arbitrary strategy Python.
10. State uncertainty/data limitations explicitly.

Do not inject a giant workflow prompt.

## 4. Tool surface

Start with three tools.

### `evaluate_strategy(strategy_spec)`
Host-owned:
- validate StrategySpec;
- load frozen historical data/protocol;
- Qlib/vector evaluation;
- freeze signals/trades;
- independent replay;
- OOS/robustness;
- write artifacts;
- return bounded evidence.

### `get_live_signals()`
- read current snapshot;
- deterministically run active strategies;
- return only triggers and compact context;
- do not ask the LLM to scan the entire market.

### `record_trade_outcome(outcome)`
- record paper or manually executed real trade facts;
- no broker action;
- local/file-native effect.

## 5. Existing upstream capabilities

Reuse rather than rebuild:
- StepPersistence;
- context controls;
- instrumentation;
- ToolSearch only if tool count justifies it;
- SpendLimits when multi-run autonomous cost becomes material.

## 6. Deferred loading

A dedicated `quant-decision` profile may load QuantDecision eagerly because the domain surface is small.

A future broad FDE profile may make QuantDecision deferred/on-demand.

## 7. CodeMode / SubAgents / DynamicWorkflow

Default OFF.

The Quant Agent should call high-level deterministic tools, not script dozens of low-level actions. Adopt one only after measured failure demonstrates it is the smallest solution.

## 8. Upstream refresh

Before final Quant integration, run a bounded compatibility refresh targeting:
- Pydantic AI 2.35.3
- Pydantic AI Harness 0.27.x

Harness is 0.x. After validation, pin the compatible minor range rather than leaving an unbounded `>=0.1`.

If upgrade requires broad unrelated refactoring, stop and report rather than rewriting Core merely to chase releases.
